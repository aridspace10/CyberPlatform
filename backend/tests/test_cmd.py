import json
import random

import pytest
from game.filenode import FileNode
from game.filesystem import FileSystem
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import descendants, tree_state
from tests.command_helpers import setup_names


@pytest.mark.integration
@pytest.mark.parametrize("option", ["-a", "-A"])
def test_shell_dot_paths_listing_then_find_and_save(run_dot_command, dot_shell, option):
    before = tree_state(dot_shell)
    run_dot_command(f"ls {option} .")
    result = run_dot_command("find .")
    assert result.status == 0
    assert result.stderr == []
    expected_count = len(list(descendants(dot_shell.fs.current)))
    assert len(result.stdout) == expected_count
    assert len(result.stdout) == len(set(result.stdout))
    assert tree_state(dot_shell) == before
    json.loads(json.dumps(dot_shell.fs.to_dict()))


@pytest.mark.integration
@pytest.mark.parametrize("option", ["-a", "-A"])
def test_shell_dot_paths_listing_then_recursive_remove(
    run_dot_command, dot_shell, option
):
    current = dot_shell.fs.current
    data = current.access("data.txt")
    run_dot_command(f"ls {option} ./branch")
    assert_success(run_dot_command("rm -r ./branch", unchanged=False))
    assert current.access("branch") is None
    assert current.access("data.txt") is data


@pytest.mark.integration
@pytest.mark.parametrize("operator", ["<", ">", ">>"])
def test_shell_dot_paths_redirection_rejects_directory(
    run_dot_command, dot_directory, operator
):
    operand, _ = dot_directory
    command = "cat" if operator == "<" else "echo changed"
    assert_failure(run_dot_command(f"{command} {operator} {operand}"))


@pytest.mark.integration
@pytest.mark.parametrize("operator", ["<", ">", ">>"])
def test_shell_dot_paths_redirection_resolves_file(
    run_dot_command, dot_shell, dot_prefix, operator
):
    source = dot_shell.fs.current.access("data.txt")
    before = list(source.inode.data)
    if operator == "<":
        result = run_dot_command(f"cat < {dot_prefix}data.txt")
        assert_success(result, before)
    else:
        result = run_dot_command(
            f"echo changed {operator} {dot_prefix}data.txt", unchanged=False
        )
        assert_success(result)
        expected = before + ["changed"] if operator == ">>" else ["changed"]
        assert source.inode.data == expected


@pytest.mark.integration
@pytest.mark.parametrize("operator", ["<", ">", ">>"])
def test_shell_dot_paths_redirection_rejects_invalid_traversal(
    run_dot_command, invalid_dot_path, operator
):
    command = "cat" if operator == "<" else "echo changed"
    assert_failure(run_dot_command(f"{command} {operator} {invalid_dot_path}"))


def test_cmd_unknown(cl, shell_empty):
    CmdResult = cl.enter_command("test abcd", shell_empty)
    assert CmdResult.stderr == ["Unknown command given"]
    assert CmdResult.stdout == []


