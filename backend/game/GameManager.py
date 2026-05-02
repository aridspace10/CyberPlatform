import random
from .ShellState import ShellState

class MiniGame:
    def __init__(self):
        self.player_attempts: dict[str, int] = {}

class GameManager:
    def __init__(self):
        self.init_config = {}

    def set_config(self, config: dict) -> None:
        self.init_config = config
        self.generate_config()

    def generate_config(self) -> None:
        # Get some constants
        self.type: str = self.init_config["type"]
        self.num_rounds: int = self.init_config["rounds"]
        self.commands: list[str] = self.init_config["allowed_commands"]
        max_files: int = self.init_config["fs"]["files"]
        max_dir: int = self.init_config["fs"]["dirs"]
        self.shell = ShellState()
        self.minigames = []
        #Generate rounds
        for i in range(self.num_rounds):
            ty = random.randint(1, 2)
            match (ty):
                case 1:
                    # Basic one command
                    cmd = random.choice(self.commands)
                    match (cmd):
                        case "ls":
                            pass
                case 2:
                    # pipe (singular)
                    pos = [(a, b) for a in self.commands for b in self.commands]
                    match (pos):
                        case (("ls", "grep")):
                            pass

        #Generate 

    def get_shell(self) -> dict:
        return self.shell.