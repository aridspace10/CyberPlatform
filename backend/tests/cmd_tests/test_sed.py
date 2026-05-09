import pytest

from game.filesystem import FileSystem
from game.ShellState import ShellState
from game.filenode import FileNode
from game.commandline import CommandLine

###### SED ##############
def test_sed_error(cl, shell_empty: ShellState):
    stderr, stdout = cl.enter_command("sed", shell_empty)
    assert stderr == ["sed [OPTION]... {script-only-if-no-other-script} [input-file]..."]
    assert stdout == []

def test_sed_malformed1(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed s/foo f1.txt", shell_basic)
    assert stderr == ["sed: substution expects s/pattern/replacement/"]
    assert stdout == []

def test_sed_malformed2(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed 's/foo/bar' f1.txt", shell_basic)
    assert stderr == ["sed: expected terminating delim"]
    assert stdout == []

def test_sed_malformed3(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed 's/foo/bar/z' f1.txt", shell_basic)
    assert stderr == ["sed: unknown expression flag - z"]
    assert stdout == []

def test_sed_malformed4(cl, shell_basic: ShellState):
    stderr, stdout = cl.enter_command("sed -a 's/foo/bar/' f1.txt", shell_basic)
    assert stderr == ["sed: unknown option given - a"]
    assert stdout == []

def test_sed_basic(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/' f1.txt", shell_sed)
    assert stdout == ["dog wolf cat", "hi dog"]
    assert stderr == []

def test_sed_global(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/g' f1.txt", shell_sed)
    assert stdout == ["dog wolf dog", "hi dog"]
    assert stderr == []

def test_sed_nochange(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/not/exist/' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf cat", "hi cat"]

def test_sed_emreplace(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat//' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == [" wolf dog", "hi "]

def test_sed_alternatedelim(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's|cat|dog|g' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf cat\nhi cat"]

    stderr, stdout = cl.enter_command("sed 's#cat#dog#' f1.txt", shell_sed)
    assert stderr == []
    assert stdout == ["cat wolf dog", "hi cat"]

def test_sed_noccurences(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/2' f1.txt", shell_sed)
    assert stdout == ["cat wolf dog", "hi cat"]
    assert stderr == []

def test_sed_cinsentive(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed 's/cat/dog/Ig' f2.txt", shell_sed)
    assert stdout == ["dog wolf dog", "hi dog"]
    assert stderr == []

def test_sed_addressing(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed '2s/cat/dog/' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat\nhi dog"]
    assert stderr == []

    stderr, stdout = cl.enter_command("sed '$s/cat/dog/' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat", "hi dog"]
    assert stderr == []

def test_sed_addressing2(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed '2,4s/cat/dog/' f3.txt", shell_sed)
    assert stdout == ["cat wolf cat", "hi dog", "whats up", " the dog", " test cat here"]
    assert stderr == []

def test_sed_delete(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed '2d' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat"]
    assert stderr == []

    stderr, stdout = cl.enter_command("sed '$d' f1.txt", shell_sed)
    assert stdout == ["cat wolf cat"]
    assert stderr == []

    stderr, stdout = cl.enter_command("sed '2,4d' f3.txt", shell_sed)
    assert stdout == ["cat wolf cat", " test cat here"]
    assert stderr == []

def test_sed_multexpr(cl, shell_sed: ShellState):
    stderr, stdout = cl.enter_command("sed -e 's/cat/dog/' -e 's/wolf/howl/ f1.txt", shell_sed)
    assert stdout == ["dog howl cat", "hi dog"]
    assert stderr == []

def test_sed_print_flag(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -n 's/cat/dog/p' f1.txt",
        shell_sed
    )
    assert stderr == []
    assert stdout == [
        "dog wolf cat",
        "hi dog"
    ]

def test_sed_print_flag_no_match(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -n 's/bird/fish/p' f1.txt",
        shell_sed
    )
    assert stderr == []
    assert stdout == []

def test_sed_expression_order(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -e 's/cat/dog/' -e 's/dog/wolf/' f1.txt",
        shell_sed
    )

    assert stderr == []
    assert stdout == [
        "wolf wolf cat",
        "hi wolf"
    ]

def test_sed_case_insensitive_single(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed 's/cat/dog/I' f2.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "dog CaT Cat"
    ]

def test_sed_delete_blank_lines(cl, shell_sed):
    shell_sed.fs.add_file("blank.txt")
    shell_sed.fs.current.items[0].set_data(["a", "", "b", "", "c"])

    stderr, stdout = cl.enter_command(
      r"sed '/^$/d' blank.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "a","b","c"
    ]

def test_sed_path_delimiters(cl, shell_sed):
    shell_sed.fs.add_file("path.txt")
    shell_sed.fs.current.items[0].set_data(["/usr/bin"])

    stderr, stdout = cl.enter_command(
      "sed 's|/usr/bin|/opt/bin|' path.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "/opt/bin"
    ]

def test_sed_empty_file(cl, shell_sed):
    shell_sed.fs.add_file("empty.txt")

    stderr, stdout = cl.enter_command(
      "sed 's/cat/dog/' empty.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == []
  
def test_sed_expression_order_changes_result(cl, shell_sed):
    stderr, stdout = cl.enter_command(
        "sed -e 's/dog/wolf/' -e 's/cat/dog/' f1.txt",
        shell_sed
    )

    assert stderr == []
    assert stdout == [
        "dog wolf dog",
        "hi dog"
    ]

def test_sed_reverse_range(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed '5,2d' f3.txt",
      shell_sed
    )

    assert stderr == []

def test_sed_bad_address(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed 'x,4d' f1.txt",
      shell_sed
    )

    assert stdout == []
    assert stderr == ["sed: expected int, got x,4"]

def test_sed_inplace_backup(cl, shell_sed):
    old = shell_sed.fs.get_file("f1.txt").get_data()
    stderr, stdout = cl.enter_command(
      "sed -i.bak 's/cat/dog/g' f1.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == []
    fn = shell_sed.fs.get_file("f1.txt.bak")
    print (shell_sed.fs.current.items)
    assert isinstance(fn, FileNode)
    assert fn.get_data() == old
    new = shell_sed.fs.get_file("f1.txt")
    assert isinstance(new, FileNode)
    assert new.get_data() == ["dog wolf dog","hi dog"]
    

def test_sed_overlapping(cl, shell_sed):
    shell_sed.fs.current.items[0].set_data(["aaaa"])

    stderr, stdout = cl.enter_command(
      "sed 's/aa/b/g' f1.txt",
      shell_sed
    )

    assert stdout == ["bb"]

def test_sed_negated_line_address(cl, shell_sed):
    stderr, stdout = cl.enter_command(
      "sed '2!d' f1.txt",
      shell_sed
    )

    assert stderr == []
    assert stdout == [
      "hi cat"
    ]