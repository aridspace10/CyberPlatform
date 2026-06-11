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
            "fs": {
                "lcs": 0,
                "nodes": {
                    "name": "root",
                    "inode": {
                        "id": 2,
                        "type": "directory",
                        "data": "",
                        "permissions": {
                            "user": {"r": True, "w": True, "x": True},
                            "group": {"r": True, "w": True, "x": True},
                            "public": {"r": True, "w": True, "x": True},
                        },
                        "btimes": "2026-04-05T21:29:22.356312",
                        "ctimes": "2026-04-05T21:29:22.356312",
                        "atimes": "2026-04-05T21:29:22.356312",
                        "mtimes": "2026-04-05T21:29:22.356312",
                    },
                    "items": [],
                },
            },
            "vars": [],
        }
