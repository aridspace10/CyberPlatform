import json
import random

import pytest
from game.commandline import CommandResult
from game.Context import ExecutionContext, SystemContext
from game.filenode import FileNode
from game.filesystem import FileSystem
from game.inode import Inode
from game.InputBuffer import InputBuffer
from game.Parser import CommandParser, lex
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import descendants, tree_state
from tests.command_helpers import setup_names
from tests.filesystem_helpers import restored_filesystem


@pytest.mark.parametrize("supplied", [None, InputBuffer(), InputBuffer(("value",))])
def test_command_setup_preserves_explicit_input(cl, shell_empty, supplied):
    received = []

    def probe(ctx):
        received.append(ctx.stdin)
        return CommandResult()

    cl.commands["probe"] = probe
    command = CommandParser(lex("probe")).parse().parts[0].pipeline.parts[0].first
    system = SystemContext(shell_empty.fs, cl.process_manager, cl.network, shell_empty)
    execution = ExecutionContext(stdin=supplied)
    cl.execute_command(command, system, execution)

    assert execution.stdin is supplied
    assert len(received) == 1
    if supplied is None:
        assert received[0] == InputBuffer()
    else:
        assert received[0] is supplied


@pytest.mark.parametrize("lines", [[], [""], ["cat", "", "wolf"]])
def test_pipeline_keeps_explicit_empty_input_and_snapshots_output(
    cl, shell_empty, monkeypatch, lines
):
    setup_inputs = []
    execute_andor = cl.execute_andor

    def record_setup(elem, system, execution):
        setup_inputs.append(execution.stdin)
        return execute_andor(elem, system, execution)

    def emit(ctx):
        return CommandResult(stdout=lines)

    def probe(ctx):
        assert ctx.stdin is setup_inputs[-1]
        assert ctx.stdin.lines == tuple(lines)
        assert ctx.stdin.has_trailing_newline is bool(lines)
        lines.append("changed upstream")
        assert "changed upstream" not in ctx.stdin.lines
        return CommandResult(stdout=list(ctx.stdin.lines))

    monkeypatch.setattr(cl, "execute_andor", record_setup)
    cl.commands.update(emit=emit, probe=probe)
    expected = list(lines)
    assert_success(cl.enter_command("emit | probe", shell_empty), expected)
    assert setup_inputs[0] is None
    assert isinstance(setup_inputs[1], InputBuffer)


@pytest.mark.parametrize("command", ["probe", "probe | probe", "probe < f1.txt"])
def test_reading_stdin_never_constructs_filesystem_nodes(
    cl, shell_basic, monkeypatch, command
):
    def unexpected_allocation(*args, **kwargs):
        pytest.fail("stdin allocated a filesystem node")

    def probe(ctx):
        assert isinstance(ctx.stdin, InputBuffer)
        return CommandResult(stdout=list(ctx.stdin.lines))

    monkeypatch.setattr(Inode, "__init__", unexpected_allocation)
    monkeypatch.setattr(FileNode, "__init__", unexpected_allocation)
    cl.commands["probe"] = probe
    result = cl.enter_command(command, shell_basic)
    assert result.status == 0
    assert result.stderr == []


@pytest.mark.parametrize("lines", [[], [""], ["cat", "", "wolf"]])
def test_heredoc_uses_an_immutable_buffer_without_allocating_nodes(
    cl, shell_empty, monkeypatch, lines
):
    received = []

    def unexpected_allocation(*args, **kwargs):
        pytest.fail("heredoc allocated a filesystem node")

    def probe(ctx):
        received.append(ctx.stdin)
        return CommandResult(stdout=list(ctx.stdin.lines))

    monkeypatch.setattr(Inode, "__init__", unexpected_allocation)
    monkeypatch.setattr(FileNode, "__init__", unexpected_allocation)
    cl.commands["probe"] = probe
    result = cl.enter_command("probe << EOF", shell_empty)
    assert result.interaction is not None
    program = cl.process_manager.get_process(shell_empty.foreground_pid).program
    for line in lines:
        assert program.receive_input(line) == ([], [])
    assert program.receive_input("EOF") == (lines, [])
    assert received == [InputBuffer.from_lines(lines)]
    program.lines.append("changed after completion")
    assert received[0].lines == tuple(lines)


@pytest.mark.parametrize(
    "target", ["missing.txt", "d1/missing.txt", "d1", ".", "f1.txt/missing.txt"]
)
def test_failed_input_redirection_never_invokes_handler_or_creates_file(
    cl, shell_basic, target
):
    before = tree_state(shell_basic)
    current = shell_basic.fs.current
    next_inode = Inode._next_id

    def probe(ctx):
        pytest.fail("handler invoked after an input-open failure")

    cl.commands["probe"] = probe
    result = cl.enter_command(f"probe < {target}", shell_basic)
    assert_failure(result)
    assert result.stdout == []
    assert result.stderr
    assert tree_state(shell_basic) == before
    assert shell_basic.fs.current is current
    assert Inode._next_id == next_inode


