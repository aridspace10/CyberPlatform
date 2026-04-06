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

    def setup_system(self, textfile):
        with open(textfile) as f:
            for line in f:
                self.current = self.filehead
                if ("*" in line):
                    line = line[0:line.index("*")]
                    with open(f"filesystems/{line}") as f:
                        data = f.read()
                else:
                    data = ""
                if (err := self.add(line.strip())):
                    print(err)
                    raise Exception("Administrator Error, Code AAA123")
                if (data):
                    self.current.set_data(data)
        self.current = self.filehead

    def get_file(self, path: str) -> FileNode | str | None:
        saved_current = self.current
        lst = path.split("/")
        if (error := self.search("/".join(lst[0:-1]))) != "":
            self.current = saved_current
            return error
        tmp = self.current
        self.current = saved_current
        return tmp.access(lst[-1])

    def tree(self, path: str = "."):
        if (error := self.search(path)) != "":
            return error
        lx = self.current.depth * 4
        nodes = self.current.preorder_traversal([], 0)
        print (nodes)
        output = [[' ' for _ in range(lx)] for _ in range(len(nodes))]
        idx = 0
        for node in nodes:
            output[idx][node[0]] = node[1]
            if (len(node[1]) > 2):
                idx += 1
        print (output)
        for col in range(0, lx):
            biggest = 0
            for row in range(len(nodes)):
                if (new := len(output[row][col])) > biggest:
                    biggest = new
            print (biggest)
            for row in range(len(nodes)):
                output[row][col] = output[row][col] + " " * (biggest - len(output[row][col]))
        return output

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
            self.current = self.current.add_child(lst[-1], inode)
        else:
            self.current = self.current.add_child(fn.name, fn.inode)
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