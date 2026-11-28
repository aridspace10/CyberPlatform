"""MiniGames command packs and selectable modes."""

from .cat import CatPack
from .echo import EchoPack
from .grep import GrepPack
from .ls import LsPack
from .sed import SedPack
from .wc import WcPack

PACK_TYPES = {
    "ls": LsPack,
    "cat": CatPack,
    "echo": EchoPack,
    "wc": WcPack,
    "grep": GrepPack,
    "sed": SedPack,
}

QUESTION_MODES = {command: pack_type.modes for command, pack_type in PACK_TYPES.items()}
