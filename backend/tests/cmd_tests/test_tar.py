"""Tests for creating byte-exact tar archives in the simulated filesystem."""

from io import BytesIO
import tarfile

from game.filenode import FileNode
from tests.cmd_tests.creation_helpers import assert_failure, assert_success
from tests.command_helpers import assert_help


def test_tar_create_preserves_binary_files_and_multiple_operands(cl, shell_empty):
    fs = shell_empty.fs
    fs.add_file("binary.dat")
    fs.add_file("notes.txt")
    binary = fs.get_file("binary.dat")
    notes = fs.get_file("notes.txt")
    assert isinstance(binary, FileNode)
    assert isinstance(notes, FileNode)
    payload = b"\x00\xff\n" + b"x" * 512
    binary.inode.set_byte_data(payload)
    notes.set_data(["first", "second"])

    assert_success(
        cl.enter_command("tar -cf bundle.tar binary.dat notes.txt", shell_empty)
    )

    archive = fs.get_file("bundle.tar")
    assert isinstance(archive, FileNode)
    assert archive.inode.data.endswith(b"\0" * 1024)
    with tarfile.open(fileobj=BytesIO(archive.inode.get_byte_data()), mode="r:") as tar:
        assert tar.getnames() == ["binary.dat", "notes.txt"]
        assert tar.extractfile("binary.dat").read() == payload
        assert tar.extractfile("notes.txt").read() == b"first\nsecond\n"


def test_tar_rejects_missing_inputs_without_creating_archive(cl, shell_empty):
    result = cl.enter_command("tar -cf bundle.tar missing.dat", shell_empty)

    assert_failure(result)
    assert shell_empty.fs.get_file("bundle.tar") is None


def test_tar_verbose_lists_added_files(cl, shell_empty):
    shell_empty.fs.add_file("note.txt")

    result = cl.enter_command("tar -cvf bundle.tar note.txt", shell_empty)

    assert_success(result, ["note.txt"])


def test_tar_help(cl, shell_empty):
    assert_help(cl, shell_empty, "tar")
