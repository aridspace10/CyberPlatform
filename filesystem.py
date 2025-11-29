from filenode import FileNode

class FileSystem:
    def __init__(self):
        self.filehead = FileNode(None, "..")
        self.current: FileNode = self.filehead

    def setup_system(self, textfile):
        with open(textfile) as f:
            for line in f:
                self.current = self.filehead
                if (err := self.add(line.strip())):
                    print(err)
                    raise Exception("Administrator Error, Code AAA123")
        self.current = self.filehead

    def tree(self, path: str = "."):
        if (error := self.search(path)) != "":
            return error

    def list_files(self, path):
        if (path != ""):
            if (error := self.search(path)) != "":
                return error
        return self.current.list_content()

    def search(self, path: str) -> str:
        lst = path.split("/")
        while len(lst) > 1:
            if lst[0] == ".":
                lst.pop(0)
                continue
            if lst[0] == "..":
                self.current = self.filehead
                lst.pop(0)
                continue

            if self.current.search(lst[0]) in [None, "file"]:
                return f"No directory named {lst[0]}"
            node = self.current.access(lst[0])
            if node is None:
                return f"No directory named {lst[0]}"
            self.current = node
            lst.pop(0)
        return ""
    
    def add(self, path: str) -> str:
        if "." in path:
            return self.add_file(path)
        else:
            return self.add_directory(path)

    def add_directory(self, path: str) -> str:
        saved_current = self.current
        if (error := self.search(path)) != "":
            self.current = saved_current
            return error
        self.current = self.current.add_child(path, 'directory')
        return ""

    def add_file(self, path):
        saved_current = self.current
        if (error := self.search(path)) != "":
            self.current = saved_current
            return error
        self.current = self.current.add_child(path, 'file')
        return ""

f = FileSystem()
f.setup_system("filesystems/example.txt")
print (f.list_files(""))