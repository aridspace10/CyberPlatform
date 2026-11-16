"""Start the backend locally with the jack/1234 development login enabled."""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent / "backend"
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))

    import uvicorn
    from main import app

    app.state.local_dev_login = True
    print("Local development login: jack / 1234")
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