def test_permission_bits_are_metadata_for_reads_writes_and_directory_operations(
    cl, shell_basic
):
    shell_basic.fs.get_file("d1/f3.txt").set_data(["nested content"])
    assert_success(cl.enter_command("chmod 000 f1.txt", shell_basic))
    assert_success(
        cl.enter_command("cat f1.txt", shell_basic),
        ["ERROR no", "INFO hey", "ERROR no2", "error 1"],
    )
    assert_success(cl.enter_command("ln -s f1.txt f1-link.txt", shell_basic))
    assert_success(
        cl.enter_command("cat f1-link.txt", shell_basic),
        ["ERROR no", "INFO hey", "ERROR no2", "error 1"],
    )
    assert_success(cl.enter_command("echo changed > f1.txt", shell_basic))
    assert shell_basic.fs.get_file("f1.txt").get_data() == ["changed"]

    assert_success(cl.enter_command("chmod -R 000 d1", shell_basic))
    assert_success(
        cl.enter_command("cat d1/f3.txt", shell_basic), ["nested content"]
    )
    assert_success(cl.enter_command("touch d1/new.txt", shell_basic))
    assert shell_basic.fs.get_file("d1/new.txt") is not None
    assert_success(cl.enter_command("rm d1/f3.txt", shell_basic))
    assert shell_basic.fs.get_file("d1/f3.txt") is None


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


def test_input_redirection_after_output_redirect_is_isolated(cl, shell_basic):
    source = shell_basic.fs.resolve("f1.txt")

    result = cl.enter_command("echo first > out.txt && cat < f1.txt", shell_basic)

    assert_success(result, list(source.inode.data))
    output = shell_basic.fs.resolve("out.txt")
    assert output.inode.data == ["first"]
    assert output.inode.has_trailing_newline


def test_input_redirection_does_not_leak_to_next_command(cl, shell_basic):
    source = shell_basic.fs.resolve("f1.txt")

    result = cl.enter_command("cat < f1.txt && cat -", shell_basic)

    assert_success(result, list(source.inode.data))


@pytest.mark.parametrize("target", ["d1", ".", "d1/", "missing/file", "f1.txt/file"])
@pytest.mark.parametrize("operator", [">", ">>"])
def test_output_redirection_rejects_invalid_targets_without_mutation(
    cl, shell_basic, target, operator
):
    before = tree_state(shell_basic)
    current = shell_basic.fs.current

    result = cl.enter_command(f"echo changed {operator} {target}", shell_basic)

    assert_failure(result)
    assert result.stderr
    assert tree_state(shell_basic) == before
    assert shell_basic.fs.current is current


@pytest.mark.parametrize("operator", [">", ">>"])
def test_output_redirection_rejects_directory_symlink_without_mutation(
    cl, shell_basic, operator
):
    assert_success(cl.enter_command("ln -s d1 dirlink", shell_basic))
    before = tree_state(shell_basic)

    result = cl.enter_command(f"echo changed {operator} dirlink", shell_basic)

    assert_failure(result)
    assert tree_state(shell_basic) == before


def test_output_redirection_follows_regular_file_symlink(cl, shell_basic):
    assert_success(cl.enter_command("ln -s f1.txt filelink", shell_basic))
    target = shell_basic.fs.resolve("f1.txt")

    assert_success(cl.enter_command("echo replacement > filelink", shell_basic))

    assert target.inode.data == ["replacement"]
    assert target.inode.has_trailing_newline is True
    link = shell_basic.fs.get_file("filelink")
    assert link.inode.data == ["f1.txt"]


def test_multiple_output_redirects_apply_in_order(cl, shell_basic):
    first = shell_basic.fs.resolve("f1.txt")

    result = cl.enter_command("echo final > f1.txt > second.txt", shell_basic)

    assert_success(result)
    assert first.inode.data == []
    assert first.inode.has_trailing_newline is False
    second = shell_basic.fs.resolve("second.txt")
    assert second.inode.data == ["final"]
    assert second.inode.has_trailing_newline is True


def test_mixed_redirections_use_final_input_and_output(cl, shell_basic):
    source = shell_basic.fs.resolve("f1.txt")
    expected = list(source.inode.data)

    result = cl.enter_command("cat < f2.txt < f1.txt > out.txt", shell_basic)

    assert_success(result)
    output = shell_basic.fs.resolve("out.txt")
    assert output.inode.data == expected
    assert output.inode.has_trailing_newline is True


def test_truncate_and_append_empty_output_preserve_correct_newline_state(cl, shell_basic):
    target = shell_basic.fs.resolve("f1.txt")

    assert_success(cl.enter_command("cat - > f1.txt", shell_basic))
    assert target.inode.data == []
    assert target.inode.has_trailing_newline is False

    target.set_data(["unfinished"])
    target.inode.has_trailing_newline = False
    assert_success(cl.enter_command("cat - >> f1.txt", shell_basic))
    assert target.inode.data == ["unfinished"]
    assert target.inode.has_trailing_newline is False


