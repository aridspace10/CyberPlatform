import random
from .ShellState import ShellState
from .helpers import biased_random, biased_randint
from .filenode import FileNode, NodeType
from .inode import Inode

QUESTION_TYPES = ["SINGLE", "PIPE_SINGLE"]
QUESTION_TYPES_PROBS = [0.8, 0.2]

class MiniGame:
    def __init__(self):
        self.player_attempts: dict[str, int] = {}

    def setup(self, shell: ShellState) -> None:
        raise NotImplementedError
    
    def check_answer(self, answer: str) -> bool:
        raise NotImplementedError


class GrepFindFiles(MiniGame):
    def __init__(self):
        super().__init__()
         

GREP_GAMES: list[type] = [GrepFindFiles]
SINGLECMD_GAMES: dict[str, list[type]] = {
    "grep": GREP_GAMES
}

class GameManager:
    def __init__(self):
        self.init_config = {}

    def set_config(self, config: dict) -> None:
        self.init_config = config
        self.generate_config()

    def auto_generate_fs(self, files: int, dirs: int):
        # Base Case
        if files == 0 and dirs == 0:
            return
        
        # Deciding what we doing this time
        choice = random.choices(
            ["file", "dir"],
            weights=[files, dirs]
        )[0]

        if choice == "dir" and dirs > 0:
            name = "THE NAME HERE WHEN DECIDE HOW DO THAT"
            self.shell.fs.add_directory(name)
            self.shell.fs.search(name)

            # Take some files for nested stuff (will rework more solid logic later)
            ftaken = biased_randint(0, files, std_factor=3)
            dtaken = biased_randint(0, dirs - 1, std_factor=3)
            
            # Recurse into new dir with its slice of the budget
            self.auto_generate_fs(ftaken, dtaken)
            # Else case is not possible however type checking
            self.shell.fs.current = self.shell.fs.current.parent if self.shell.fs.current.parent != None else self.shell.fs.current
            
            # Continue at current level with the remainder
            self.auto_generate_fs(files - ftaken, dirs - 1 - dtaken)

        elif choice == "file" and files > 0:
            # Generate file and put in current directory
            file_name = "THE NAME HERE WHEN DECIDE HOW DO THAT"
            inode = Inode(NodeType.FILE)
            fn = FileNode(self.shell.fs.current, file_name, inode)
            self.shell.fs.add_file(file_name)
            
            self.auto_generate_fs(files - 1, dirs)
 
    def generate_config(self) -> None:
        # Get some constants
        self.type: str = self.init_config["type"]
        self.num_rounds: int = self.init_config["rounds"]
        self.commands: list[str] = self.init_config["allowed_commands"]
        max_files: int = self.init_config["fs"]["files"]
        max_dir: int = self.init_config["fs"]["dirs"]
        self.shell = ShellState()
        self.minigames = []
        #Generate FS
        num_files = biased_randint(1, max_files)
        num_dirs = biased_randint(1, max_dir)
        self.auto_generate_fs(num_files, num_dirs)

        #Generate rounds
        for i in range(self.num_rounds):
            ty = random.choices(QUESTION_TYPES, QUESTION_TYPES_PROBS, k=1)[0]
            match (ty):
                case "SINGLE":
                    # Basic one command
                    game = random.choice(SINGLECMD_GAMES[random.choice(self.commands)])()
                case "PIPE_SINGLE":
                    # pipe (singular)
                    pos = [(a, b) for a in self.commands for b in self.commands]
                    match (pos):
                        case (("ls", "grep")):
                            pass

    def get_shell(self) -> dict:
        return self.shell.