import json

from game.filesystem import FileSystem


def restored_filesystem(fs: FileSystem) -> FileSystem:
    saved = json.loads(json.dumps(fs.to_dict()))
    restored = FileSystem()
    restored.from_dict(saved)
    return restored
