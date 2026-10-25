class Network:
    def __init__(self, ip: str, online: bool = True):
        self.ip = ip
        self.online = online


class NetworkManager:
    def __init__(self):
        """Own the deterministic, in-game network table used by ping."""
        self.networks: dict[str, Network] = {}
        self.add_network("gateway", "192.0.2.1", online=True)
        self.add_network("offline-host", "192.0.2.2", online=False)

    def add_network(self, name: str, ip: str, online: bool = True) -> Network:
        """Add or replace a simulated destination; no host networking is used."""
        network = Network(ip, online)
        self.networks[name] = network
        return network

    def get_network(self, destination: str) -> Network | None:
        """Resolve an in-game destination by name or configured IP address."""
        network = self.networks.get(destination)
        if network is not None:
            return network
        return next(
            (item for item in self.networks.values() if item.ip == destination), None
        )
