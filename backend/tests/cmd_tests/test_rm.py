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
