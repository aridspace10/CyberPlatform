"""echo MiniGames scenarios."""

from .core import Challenge, OutputPack


class EchoPack(OutputPack):
    command = "echo"
    root = "messages"
    variants = ("incident", "release", "handoff")
    modes = {"Phrase": "phrase"}

    def build(self, index: int, mode: str, variant: str) -> Challenge:
        marker = self.token_hex(3)
        text = (
            f"{variant} {marker} ready"
            if mode == "phrase"
            else f"ACK-{marker}"
        )
        context = {
            "incident": "Acknowledge an incident update.",
            "release": "Confirm a release step.",
            "handoff": "Send a handoff acknowledgment.",
        }[variant]
        prompt = f"{context} Use echo to print exactly: {text}"
        example = (
            'echo "sample message ready"'
            if mode == "phrase"
            else "echo ACK-sample"
        )
        return self._output_challenge(
            index,
            mode,
            variant,
            prompt,
            example,
            f"echo {text}",
            (),
            [text],
        )
