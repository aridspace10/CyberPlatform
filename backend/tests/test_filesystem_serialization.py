import json
from copy import deepcopy

import pytest

from game.filesystem import FileSystem
from game.inode import Inode, NodeType
from tests.filesystem_helpers import restored_filesystem


def test_restored_tree_has_unique_siblings_and_correct_parents():
    fs = FileSystem()
    fs.add_directory("d")
    fs.add_file("d/inside.txt")
    restored = restored_filesystem(fs)

    directory = restored.filehead.access("d")
    child = directory.access("inside.txt")
    assert restored.filehead.parent is None
    assert directory.parent is restored.filehead
    assert child.parent is directory
    assert len(restored.filehead.items) == 1
    assert len(directory.items) == 1

    restored.from_dict(json.loads(json.dumps(fs.to_dict())))
    assert len(restored.filehead.items) == 1


def test_legacy_save_restores_shared_links_with_documented_newline_default():
    fs = FileSystem()
    fs.add_file("a.txt")
    source = fs.filehead.access("a.txt")
    source.set_data(["first", "second"])
    fs.filehead.add_child("h.txt", source.inode)

    legacy = json.loads(json.dumps(fs.to_dict()))
    for child in legacy["nodes"]["items"]:
        child["inode"].pop("has_trailing_newline")
        child["inode"].pop("link_count")

    restored = FileSystem()
    restored.from_dict(legacy)
    a = restored.filehead.access("a.txt")
    h = restored.filehead.access("h.txt")
    assert a.inode is h.inode
    assert a.inode.link_count == 2
    assert a.inode.has_trailing_newline is False


def test_restored_inode_ids_and_metadata_survive_new_process_allocator():
    fs = FileSystem()
    fs.add_file("a.txt")
    source = fs.filehead.access("a.txt")
    source.set_data(["data"])
    saved = json.loads(json.dumps(fs.to_dict()))
    saved["nodes"]["inode"]["id"] = 1
    saved["nodes"]["items"][0]["inode"]["id"] = 100
    time_keys = ("btimes", "ctimes", "atimes", "mtimes")
    expected_times = tuple(
        saved["nodes"]["items"][0]["inode"][key] for key in time_keys
    )

    previous_next_id = Inode._next_id
    try:
        Inode._next_id = 1
        restored = FileSystem()
        restored.from_dict(saved)
        inode = restored.filehead.access("a.txt").inode
        assert inode.id == 100
        assert inode.type is NodeType.FILE
        assert inode.has_trailing_newline is True
        assert tuple(inode.to_dict()[key] for key in time_keys) == expected_times
        assert Inode(NodeType.FILE).id > 100
    finally:
        Inode._next_id = max(previous_next_id, Inode._next_id)


def test_duplicate_sibling_in_saved_tree_is_rejected_without_changing_fs():
    fs = FileSystem()
    fs.add_file("a.txt")
    original_root = fs.filehead
    saved = deepcopy(fs.to_dict())
    saved["nodes"]["items"].append(deepcopy(saved["nodes"]["items"][0]))

    with pytest.raises(Exception, match="Syncronization failure"):
        fs.from_dict(saved)
    assert fs.filehead is original_root
