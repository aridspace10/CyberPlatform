"""MiniGames command packs and selectable modes."""

from .cat import CatPack
from .grep import GrepPack
from .ls import LsPack
from .rm import RmPack
from .sed import SedPack
from .wc import WcPack

PACK_TYPES = {
    "ls": LsPack,
    "cat": CatPack,
    "wc": WcPack,
    "grep": GrepPack,
    "sed": SedPack,
    "rm": RmPack,
}

QUESTION_MODES = {command: pack_type.modes for command, pack_type in PACK_TYPES.items()}
