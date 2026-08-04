import copy
import random
from .ShellState import ShellState
from .helpers import biased_random, biased_randint, get_all_files, weighted_sample
from .filenode import FileNode, NodeType
from .inode import Inode

QUESTION_TYPES = ["SINGLE", "PIPE_SINGLE"]
QUESTION_TYPES_PROBS = [1, 0]

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
        self.expected_files = []

    def setup(self, shell: ShellState) -> None:
        self.options = []
        self.target_pattern = random.choice(["error", "secret", "TODO", "admin"])
        self.starting_dir = "."

        # Get all files (not dirs) from the FS and Get weights using inverse bias
        all_files = get_all_files(shell.fs.filehead)
        weights = [1 / (f.depth + 1) for f in all_files]
        
        # Get the number of matches we doing for this game and the files we inserting into
        num_matches = biased_randint(1, max(1, len(all_files) // 3))
        match_files = weighted_sample(all_files, weights, k=num_matches)
        
        # Insert all the expected output files
        for f in match_files:
            f.random_insert(self.target_pattern)
            f.needed = True
            self.expected_files.append(f.name)
            
        self.expected_command = f"grep -{"".join(sorted(self.options))} {self.target_pattern} {self.starting_dir}"
    
    def check_answer(self, answer: str) -> bool:
        answered = set(answer.split("\n"))
        expected = set(self.expected_files)
        return True

GREP_GAMES: list[type] = [GrepFindFiles]
SINGLECMD_GAMES: dict[str, list[type]] = {
    "grep": GREP_GAMES
}

class GameManager:
    def __init__(self):
        self.init_config: dict = {}
        self.gen_config: dict = {}
        self.session_name = ""
        self.play_type = "SinglePlayer"
        self.game_type = ""
        self.creator_id: int | None = None
        self.command_config: dict[str, dict] = {}
        self.commands: list[str] = []
        self.options: dict = {}
        self.allow_pipes = False
        self.num_rounds = 0
        self.shell = ShellState()
        self.minigames = []

    def set_config(self, config: dict) -> None:
        """Store the complete session-creation contract for game setup.

        Actual round generation is intentionally a separate step.  Creating a
        session should not start consuming the configuration before players
        have reached the appropriate game screen.
        """
        self.init_config = copy.deepcopy(config)
        self.gen_config = copy.deepcopy(config)

        self.session_name = config.get("name", "")
        self.play_type = config.get("playType", "SinglePlayer")
        self.game_type = config.get("gameType", config.get("name", ""))
        self.creator_id = config.get("creatorID")
        self.command_config = copy.deepcopy(config.get("commands", {}))
        self.commands = [
            command
            for command, state in self.command_config.items()
            if state.get("selected", False)
        ]
        self.options = copy.deepcopy(config.get("options", {}))
        self.allow_pipes = bool(self.options.get("allowPipes", False))
        self.num_rounds = int(self.options.get("rounds", 0))

        self.shell = ShellState()
        self.shell.commands = list(self.commands)
        self.minigames = []

    def get_shell(self) -> dict:
        """Return a serializable copy of the configured starting shell."""
        return {
            "vars": copy.deepcopy(self.shell.vars),
            "cmds": list(self.shell.commands),
            "fs": self.shell.fs.to_dict(),
        }

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