def test_append_updates_newline_state_and_joins_unterminated_line(cl, shell_basic):
    target = shell_basic.fs.resolve("f1.txt")
    target.set_data(["unfinished"])
    target.inode.has_trailing_newline = False

    assert_success(cl.enter_command("echo tail >> f1.txt", shell_basic))
    assert target.inode.data == ["unfinishedtail"]
    assert target.inode.has_trailing_newline is True

    assert_success(cl.enter_command("echo abc >> new.txt", shell_basic))
    assert_success(cl.enter_command("wc -l new.txt", shell_basic), ["1"])


def test_subshell_inherits_redirected_and_pipeline_input(cl, shell_basic):
    source = shell_basic.fs.resolve("f1.txt")
    expected = list(source.inode.data)

    assert_success(cl.enter_command("(cat -) < f1.txt", shell_basic), expected)
    assert_success(cl.enter_command("cat f1.txt | (cat -)", shell_basic), expected)


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
    CmdResult = cl.enter_command("echo before; cd d1; echo after; ls", shell_basic)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["before", "after", "f3.txt", "f4.txt"]
    assert shell_basic.cwd == "/d1"


@pytest.mark.integration
def test_shell_copy_then_write_preserves_source_and_rereads_copy(cl, shell_fouritems):
    source = shell_fouritems.fs.resolve("f1.txt")
    source_inode = source.inode
    original = list(source.inode.data)

    result = cl.enter_command(
        "cp f1.txt copy.txt; echo independent > copy.txt; cat copy.txt; cat f1.txt",
        shell_fouritems,
    )

    copied = shell_fouritems.fs.resolve("copy.txt")
    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["independent", *original]
    assert copied.inode is not source_inode
    assert copied.inode.data == ["independent"]
    assert source.inode.data == original


@pytest.mark.integration
def test_shell_failed_lookup_does_not_suppress_following_command(cl, shell_basic):
    original_cwd = shell_basic.fs.current

    result = cl.enter_command("cat missing.txt; echo recovered", shell_basic)

    assert result.status == 0
    assert result.stdout == ["recovered"]
    assert result.stderr == ["File missing.txt does not exist"]
    assert shell_basic.fs.current is original_cwd


@pytest.mark.integration
def test_shell_sed_then_sort_and_cat_reread_persisted_contents(cl, shell_empty):
    shell_empty.fs.add_file("source.txt")
    source = shell_empty.fs.resolve("source.txt")
    source.set_data(["zeta", "alpha"])

    result = cl.enter_command(
        "sed -i 's/zeta/omega/' source.txt; sort source.txt; cat source.txt",
        shell_empty,
    )

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["alpha", "omega", "omega", "alpha"]
    assert source.inode.data == ["omega", "alpha"]


@pytest.mark.integration
def test_shell_copy_and_edit_state_survives_filesystem_roundtrip(cl, shell_fouritems):
    source = shell_fouritems.fs.resolve("f1.txt")
    original = list(source.inode.data)
    result = cl.enter_command(
        "cp f1.txt copy.txt; echo persisted > copy.txt", shell_fouritems
    )
    assert result.status == 0
    assert result.stdout == []
    assert result.stderr == []

    restored = restored_filesystem(shell_fouritems.fs)
    restored_source = restored.resolve("f1.txt")
    restored_copy = restored.resolve("copy.txt")
    assert restored_source.inode.data == original
    assert restored_copy.inode.data == ["persisted"]
    assert restored_source.inode is not restored_copy.inode


def test_sequence_accumulates_output_and_diagnostics(cl, shell_basic):
    result = cl.enter_command("echo first; echo second", shell_basic)
    assert result.status == 0
    assert result.stdout == ["first", "second"]
    assert result.stderr == []

    result = cl.enter_command("cat missing; echo okay", shell_basic)
    assert result.status == 0
    assert result.stdout == ["okay"]
    assert result.stderr == ["File missing does not exist"]


def test_andor_skips_only_ineligible_branch(cl, shell_basic):
    result = cl.enter_command(
        "cat missing && echo skip || echo recovered", shell_basic
    )

    assert result.status == 0
    assert result.stdout == ["recovered"]
    assert result.stderr == ["File missing does not exist"]


def test_pipeline_preserves_upstream_diagnostics_and_final_status(cl, shell_basic):
    result = cl.enter_command("cat missing | cat", shell_basic)

    assert result.status == 0
    assert result.stdout == []
    assert result.stderr == ["File missing does not exist"]


def test_subshell_inherits_pipeline_stdin_and_restores_nested_cwd(cl, shell_basic):
    result = cl.enter_command("cat f1.txt | (cat)", shell_basic)
    assert result.stdout == ["ERROR no", "INFO hey", "ERROR no2", "error 1"]
    assert result.stderr == []

    result = cl.enter_command("cd d1; ((cd ..; pwd)); pwd", shell_basic)
    assert result.status == 0
    assert result.stdout == ["root", "root/d1"]
    assert shell_basic.fs.current is shell_basic.fs.filehead.access("d1")


def test_last_status_expansion_tracks_previous_command(cl, shell_basic):
    failed = cl.enter_command("cat missing", shell_basic)
    assert failed.status == 1

    status = cl.enter_command("echo $?", shell_basic)
    assert status.status == 0
    assert status.stdout == ["1"]
    assert status.stderr == []


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
