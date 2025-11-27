from filenode import FileNode


class FileSystem:
    def __init__(self):
        self.filehead = FileNode(None, "..")
        self.current: FileNode = self.filehead

    def setup_system(self, textfile):
        temp = self.current
        self.current = self.filehead
        with open(textfile) as f:
            for line in f:
                if (self.add_directory(line)):
                    raise Exception("Adminstator Error, Code AAA123")
        self.current = temp

    def list_files(self, path):
        if (path != ""):
            if (error := self.search(path)) != "":
                return error
        return self.current.list_content()

    def search(self, path: str) -> str:
        while (len(lst := path.split("/")) > 1):
            if (lst[0] == "."):
                continue
            if (lst[0] == ".."):
                self.current = self.filehead
                continue

            if (self.current.search(lst[0])) in [None, "file"]:
                return f"No directory named {lst[0]} in \"${self.current}\""
            node = self.current.access(lst[0])
            if node is None:
                return f"No directory named {lst[0]} in \"${self.current}\""
            self.current = node
            path = path[1]
        return ""

    def add_directory(self, path: str) -> str:
        if (error := self.search(path)) != "":
            return error
        self.current = self.current.add_child(path, 'directory')
        return ""

    def add_file(self, path):
        pass
