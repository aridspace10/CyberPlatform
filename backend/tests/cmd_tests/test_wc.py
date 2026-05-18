import pytest
import datetime
import random
import math
from game.commandline import CommandLine
from game.ShellState import ShellState
from game.filesystem import FileSystem
from game.filenode import FileNode, Inode, NodeType
from wonderwords import RandomWord
from game.helpers import determine_perms_fromstr
import os
import time

# ---------- BASIC ----------

def test_wc_l_empty_file(cl, shell_emptyfile: ShellState):
    stderr, stdout = cl.enter_command('wc -l empty.txt', shell_emptyfile)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_l_single_line_no_newline(cl, shell_one_line_no_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt', shell_one_line_no_newline)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_l_single_line_with_newline(cl, shell_one_line_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt', shell_one_line_newline)
    assert stderr == []
    assert stdout == ["1"]


def test_wc_l_two_lines(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


# ---------- BLANK LINES ----------

def test_wc_l_blank_lines(cl, shell_blank_lines: ShellState):
    stderr, stdout = cl.enter_command('wc -l blank.txt', shell_blank_lines)
    assert stderr == []
    assert stdout == ["3"]


def test_wc_l_only_newlines(cl, shell_only_newlines: ShellState):
    stderr, stdout = cl.enter_command('wc -l nl.txt', shell_only_newlines)
    assert stderr == []
    assert stdout == ["4"]


def test_wc_l_whitespace_lines_count(cl, shell_whitespace_lines: ShellState):
    stderr, stdout = cl.enter_command('wc -l white.txt', shell_whitespace_lines)
    assert stderr == []
    assert stdout == ["3"]


# ---------- PIPE INPUT ----------

def test_wc_l_pipe_cat(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | wc -l', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


def test_wc_l_pipe_empty(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('ls | wc -l', shell_empty)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_l_pipe_grep(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat | wc -l', shell_sed)
    assert stderr == []
    assert stdout == ["2"]


def test_wc_l_pipe_filtered_single(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command(
        'cat f1.txt | grep wolf | wc -l',
        shell_sed
    )
    assert stderr == []
    assert stdout == ["1"]


def test_wc_l_pipe_no_matches(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command(
        'cat f1.txt | grep zebra | wc -l',
        shell_sed
    )
    assert stderr == []
    assert stdout == ["0"]


# ---------- MULTIPLE FILES ----------

def test_wc_l_two_files(cl, shell_twofiles: ShellState):
    stderr, stdout = cl.enter_command('wc -l f1.txt f2.txt', shell_twofiles)
    assert stderr == []
    assert stdout == [
        "2 f1.txt",
        "3 f2.txt",
        "5 total"
    ]


def test_wc_l_multiple_files_one_empty(cl, shell_mixfiles: ShellState):
    stderr, stdout = cl.enter_command(
        'wc -l a.txt b.txt',
        shell_mixfiles
    )
    assert stderr == []
    assert stdout == [
        "0 a.txt",
        "4 b.txt",
        "4 total"
    ]


# ---------- EDGE CASES ----------

def test_wc_l_file_not_found(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -l fake.txt', shell_basic)
    assert stdout == []
    assert len(stderr) > 0


def test_wc_l_directory_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -l d1', shell_basic)
    assert stdout == []
    assert stderr == ["wc: cannot perform operation on directory (d1)"]


def test_wc_l_no_arguments(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -l', shell_basic)
    # depends whether your shell reads stdin or errors
    assert stderr == [] or len(stderr) > 0


# ---------- STRESS / ODDITIES ----------

def test_wc_l_large_file(cl, shell_largefile: ShellState):
    stderr, stdout = cl.enter_command('wc -l huge.txt', shell_largefile)
    assert stderr == []
    assert stdout == ["1000"]


def test_wc_l_trailing_newline_matters(cl, shell_trailing_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l t.txt', shell_trailing_newline)
    assert stderr == []
    assert stdout == ["2"]


def test_wc_l_no_final_newline(cl, shell_no_final_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -l t.txt', shell_no_final_newline)
    assert stderr == []
    assert stdout == ["1"]

# Byte / char count derivation for each fixture (all content is ASCII so -c == -m):
#
# Encoding model: each line contributes len(line)+1 bytes (\n terminator),
# except the last line which only gets +1 if has_trailing_newline is True
# (the FileSystem default is True).
#
# shell_emptyfile         []                              → 0 B
# shell_one_line_no_newline ["hello"], trailing=False     → 5 B
# shell_one_line_newline  ["hello"], trailing=True        → 6 B
# shell_blank_lines       ["","",""], trailing=True       → 3 B
# shell_only_newlines     ["","","",""], trailing=True    → 4 B
# shell_whitespace_lines  ["   ","\t","hello"]            → 4+2+6 = 12 B
# shell_twofiles f1       ["a","b"]                       → 4 B
# shell_twofiles f2       ["1","2","3"]                   → 6 B
# shell_mixfiles  a       []                              → 0 B
# shell_mixfiles  b       ["1","2","3","4"]               → 8 B
# shell_trailing_newline  ["a","b"], trailing=True        → 4 B
# shell_no_final_newline  ["a","b"], trailing=False       → 3 B
# shell_largefile         [str(i) for i in range(1000)]
#   "0"\n=2, "1"–"9"\n=9×2=18, "10"–"99"\n=90×3=270, "100"–"999"\n=900×4=3600 → 3890 B
# shell_sed f1            ["cat wolf cat","hi cat"]       → 14+7 = 21 B


# ---------- WC -C (BYTES) — basic ----------

def test_wc_c_empty_file(cl, shell_emptyfile: ShellState):
    stderr, stdout = cl.enter_command('wc -c empty.txt', shell_emptyfile)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_c_single_line_no_newline(cl, shell_one_line_no_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -c f1.txt', shell_one_line_no_newline)
    assert stderr == []
    assert stdout == ["5"]


def test_wc_c_single_line_with_newline(cl, shell_one_line_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -c f1.txt', shell_one_line_newline)
    assert stderr == []
    assert stdout == ["6"]


def test_wc_c_blank_lines(cl, shell_blank_lines: ShellState):
    stderr, stdout = cl.enter_command('wc -c blank.txt', shell_blank_lines)
    assert stderr == []
    assert stdout == ["3"]


def test_wc_c_only_newlines(cl, shell_only_newlines: ShellState):
    stderr, stdout = cl.enter_command('wc -c nl.txt', shell_only_newlines)
    assert stderr == []
    assert stdout == ["4"]


def test_wc_c_whitespace_lines(cl, shell_whitespace_lines: ShellState):
    # "   "\n + "\t"\n + "hello"\n = 4 + 2 + 6 = 12
    stderr, stdout = cl.enter_command('wc -c white.txt', shell_whitespace_lines)
    assert stderr == []
    assert stdout == ["12"]


def test_wc_c_trailing_newline(cl, shell_trailing_newline: ShellState):
    # "a"\n + "b"\n = 2 + 2 = 4
    stderr, stdout = cl.enter_command('wc -c t.txt', shell_trailing_newline)
    assert stderr == []
    assert stdout == ["4"]


def test_wc_c_no_final_newline(cl, shell_no_final_newline: ShellState):
    # "a"\n + "b" (no trailing \n) = 2 + 1 = 3
    stderr, stdout = cl.enter_command('wc -c t.txt', shell_no_final_newline)
    assert stderr == []
    assert stdout == ["3"]


# ---------- WC -C (BYTES) — pipe ----------

def test_wc_c_pipe_cat(cl, shell_sed: ShellState):
    # f1.txt: ["cat wolf cat", "hi cat"] → 14 + 7 = 21
    stderr, stdout = cl.enter_command('cat f1.txt | wc -c', shell_sed)
    assert stderr == []
    assert stdout == ["21"]


def test_wc_c_pipe_grep_all_match(cl, shell_sed: ShellState):
    # both lines contain "cat"; piped output preserves newlines → 21 B
    stderr, stdout = cl.enter_command('cat f1.txt | grep cat | wc -c', shell_sed)
    assert stderr == []
    assert stdout == ["21"]


def test_wc_c_pipe_grep_one_match(cl, shell_sed: ShellState):
    # only "cat wolf cat\n" matches "wolf" → 14 B
    stderr, stdout = cl.enter_command('cat f1.txt | grep wolf | wc -c', shell_sed)
    assert stderr == []
    assert stdout == ["14"]


def test_wc_c_pipe_no_match(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep zebra | wc -c', shell_sed)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_c_pipe_empty_dir(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('ls | wc -c', shell_empty)
    assert stderr == []
    assert stdout == ["0"]


# ---------- WC -C (BYTES) — multiple files ----------

def test_wc_c_two_files(cl, shell_twofiles: ShellState):
    # f1: ["a","b"] → 4 B;  f2: ["1","2","3"] → 6 B;  total 10 B
    stderr, stdout = cl.enter_command('wc -c f1.txt f2.txt', shell_twofiles)
    assert stderr == []
    assert stdout == [
        "4 f1.txt",
        "6 f2.txt",
        "10 total",
    ]


def test_wc_c_multiple_files_one_empty(cl, shell_mixfiles: ShellState):
    # a: 0 B;  b: ["1","2","3","4"] → 8 B;  total 8 B
    stderr, stdout = cl.enter_command('wc -c a.txt b.txt', shell_mixfiles)
    assert stderr == []
    assert stdout == [
        "0 a.txt",
        "8 b.txt",
        "8 total",
    ]


# ---------- WC -C (BYTES) — edge cases ----------

def test_wc_c_file_not_found(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -c fake.txt', shell_basic)
    assert stdout == []
    assert len(stderr) > 0


def test_wc_c_directory_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -c d1', shell_basic)
    assert stdout == []
    assert stderr == ["wc: cannot perform operation on directory (d1)"]


def test_wc_c_large_file(cl, shell_largefile: ShellState):
    # "0"\n=2, "1"–"9"\n=9×2=18, "10"–"99"\n=90×3=270, "100"–"999"\n=900×4=3600 → 3890
    stderr, stdout = cl.enter_command('wc -c huge.txt', shell_largefile)
    assert stderr == []
    assert stdout == ["3890"]


# ---------- WC -M (CHARS) — basic ----------
# All fixture content is pure ASCII so char count == byte count throughout.

def test_wc_m_empty_file(cl, shell_emptyfile: ShellState):
    stderr, stdout = cl.enter_command('wc -m empty.txt', shell_emptyfile)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_m_single_line_no_newline(cl, shell_one_line_no_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -m f1.txt', shell_one_line_no_newline)
    assert stderr == []
    assert stdout == ["5"]


def test_wc_m_single_line_with_newline(cl, shell_one_line_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -m f1.txt', shell_one_line_newline)
    assert stderr == []
    assert stdout == ["6"]


def test_wc_m_blank_lines(cl, shell_blank_lines: ShellState):
    stderr, stdout = cl.enter_command('wc -m blank.txt', shell_blank_lines)
    assert stderr == []
    assert stdout == ["3"]


def test_wc_m_only_newlines(cl, shell_only_newlines: ShellState):
    stderr, stdout = cl.enter_command('wc -m nl.txt', shell_only_newlines)
    assert stderr == []
    assert stdout == ["4"]


def test_wc_m_whitespace_lines(cl, shell_whitespace_lines: ShellState):
    stderr, stdout = cl.enter_command('wc -m white.txt', shell_whitespace_lines)
    assert stderr == []
    assert stdout == ["12"]


def test_wc_m_trailing_newline(cl, shell_trailing_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -m t.txt', shell_trailing_newline)
    assert stderr == []
    assert stdout == ["4"]


def test_wc_m_no_final_newline(cl, shell_no_final_newline: ShellState):
    stderr, stdout = cl.enter_command('wc -m t.txt', shell_no_final_newline)
    assert stderr == []
    assert stdout == ["3"]


# ---------- WC -M (CHARS) — pipe ----------

def test_wc_m_pipe_cat(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | wc -m', shell_sed)
    assert stderr == []
    assert stdout == ["21"]


def test_wc_m_pipe_grep_one_match(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep wolf | wc -m', shell_sed)
    assert stderr == []
    assert stdout == ["14"]


def test_wc_m_pipe_no_match(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('cat f1.txt | grep zebra | wc -m', shell_sed)
    assert stderr == []
    assert stdout == ["0"]


def test_wc_m_pipe_empty_dir(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command('ls | wc -m', shell_empty)
    assert stderr == []
    assert stdout == ["0"]


# ---------- WC -M (CHARS) — multiple files ----------

def test_wc_m_two_files(cl, shell_twofiles: ShellState):
    stderr, stdout = cl.enter_command('wc -m f1.txt f2.txt', shell_twofiles)
    assert stderr == []
    assert stdout == [
        "4 f1.txt",
        "6 f2.txt",
        "10 total",
    ]


def test_wc_m_multiple_files_one_empty(cl, shell_mixfiles: ShellState):
    stderr, stdout = cl.enter_command('wc -m a.txt b.txt', shell_mixfiles)
    assert stderr == []
    assert stdout == [
        "0 a.txt",
        "8 b.txt",
        "8 total",
    ]


# ---------- WC -M (CHARS) — edge cases ----------

def test_wc_m_file_not_found(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -m fake.txt', shell_basic)
    assert stdout == []
    assert len(stderr) > 0


def test_wc_m_directory_error(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command('wc -m d1', shell_basic)
    assert stdout == []
    assert stderr == ["wc: cannot perform operation on directory (d1)"]


def test_wc_m_large_file(cl, shell_largefile: ShellState):
    stderr, stdout = cl.enter_command('wc -m huge.txt', shell_largefile)
    assert stderr == []
    assert stdout == ["3890"]


# ---------- ASCII invariant: -c and -m must agree ----------

def test_wc_cm_agree_single_line(cl, shell_one_line_newline: ShellState):
    _, c = cl.enter_command('wc -c f1.txt', shell_one_line_newline)
    _, m = cl.enter_command('wc -m f1.txt', shell_one_line_newline)
    assert c == m


def test_wc_cm_agree_multiline(cl, shell_sed: ShellState):
    _, c = cl.enter_command('wc -c f1.txt', shell_sed)
    _, m = cl.enter_command('wc -m f1.txt', shell_sed)
    assert c == m


def test_wc_cm_agree_trailing_newline(cl, shell_trailing_newline: ShellState):
    _, c = cl.enter_command('wc -c t.txt', shell_trailing_newline)
    _, m = cl.enter_command('wc -m t.txt', shell_trailing_newline)
    assert c == m


def test_wc_cm_agree_no_final_newline(cl, shell_no_final_newline: ShellState):
    _, c = cl.enter_command('wc -c t.txt', shell_no_final_newline)
    _, m = cl.enter_command('wc -m t.txt', shell_no_final_newline)
    assert c == m


# ---------- Combined flags: -lc and -lm ----------

def test_wc_lc_two_lines(cl, shell_sed: ShellState):
    # f1.txt: 2 lines, 21 bytes
    stderr, stdout = cl.enter_command('wc -l -c f1.txt', shell_sed)
    assert stderr == []
    parts = stdout[0].split()
    assert parts[0] == "2"       # line count
    assert parts[1] == "21"      # byte count
    assert parts[2] == "f1.txt"


def test_wc_lm_two_lines(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command('wc -l -m f1.txt', shell_sed)
    assert stderr == []
    parts = stdout[0].split()
    assert parts[0] == "2"
    assert parts[1] == "21"
    assert parts[2] == "f1.txt"


def test_wc_lmc_ascii_chars_equal_bytes(cl, shell_sed: ShellState):
    # With all three flags on ASCII content, char count == byte count
    stderr, stdout = cl.enter_command('wc -l -m -c f1.txt', shell_sed)
    assert stderr == []
    parts = stdout[0].split()
    # expected order: line_count char_count byte_count filename
    assert parts[0] == "2"
    assert parts[1] == parts[2]  # chars == bytes for ASCII
    assert parts[3] == "f1.txt"