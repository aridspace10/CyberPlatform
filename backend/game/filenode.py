from __future__ import annotations
from typing import Literal, Tuple, List
import datetime
from game.inode import Inode, NodeType
from game.Parser import Node, NotNode, OrNode, AndNode, FilterNode
import fnmatch

class FileNode:
    def __init__(self, parent: FileNode | None, name: str, inode: Inode):
        self.name = name
        self.parent: FileNode | None = parent
        self.depth = 0
        self.items: list[FileNode] = []
        self.inode: Inode = inode

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "inode": self.inode.to_dict(),
            "items": [item.to_dict() for item in self.items]
        }
    
    def __eq__(self, other):
        if not isinstance(other, FileNode):
            return False
        return self.name == other.name and self.items == other.items and self.get_size() == other.get_size()

    def from_dict(self, fn: dict, depth: int, parent: FileNode | None) -> None:
        try:
            self.name = fn["name"]
            self.depth = depth
            self.inode.from_dict(fn["inode"])
            for item in fn["items"]:
                inode = Inode(item["inode"]["type"])
                f = FileNode(parent, item["name"], inode)
                f.from_dict(item, depth + 1, self)
                self.items.append(f)
        except:
            raise Exception("Syncronization Error")
    
    def __str__(self):
        return f"name: {self.name}, items: {self.items}, size: {self.inode.size}"
    
    def __repr__(self):
        return self.__str__()
    
    def get_type(self) -> NodeType:
        return self.inode.type

    def get_size(self) -> int:
        return self.inode.size
    
    def get_permission_str(self, item: FileNode):
        permission = "d" if item.get_type() == NodeType.DIRECTORY else "-"
        for i in item.inode.permissions.values():
            for key, value in i.items():
                permission += key if value else "-"
        return permission
    
    def update_permissions(self, updated: dict, recurse: bool, verbose: list[str]) -> list[str]:
        self.ctime = datetime.datetime.now()
        self.inode.permissions = updated

        verbose.append(f"Updated permissions of ${self.name} with ${self.get_permission_str(self)}")
        if (recurse):
            for item in self.items:
                verbose.extend(item.update_permissions(updated, recurse, verbose))
        return verbose

    def get_data(self) -> str:
        return self.inode.get_data()
    
    def set_data(self, data: str) -> None:
        self.inode.set_data(data)
    
    def append_data(self, data: str) -> None:
        self.inode.append_data(data)

    def accumualate_depth(self) -> None:
        self.depth += 1
        if (self.parent != None):
            self.parent.accumualate_depth()
    
    def add_child(self, name: str, inode: Inode) -> str:
        """ Adds a child to the filenode """
        for file in self.items:
            if file.name == name:
                return f"Filename '{name}' already exists"
        file = FileNode(self, name, inode)
        if (not len(self.items)):
            self.depth = 1
            if (self.parent is not None):
                self.parent.accumualate_depth()
        self.items.append(file)
        return ""
    
    def search(self, name: str) -> NodeType | None:
        for item in self.items:
            if (item.name == name):
                return item.get_type()
        return None
    
    def access(self, name: str) -> FileNode | None:
        for item in self.items:
            if (item.name == name):
                return item
        return None

    def delete_child(self, name: str, recurse: bool = False) -> FileNode | str:
        for idx, item in enumerate(self.items):
            if (item.name == name):
                if (item.get_type() == NodeType.DIRECTORY and recurse == False):
                    return "dir"
                return self.items.pop(idx)
        return ""
    
    def _evalNode(self, node: Node) -> bool:
        if (isinstance(node, OrNode)):
            return self._evalOrFindNode(node)
        elif (isinstance(node, AndNode)):
            return self._evalAndNode(node)
        elif (isinstance(node, NotNode)):
            return not self._evalNode(node.node)
        elif (isinstance(node, FilterNode)):
            return self._evalFilterNode(node)
        return False
    
    def _evalOrFindNode(self, node: OrNode) -> bool:
        val = self._evalNode(node.left)
        if (not val):
            return self._evalNode(node.right)
        return True

    def _evalAndNode(self, node: AndNode) -> bool:
        val = self._evalNode(node.left)
        if (val):
            return self._evalNode(node.right)
        return False
    
    def _evalFindType(self, val: str):
        match (val):
            case ("f"):
                return self.get_type() == NodeType.FILE
            case ("d"):
                return self.get_type() == NodeType.DIRECTORY
            case ("s"):
                return self.get_type() == NodeType.SYMLINK
            case _:
                raise SyntaxError(f"Value for -type not allowed: ${val}") 

    def _evalFilterNode(self, node: FilterNode) -> bool:
        match (node.type):
            case ("-type"):
                return self._evalFindType(node.value)
            case ("-name"):
                return fnmatch.fnmatch(self.name, node.value)
        return True
    
    def _join(self, past: str) -> str:
        if (self.parent == None):
            return "."
        if past == ".":
            return f"./{self.name}"
        return f"{past}/{self.name}"
    
    def find(self, filter: Node, past: str) -> List[str]:
        output = []
        current_path = "." if past == "." and self.name == "" else self._join(past)
        if self._evalNode(filter):
            output.append(current_path)

        for item in self.items:
            output.extend(item.find(filter, current_path))
        return output
                
    def len(self) -> int:
        return len(self.items)

    def list_content(self, prev: str, deep: int = 0, detail: int = 0, extras: dict[str, bool | str] = {}) -> list:
        content: list[list] = []
        items = self.items
        if "showhiddenall" in extras:
            items.append(self) 
            if self.parent is not None:
                items.append(self.parent)

        for item in items:
            if ((item.name[0] == ".") and ("showhiddenall" not in extras or "showhidden" not in extras)):
                continue
            if (item == self):
                itemname = "."
            elif (item == self.parent):
                itemname = ".."
            else:
                itemname = prev + "/" + item.name if prev else item.name
            tmp = []

            if "inode" in extras:
                tmp.append(str(self.inode.id))

            if (not detail):
                tmp.append(itemname)
            else:
                tmp.extend([self.get_permission_str(item), str(1), "user", "user", str(item.get_size()), str(self.inode.mtime.strftime("%b")), str(self.inode.mtime.day), str(self.inode.mtime.year), itemname])

            content.append(tmp)

            if item.get_type() == NodeType.DIRECTORY and deep and itemname not in [".", ".."]:
                deep -= 1
                content.extend(item.list_content(prev + "/" + item.name, deep))
        
        if "sortby" in extras:
            method = extras["sortby"]
            if ("reverse" in extras):
                rev = bool(extras["reverse"])
            else:
                rev = False
            if (method == "ext"):
                def ext_sort(val):
                    lst = val[-1].split(".")
                    if (len(lst) == 1):
                        return ""
                    return lst[1]
                content = sorted(content, key=ext_sort, reverse=rev)
            elif method == "size":
                def size_sort(val):
                    itemname = val[-1]
                    item = self.access(itemname)
                    if item == None:
                        return ""
                    return item.inode.size

                content = sorted(content, key=size_sort, reverse=not rev)
            else:
                def time_sort(val):
                    itemname = val[-1].split("/")[-1]
                    item = self.access(itemname)
                    print (item)
                    print (item.inode.ctime)
                    if item == None:
                        return 0
                    if method == "mod":
                        return item.inode.mtime
                    elif method == "atime":
                        return item.inode.atime
                    elif method == "ctime":
                        return item.inode.ctime
                    return 0

                content = sorted(content, key=time_sort, reverse=not rev)
        else:
            if ("reverse" in extras):
                content = content[::-1]
        return content