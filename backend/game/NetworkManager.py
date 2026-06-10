
class Network:
    def __init__(self, ip: str, online: bool = True):
        self.ip = ip
        self.online = online

class NetworkManager():
    def __init__(self):
        self.networks: dict[str, Network] = {}