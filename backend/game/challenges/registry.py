"""MiniGames command packs and selectable modes."""

from .cat import CatPack
from .grep import GrepPack
from .ls import LsPack
from .sed import SedPack
from .tail import TailPack
from .wc import WcPack

PACK_TYPES = {
    "ls": LsPack,
    "cat": CatPack,
    "wc": WcPack,
    "grep": GrepPack,
    "sed": SedPack,
    "tail": TailPack,
}

QUESTION_MODES = {command: pack_type.modes for command, pack_type in PACK_TYPES.items()}
