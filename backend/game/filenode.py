from __future__ import annotations
from typing import Literal, Tuple
import datetime
from inode import Inode, NodeType

class FileNode:
    def __init__(self, parent: FileNode | None, name: str, inode: Inode):
        self.name = name
        self.parent: FileNode | None = parent
        self.depth = 0
        self.items: list[FileNode] = []
        self.inode: Inode = inode
    
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
        self.permissions = updated

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
    
    def preorder_traversal(self, content: list[Tuple[int, str]], move: int) -> list[Tuple[int, str]]:
        if (self.items):
            mid = len(self.items) // 2
            for idx, item in enumerate(self.items):
                if (idx == mid):
                    content.append((move, self.name + "-|"))
                content = (item.preorder_traversal(content, move + 1))
        else:
            content.append((move, "--"))
            move += 1
            content.append((move, self.name))
        return content

    def add_child(self, name: str, inode: Inode) -> FileNode:
        file = FileNode(self, name, inode)
        if (not len(self.items)):
            self.depth = 1
            if (self.parent is not None):
                self.parent.accumualate_depth()
        self.items.append(file)
        return file
    
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

    def delete_child(self, name: str) -> FileNode | None:
        for idx, item in enumerate(self.items):
            if (item.name == name):
                return self.items.pop(idx)
        return None
                
    def len(self) -> int:
        return len(self.items)

    def list_content(self, prev: str, deep: int = 0, detail: int = 0, extras: dict[str, bool | str] = {}) -> list:
        content: list[list] = []
        for item in self.items:
            itemname = prev + "/" + item.name if prev else item.name
            tmp = []

            if "inode" in extras:
                tmp.append(str(self.inode.id))

            if (not detail):
                tmp.append(itemname)
            else:
                tmp.extend([self.get_permission_str(item), str(1), "user", "user", str(item.get_size()), str(self.inode.mtime.strftime("%b")), str(self.inode.mtime.day), str(self.inode.mtime.year), itemname])

            content.append(tmp)

            if item.get_type() == NodeType.DIRECTORY and deep:
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

                content = sorted(content, key=size_sort, reverse=rev)
            else:
                def time_sort(val):
                    itemname = val[-1]
                    item = self.access(itemname)
                    if item == None:
                        return ""
                    if method == "mod":
                        return item.inode.mtime
                    elif method == "atime":
                        return item.inode.atime
                    elif method == "ctime":
                        return item.inode.ctime
                    return ""

                content = sorted(content, key=time_sort, reverse=rev)
        else:
            if ("reverse" in extras):
                content = content[::-1]
        return content