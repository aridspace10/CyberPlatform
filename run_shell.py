"""Run the CyberPlatform development shell from any working directory."""

import os
import sys
from pathlib import Path


def main() -> int:
    backend = Path(__file__).resolve().parent / "backend"
    sys.path.insert(0, str(backend))
    # The command engine loads its help files relative to backend/.
    os.chdir(backend)
    from game.dev_shell import main as shell_main

    return shell_main()


if __name__ == "__main__":
    raise SystemExit(main())
