from game.Process import ProcessState
from game.ShellState import ShellState


def test_rm_basic(cl, shell_fouritems: ShellState):
    CmdResult = cl.enter_command("rm f2.txt", shell_fouritems)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    assert len(shell_fouritems.fs.current.items) == 3


def test_rm_dir(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("rm d1", shell_basic)
    assert len(shell_basic.fs.current.items) == 3
    assert CmdResult.stderr == ["rm: cannot remove 'd1': Is a directory"]
    assert CmdResult.stdout == []
    CmdResult = cl.enter_command("rm -r d1", shell_basic)
    assert len(shell_basic.fs.current.items) == 2
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_rm_interactive_recursive_expands_nested_targets(cl, shell_basic: ShellState):
    result = cl.enter_command("rm -ri d1", shell_basic)
    assert result.stderr == []
    assert result.interaction is not None
    assert result.interaction.prompt == "rm: remove regular file 'd1/f3.txt'?"

    pid = shell_basic.foreground_pid
    assert pid is not None
    process = cl.process_manager.get_process(pid)
    assert process is not None
    assert process.program is not None

    expected_prompts = [
        "rm: remove regular file 'd1/f4.txt'?",
        "rm: remove directory 'd1'?",
    ]
    for prompt in expected_prompts:
        stdout, stderr = process.program.receive_input("yes")
        assert stdout == []
        assert stderr == []
        assert process.program.prompt == prompt

    stdout, stderr = process.program.receive_input("yes")
    assert stdout == []
    assert stderr == []
    assert process.status == ProcessState.TERMINATED
    assert shell_basic.fs.get_file("d1") is None


def test_rm_interactive_missing_file_finishes_without_blocking(cl, shell_empty):
    result = cl.enter_command("rm -i missing.txt", shell_empty)
    assert result.status == 1
    assert result.interaction is None
    assert shell_empty.foreground_pid is None
    assert result.stderr == ["rm: cannot remove 'missing.txt': No such file"]


def test_rm_interactive_rejected_child_preserves_directory(cl, shell_basic):
    result = cl.enter_command("rm -ri d1", shell_basic)
    assert result.interaction is not None

    pid = shell_basic.foreground_pid
    assert pid is not None
    process = cl.process_manager.get_process(pid)
    assert process is not None
    assert process.program is not None

    process.program.receive_input("no")
    process.program.receive_input("yes")
    _stdout, stderr = process.program.receive_input("yes")

    assert stderr == ["rm: cannot remove 'd1': Directory not empty"]
    directory = shell_basic.fs.get_file("d1")
    assert directory is not None
    assert not isinstance(directory, str)
    assert [item.name for item in directory.items] == ["f3.txt"]


def test_rm_nested_delete_restores_filesystem_pointer(cl, shell_basic: ShellState):
    assert shell_basic.fs.search("d1") == ""
    directory = shell_basic.fs.current

    result = cl.enter_command("rm f3.txt", shell_basic)

    assert result.stderr == []
    assert shell_basic.fs.current is directory
    assert shell_basic.fs.get_file("f3.txt") is None
