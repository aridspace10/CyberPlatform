
class GameManager:
    def __init__(self):
        self.init_config = {}

    def set_config(self, config: dict) -> None:
        self.init_config = config

    def generate_config(self) -> None:
        self.gen_config = {}