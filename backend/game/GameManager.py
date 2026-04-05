
class GameManager:
    def __init__(self):
        self.init_config = {}

    def set_config(self, config: dict) -> None:
        self.init_config = config
        self.generate_config()

    def generate_config(self) -> None:
        self.gen_config = {}

    def get_shell(self) -> dict:
        return {
            "environment": [],
            "cmds": [],
            "fs": {"lcs": 0, "nodes": []},
            "vars": [],
        }