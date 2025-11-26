from filenode import FileNode


class FileSystem:
    def __init__(self):
        self.filehead = FileNode(None, "..")
        self.current: FileNode = self.filehead

    def setup_system(self, textfile):
        pass

    def add_directory(self, path: str) -> str:
        self.inital = self.current
        while (lst := path.split("/")):
            if (self.current.search(lst[0])) in [None, "file"]:
                temp = self.current
                self.current = self.inital
                return f"No directory named {lst[0]} in \"${temp}\""
            node = self.current.access(lst[0])
            if node is None:
                temp = self.current
                self.current = self.inital
                return f"No directory named {lst[0]} in \"${temp}\""
            self.current = node
        self.current = self.current.add_child(path, 'directory')
        return ""

    def add_file(self, path):
        pass
