import pytest
from game.filenode import FileNode
from game.ShellState import ShellState
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.cmd_tests.path_helpers import assert_directory_error
from tests.command_helpers import assert_help


@pytest.mark.parametrize(
    ("lines", "expected"),
    [([], []), (["cat cat", "", "wolf"], ["dog dog", "", "wolf"])],
)
def test_sed_buffered_input(run_buffered_command, lines, expected):
    assert_success(run_buffered_command("sed 's/cat/dog/g'", lines), expected)


@pytest.mark.parametrize("input_args", ["", "-", "< f1.txt"])
def test_sed_in_place_rejects_stdin_without_editing_file(cl, shell_sed, input_args):
    from tests.command_helpers import assert_command_error_without_mutation

    result = assert_command_error_without_mutation(
        cl, shell_sed, f"sed -i.bak 's/cat/dog/g' {input_args}"
    )
    assert result.stderr == ["sed: cannot edit standard input in place"]


###### SED ##############
def test_sed_error(cl, shell_empty: ShellState):
    CmdResult = cl.enter_command("sed", shell_empty)
    assert CmdResult.stderr == [
        "sed [OPTION]... {script-only-if-no-other-script} [input-file]..."
    ]
    assert CmdResult.stdout == []


def test_sed_malformed1(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("sed s/foo f1.txt", shell_basic)
    assert CmdResult.stderr == ["sed: substution expects s/pattern/replacement/"]
    assert CmdResult.stdout == []


def test_sed_malformed2(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("sed 's/foo/bar' f1.txt", shell_basic)
    assert CmdResult.stderr == ["sed: expected terminating delim"]
    assert CmdResult.stdout == []


def test_sed_malformed3(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("sed 's/foo/bar/z' f1.txt", shell_basic)
    assert CmdResult.stderr == ["sed: unknown expression flag - z"]
    assert CmdResult.stdout == []


def test_sed_malformed4(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("sed -a 's/foo/bar/' f1.txt", shell_basic)
    assert CmdResult.stderr == ["sed: unknown option given - a"]
    assert CmdResult.stdout == []


def test_sed_malformed5(cl, shell_basic: ShellState):
    CmdResult = cl.enter_command("sed 's/foo/bar/' not_exist.txt", shell_basic)
    assert CmdResult.stderr == ["sed: No directory named not_exist.txt"]
    assert CmdResult.stdout == []


def test_sed_invalid_regex_does_not_create_backup_or_mutate_file(cl, shell_basic):
    source = shell_basic.fs.get_file("f1.txt")
    before = list(source.get_data())
    result = cl.enter_command("sed -i.bak 's/[(/x/' f1.txt", shell_basic)
    assert result.status != 0
    assert result.stderr
    assert source.get_data() == before
    assert shell_basic.fs.get_file("f1.txt.bak") is None


def test_sed_empty_expression_is_a_command_error(cl, shell_basic):
    result = cl.enter_command('sed ""', shell_basic)
    assert result.status != 0
    assert result.stderr


def test_sed_basic(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed 's/cat/dog/' f1.txt", shell_sed)
    assert CmdResult.stdout == ["dog wolf cat", "hi dog"]
    assert CmdResult.stderr == []


def test_sed_global(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed -e 's/cat/dog/g' f1.txt", shell_sed)
    assert CmdResult.stdout == ["dog wolf dog", "hi dog"]
    assert CmdResult.stderr == []


def test_sed_nochange(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed -e 's/not/exist/' f1.txt", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat", "hi cat"]


def test_sed_reads_script_file_separately_from_input(cl, shell_sed):
    shell_sed.fs.add_file("script.sed")
    shell_sed.fs.get_file("script.sed").set_data(["s/cat/dog/g"])

    result = cl.enter_command("sed -f script.sed f1.txt", shell_sed)

    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["dog wolf dog", "hi dog"]


def test_sed_explicit_stdin_operand(cl, shell_empty):
    result = cl.enter_command("sed -e 's/cat/dog/' -", shell_empty)
    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == []


def test_sed_emreplace(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed 's/cat//' f1.txt", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == [" wolf cat", "hi "]


def test_sed_alternatedelim(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed 's|cat|dog|g' f1.txt", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["dog wolf dog", "hi dog"]


def test_sed_noccurences(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed 's/cat/dog/2' f1.txt", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf dog", "hi cat"]


def test_sed_second_occurrence_global_multiple(cl, shell_sed):
    CmdResult = cl.enter_command(r"sed 's/cat/dog/2g' many.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat dog dog dog"]


def test_sed_cinsentive(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed 's/cat/dog/Ig' f2.txt", shell_sed)
    assert CmdResult.stdout == ["dog dog dog"]
    assert CmdResult.stderr == []


def test_sed_addressing(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed '2s/cat/dog/' f1.txt", shell_sed)
    assert CmdResult.stdout == ["cat wolf cat", "hi dog"]
    assert CmdResult.stderr == []

    CmdResult = cl.enter_command("sed '$s/cat/dog/' f1.txt", shell_sed)
    assert CmdResult.stdout == ["cat wolf cat", "hi dog"]
    assert CmdResult.stderr == []


def test_sed_regex_address_miss_does_not_substitute(cl, shell_sed):
    result = cl.enter_command("sed '/NOMATCH/s/cat/dog/' f1.txt", shell_sed)
    assert result.status == 0
    assert result.stderr == []
    assert result.stdout == ["cat wolf cat", "hi cat"]

def test_sed_addressing2(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed '2,4s/cat/dog/' f3.txt", shell_sed)
    assert CmdResult.stdout == [
        "cat wolf cat",
        "hi dog",
        " whats up",
        " the dog",
        " test cat here",
    ]
    assert CmdResult.stderr == []


def test_sed_delete(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command("sed '2d' f1.txt", shell_sed)
    assert CmdResult.stdout == ["cat wolf cat"]
    assert CmdResult.stderr == []

    CmdResult = cl.enter_command("sed '$d' f1.txt", shell_sed)
    assert CmdResult.stdout == ["cat wolf cat"]
    assert CmdResult.stderr == []

    CmdResult = cl.enter_command("sed '2,4d' f3.txt", shell_sed)
    assert CmdResult.stdout == ["cat wolf cat", " test cat here"]
    assert CmdResult.stderr == []


def test_sed_multexpr(cl, shell_sed: ShellState):
    CmdResult = cl.enter_command(
        "sed --expression=s/cat/dog/ -e 's/wolf/howl/' f1.txt", shell_sed
    )
    assert CmdResult.stdout == ["dog howl cat", "hi dog"]
    assert CmdResult.stderr == []


def test_sed_print_flag(cl, shell_sed):
    CmdResult = cl.enter_command("sed -n 's/cat/dog/p' f1.txt", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["dog wolf cat", "hi dog"]


def test_sed_print_flag_no_match(cl, shell_sed):
    CmdResult = cl.enter_command("sed -n 's/bird/fish/p' f1.txt", shell_sed)
    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_sed_substitution_print_flag_with_default_output(cl, shell_sed):
    result = cl.enter_command("sed 's/cat/dog/p' f1.txt", shell_sed)
    assert result.status == 0
    assert result.stdout == ["dog wolf cat", "dog wolf cat", "hi dog", "hi dog"]


def test_sed_expression_order(cl, shell_sed):
    CmdResult = cl.enter_command(
        "sed -e 's/cat/dog/' -e 's/dog/wolf/' f1.txt", shell_sed
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["wolf wolf cat", "hi wolf"]


def test_sed_case_insensitive_single(cl, shell_sed):
    CmdResult = cl.enter_command("sed 's/cat/dog/I' f2.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["dog CaT Cat"]


def test_sed_delete_blank_lines(cl, shell_sed):
    shell_sed.fs.add_file("blank.txt")
    fn = shell_sed.fs.get_file("blank.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["a", "", "b", "", "c"])

    CmdResult = cl.enter_command(r"sed '/^$/d' blank.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["a", "b", "c"]


def test_sed_path_delimiters(cl, shell_sed):
    shell_sed.fs.add_file("path.txt")
    fn = shell_sed.fs.get_file("path.txt")
    assert isinstance(fn, FileNode)
    fn.set_data(["/usr/bin"])

    CmdResult = cl.enter_command("sed 's|/usr/bin|/opt/bin|' path.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["/opt/bin"]


def test_sed_empty_file(cl, shell_sed):
    shell_sed.fs.add_file("empty.txt")

    CmdResult = cl.enter_command("sed 's/cat/dog/' empty.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []


def test_sed_expression_order_changes_result(cl, shell_sed):
    CmdResult = cl.enter_command(
        "sed -e 's/dog/wolf/' -e 's/cat/dog/' f1.txt", shell_sed
    )

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["dog wolf cat", "hi dog"]


def test_sed_reverse_range(cl, shell_sed):
    CmdResult = cl.enter_command("sed '5,2d' f3.txt", shell_sed)

    assert CmdResult.stderr == []


def test_sed_bad_address(cl, shell_sed):
    CmdResult = cl.enter_command("sed 'x,4d' f1.txt", shell_sed)

    assert CmdResult.stdout == []
    assert CmdResult.stderr == ["sed: expected int, got x,4"]


def test_sed_inplace_backup(cl, shell_sed):
    old = shell_sed.fs.get_file("f1.txt").get_data()
    CmdResult = cl.enter_command("sed -i.bak 's/cat/dog/g' f1.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == []
    fn = shell_sed.fs.get_file("f1.txt.bak")
    print(shell_sed.fs.current.items)
    assert isinstance(fn, FileNode)
    assert fn.get_data() == old
    new = shell_sed.fs.get_file("f1.txt")
    assert isinstance(new, FileNode)
    assert new.get_data() == ["dog wolf dog", "hi dog"]


def test_sed_overlapping(cl, shell_sed):
    shell_sed.fs.current.items[0].set_data(["aaaa"])

    CmdResult = cl.enter_command("sed 's/aa/b/g' f1.txt", shell_sed)

    assert CmdResult.stdout == ["bb"]


def test_sed_negated_line_address(cl, shell_sed):
    CmdResult = cl.enter_command("sed '2!d' f1.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hi cat"]


def test_sed_print_command(cl, shell_sed):
    CmdResult = cl.enter_command(r"sed -n 'p' f1.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat", "hi cat"]


def test_sed_print_single_line(cl, shell_sed):
    CmdResult = cl.enter_command(r"sed -n '2p' f1.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hi cat"]


def test_sed_print_range(cl, shell_sed):
    CmdResult = cl.enter_command(r"sed -n '2,4p' f3.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["hi cat", " whats up", " the cat"]


def test_sed_print_regex(cl, shell_sed):
    CmdResult = cl.enter_command(r"sed -n '/wolf/p' f1.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat"]


def test_sed_print_last_line(cl, shell_sed):
    CmdResult = cl.enter_command(r"sed -n '$p' f3.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == [" test cat here"]


def test_sed_print_negated_line(cl, shell_sed):
    CmdResult = cl.enter_command(r"sed -n '2!p' f1.txt", shell_sed)

    assert CmdResult.stderr == []
    assert CmdResult.stdout == ["cat wolf cat"]


def test_sed_help(cl, shell_empty):
    assert_help(cl, shell_empty, "sed")


def test_sed_dot_paths_read_file(run_dot_command, dot_prefix):
    result = run_dot_command(f"sed -n p {dot_prefix}data.txt")
    assert_success(result, ["beta:2", "alpha:1", "alpha:1"])


def test_sed_dot_paths_reject_directory(run_dot_command, dot_directory):
    operand, _ = dot_directory
    result = run_dot_command(f"sed -n p {operand}")
    assert_directory_error(result)


def test_sed_dot_paths_reject_invalid_traversal(run_dot_command, invalid_dot_path):
    result = run_dot_command(f"sed -n p {invalid_dot_path}")
    assert_failure(result)


def test_sed_dot_paths_preserve_literal_dot_names(run_dot_command):
    result = run_dot_command("sed -n p ./..backup")
    assert_success(result, ["literal:5"])


def test_sed_dot_paths_in_place_edit(run_dot_command, dot_shell, dot_prefix):
    source = dot_shell.fs.current.access("data.txt")
    result = run_dot_command(
        f"sed -i 's/beta/BETA/' {dot_prefix}data.txt", unchanged=False
    )
    assert source.inode.data == ["BETA:2", "alpha:1", "alpha:1"]
    assert result.status == 0
    assert result.stderr == []


def test_sed_dot_paths_read_parent_file(run_dot_command, dot_shell):
    current = dot_shell.fs.current
    parent = current.parent if current.parent is not None else current
    lines = list(parent.access("data.txt").inode.data)
    result = run_dot_command("sed -n p ../data.txt")
    assert_success(result, lines)