def test_redirection_writes_file(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("echo hi > d1/f3.txt", shell_basic)
    assert CmdResult.stdout == []
    assert CmdResult.stderr == []
    CmdResult = cl.enter_command("cat d1/f3.txt", shell_basic)
    assert CmdResult.stdout == ["hi"]
    assert CmdResult.stderr == []


def test_redirection_path_error(cl, shell_basic: ShellState, fs_basic):
    CmdResult = cl.enter_command("echo hi > not/f3.txt", shell_basic)
    assert CmdResult.stderr == ["No directory named not"]
    assert CmdResult.stdout == []

    CmdResult = cl.enter_command("echo hi >> not/f3.txt", shell_basic)
    assert CmdResult.stderr == ["No directory named not"]
    assert CmdResult.stdout == []


def test_redirection_rewrites_file(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command("echo hi >> f1.txt", shell_basic)
    fs_basic.search("f1.txt")
    fnode = fs_basic.current
    assert fnode.get_data() == ["ERROR no", "INFO hey", "ERROR no2", "error 1", "hi"]


def test_redirection_writes_newfile(cl, shell_basic: ShellState, fs_basic: FileSystem):
    cl.enter_command("echo hi >> f3.txt", shell_basic)
    fs_basic.search("f3.txt")
    fnode = fs_basic.current
    assert fnode.get_data() == ["hi"]


def test_andor(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d1 && ls", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


def test_and_failure(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d3 && ls", shell_basic)
    assert CmdResult.stderr == ["cd:No directory named d3"]
    assert CmdResult.stdout == []


def test_subshell_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("(cd d1 && ls)", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]
    CmdResult = cl.enter_command("ls", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt", "d1"]


def test_semicolon_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("cd d1; ls", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


def test_var_basic(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("X=5", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert shell_basic.vars["X"] == "5"

    CmdResult = cl.enter_command("echo $X", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["5"]


def test_var_error(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("echo $X", shell_basic)
    assert CmdResult.stderr == ["Var Used which is unassigned: X"]
    assert CmdResult.stdout == []


def test_pipes_lsgrep(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep f", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt"]


def test_pipes_lshead(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | head --lines=2", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f1.txt", "f2.txt"]


def test_pipes_lshead2(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("ls | head", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_pipes_sortuniq(cl, shell_basic: ShellState):
    names = setup_names(shell_basic, "f2.txt")
    print(names)
    name = random.choice(names)
    names = names.copy()
    fn = shell_basic.fs.get_file("f2.txt")
    assert isinstance(fn, FileNode)
    fn.append_data([name])
    CmdResult = cl.enter_command("sort f2.txt | uniq", shell_basic)
    assert CmdResult.stderr == []
    assert len(CmdResult.stdout) == len(names)
    for i in range(0, len(names)):
        assert CmdResult.stdout[i] == names[i]


def test_pipes_lsgrep_inverse(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep -v f1", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f2.txt", "d1"]


def test_pipes_lssort(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | sort", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == sorted(CmdResult.stdout)


def test_pipes_ls_tail(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | tail --lines=2", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt", "f4.txt"]


def test_pipes_catgrep(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat", "hi cat"]


def test_pipes_catgrephead(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | head --lines=1", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat"]


def test_pipes_catgreptail(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | tail --lines=1", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hi cat"]


def test_pipes_catwc_lines(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | wc -l", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]


def test_pipes_catwc_words(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | wc -w", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["5"]


def test_pipes_cat_sort(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | sort", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == sorted(CmdResult.stdout)


def test_pipes_catuniq(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f2.txt | uniq", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat CaT Cat"]


def test_pipes_grep_wc(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | wc -l", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]


def test_pipes_lsgrepwc(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep txt | wc -l", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["2"]


def test_pipes_multiple_grep(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f1.txt | grep cat | grep wolf", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat"]


def test_pipes_head_tail_combo(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command(
        "ls | head --lines=3 | tail --lines=1", shell_fouritems
    )
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f3.txt"]


def test_pipes_ls_grep_no_match(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("ls | grep xyz", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_pipes_empty_chain(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("ls | grep f | wc -l", shell_empty)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["0"]


def test_pipes_long_chain(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command(
        "cat f1.txt | grep cat | sort | head --lines=1 | wc -w", shell_sed
    )
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["3"]


def test_pipes_cat_grep_ignorecase(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("cat f2.txt | grep -i cat", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat CaT Cat"]


def test_pipes_ls_head_wc(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | head --lines=3 | wc -l", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["3"]


def test_pipes_sort_tail(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("ls | sort | tail --lines=1", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["f4.txt"]


def test_blank_input_is_a_noop(cl, shell_basic):
    before = tree_state(shell_basic)
    result = cl.enter_command(" \t ", shell_basic)
    assert result.status == 0
    assert result.stdout == []
    assert result.stderr == []
    assert tree_state(shell_basic) == before


def test_help_loading_does_not_depend_on_process_cwd(
    cl, shell_empty, monkeypatch, tmp_path
):
    from tests.command_helpers import assert_help

    monkeypatch.chdir(tmp_path)
    assert_help(cl, shell_empty, "head")


@pytest.mark.parametrize(
    "command",
    ["|", "&&", "||", "echo |", "echo &&", "echo >", "(", ")", ">", "$"],
)
def test_malformed_shell_syntax_returns_a_command_error(cl, shell_basic, command):
    before = tree_state(shell_basic)
    result = cl.enter_command(command, shell_basic)
    assert result.status != 0
    assert result.stderr
    assert tree_state(shell_basic) == before


def test_unexpected_subshell_exception_restores_shell_state(cl, shell_basic):
    before_tree = tree_state(shell_basic)
    before_vars = shell_basic.vars.copy()
    before_current = shell_basic.fs.current
    before_cwd = shell_basic.cwd
    before_fs_cwd = shell_basic.fs.cwd

    def explode(ctx):
        ctx.system.shell.vars["TEMP"] = "changed"
        ctx.system.shell.cwd = "/changed"
        ctx.system.fs.cwd = "/changed"
        ctx.system.fs.current = ctx.system.fs.filehead
        raise RuntimeError("expected test failure")

    cl.commands["explode"] = explode
    with pytest.raises(RuntimeError, match="expected test failure"):
        cl.enter_command("(explode)", shell_basic)

    assert tree_state(shell_basic) == before_tree
    assert shell_basic.vars == before_vars
    assert shell_basic.fs.current is before_current
    assert shell_basic.cwd == before_cwd
    assert shell_basic.fs.cwd == before_fs_cwd
