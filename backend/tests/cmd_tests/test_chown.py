from game.identity import EffectiveIdentity
from game.ShellState import ShellState
from game.filesystem import FileSystem
from tests.cmd_tests.creation_helpers import assert_failure, assert_success


def test_chown_requires_privileged_identity(cl, shell_basic):
    shell_basic.identity = EffectiveIdentity("alice", "users", frozenset({"users"}))

    result = cl.enter_command("chown bob:staff f1.txt", shell_basic)

    assert_failure(result)
    assert result.stderr == ["chown: Operation not permitted"]
    node = shell_basic.fs.filehead.access("f1.txt")
    assert (node.inode.owner, node.inode.group) == ("user", "user")


def test_client_supplied_root_username_does_not_grant_privilege(cl, shell_basic):
    shell_basic.identity = EffectiveIdentity.for_session("root", "0")
    node = shell_basic.fs.filehead.access("f1.txt")
    node.inode.owner = "root"
    node.inode.group = "root"
    node.inode.permissions = {
        "user": {"r": True, "w": True, "x": True},
        "group": {"r": False, "w": False, "x": False},
        "public": {"r": False, "w": False, "x": False},
    }

    result = cl.enter_command("cat f1.txt", shell_basic)

    assert shell_basic.identity.username == "untrusted-root"
    assert not shell_basic.identity.privileged
    assert_failure(result)


def test_root_chown_updates_owner_group_and_long_listing(cl, shell_basic):
    shell_basic.identity = EffectiveIdentity("root", "root", frozenset({"root"}), True)

    result = cl.enter_command("chown alice:staff f1.txt", shell_basic)
    listing = cl.enter_command("ls -l f1.txt", shell_basic)

    assert_success(result)
    assert listing.status == 0
    assert listing.stderr == []
    assert "alice staff" in listing.stdout[0]


def test_new_files_inherit_effective_owner_and_parent_group(cl, shell_basic):
    shell_basic.identity = EffectiveIdentity("alice", "staff", frozenset({"staff"}))

    result = cl.enter_command("touch created.txt", shell_basic)

    assert_success(result)
    node = shell_basic.fs.filehead.access("created.txt")
    assert node.inode.owner == "alice"
    assert node.inode.group == shell_basic.fs.filehead.inode.group


def test_recursive_chown_skips_symbolic_links(cl, shell_basic):
    assert_success(cl.enter_command("ln -s f1.txt d1/link", shell_basic))
    link = shell_basic.fs.filehead.access("d1").access("link")
    target = shell_basic.fs.filehead.access("f1.txt")
    shell_basic.identity = EffectiveIdentity("root", "root", frozenset({"root"}), True)

    result = cl.enter_command("chown -R alice:staff d1", shell_basic)

    assert_success(result)
    assert link.inode.owner == "user"
    assert target.inode.owner == "user"
    assert shell_basic.fs.filehead.access("d1").inode.owner == "alice"
    assert shell_basic.fs.filehead.access("d1").access("f3.txt").inode.owner == "alice"


def test_effective_identity_is_isolated_between_shell_sessions(cl):
    first = ShellState()
    first.cwd = "/"
    first.fs = FileSystem()
    first.identity = EffectiveIdentity("alice", "staff", frozenset({"staff"}))
    first.fs.add_file("private.txt")
    private = first.fs.filehead.access("private.txt")
    private.inode.owner = "alice"
    private.inode.permissions["user"] = {"r": True, "w": True, "x": False}
    private.inode.permissions["group"] = {"r": False, "w": False, "x": False}
    private.inode.permissions["public"] = {"r": False, "w": False, "x": False}
    private.inode.set_data(["secret"])

    second = ShellState()
    second.cwd = "/"
    second.fs = FileSystem()
    second.identity = EffectiveIdentity("bob", "visitors", frozenset({"visitors"}))
    second.fs.add_file("private.txt")
    second.fs.filehead.access("private.txt").inode.owner = "alice"
    second.fs.filehead.access("private.txt").inode.permissions = {
        key: value.copy() for key, value in private.inode.permissions.items()
    }
    second.fs.filehead.access("private.txt").inode.set_data(["secret"])

    first_result = cl.enter_command("cat private.txt", first)
    second_result = cl.enter_command("cat private.txt", second)

    assert first_result.stdout == ["secret"]
    assert first_result.status == 0
    assert_failure(second_result)
    assert second_result.stderr == [
        "cat: private.txt: Permission denied: read 'private.txt'"
    ]
    assert first.fs.identity.username == "alice"
    assert second.fs.identity.username == "bob"
