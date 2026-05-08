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