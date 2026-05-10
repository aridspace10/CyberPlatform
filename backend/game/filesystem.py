from game.filenode import FileNode
from typing import Literal, Tuple
from game.inode import Inode, NodeType

class FileSystem:
    def __init__(self):
        inode = Inode(NodeType.DIRECTORY)
        self.filehead = FileNode(None, "root", inode)
        self.current: FileNode = self.filehead
        self.lcs = 0
        self.cwd = ""
    
    def to_dict(self) -> dict:
        return {
            "lcs": self.lcs,
            "nodes": self.filehead.to_dict()
        }

    def from_dict(self, fs: dict) -> None:
        # Clear fs
        self.__init__()
        # restore fs
        try:
            self.lcs = fs["lcs"]
            self.filehead.from_dict(fs["nodes"], 0, None)
        except:
            raise Exception("Syncronization failure")

    def get_file(self, path: str) -> FileNode | str | None:
        saved_current = self.current
        lst = path.split("/")
        if (error := self.search("/".join(lst[0:-1]))) != "":
            self.current = saved_current
            return error
        tmp = self.current
        self.current = saved_current
        return tmp.access(lst[-1])
    
    def list_files(self, path: str, deep: int = 0, detail: int = 0, extras: dict[str, bool | str] = {}) -> list[list[str]] | str:
        if (path != ""):
            if (error := self.search(path)) != "":
                return error
        return self.current.list_content("", deep, detail, extras)

    def search(self, path: str, creating: bool = False) -> str:
        if (path == "/"):
            return ""
        lst = path.split("/")
        while len(lst) > 0 and lst != ['']:
            cur = lst.pop(0)
            # if we are staying still
            if cur == '' or cur == ".":
                continue
            # if we going back
            if cur == "..":
                if (self.current.parent is not None):
                    self.current = self.current.parent
                    continue

            if self.current.get_type() == NodeType.FILE:
                return f"{self.current.name} is not a directory"
            
            if self.current.access(cur) is None and creating:
                inode = Inode(NodeType.DIRECTORY)
                self.current.add_child(cur, inode)
            node = self.current.access(cur)
            if node is None:
                return f"No directory named {cur}"
            if node.inode.type == NodeType.SYMLINK:
                target = node.inode.data
                # Resolve target relative to symlink's parent
                saved = self.current
                err = self.search(target)
                if err != "":
                    return err
                node = self.current
                self.current = saved
            self.current = node
        return ""
    
    def search_withaccess(self, path: str, creating: bool = False) -> NodeType | None: 
        lst = path.split("/")
        self.search("/".join(lst[0:-1]))
        for item in self.current.items:
            if item.name == lst[-1]:
                self.current = item
                return item.get_type()
        return None
    
    def add(self, path: str) -> str:
        if "." in path:
            return self.add_file(path)
        else:
            return self.add_directory(path)

    def add_directory(self, path: str, creating: bool = False, permissions: dict = {}) -> str:
        error = ""
        saved_current = self.current
        lst = path.split("/")
        if (error := self.search("/".join(lst[0:-1]), creating)) != "":
            self.current = saved_current
            return error
        inode = Inode(NodeType.DIRECTORY)
        inode.permissions = permissions
        error = self.current.add_child(lst[-1], inode)
        self.current = saved_current
        return error

    def add_file(self, path: str, fn: FileNode | None = None):
        saved_current = self.current
        lst = path.split("/")
        if (error := self.search("/".join(lst[0:-1]))) != "":
            self.current = saved_current
            return error
        if fn is None:
            inode = Inode(NodeType.FILE)
            self.current.add_child(lst[-1], inode)
        else:
            self.current.add_child(fn.name, fn.inode)
        self.current = saved_current
        return ""

"""
f = FileSystem()
f.setup_system("filesystems/example.txt")
print (f.list_files("", 1))
content = f.tree()
for p in content:
    print ("".join(p))
"""