from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the personal_lab service.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Bind port. Default: 8000")
    parser.add_argument(
        "--home",
        default="",
        help="Runtime home for data/logs/uploads. Default: source root in dev, otherwise ./.personal_lab",
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload mode.")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.home:
        runtime_home = Path(args.home)
        if not runtime_home.is_absolute():
            runtime_home = Path.cwd() / runtime_home
        os.environ["PERSONAL_LAB_HOME"] = str(runtime_home.resolve())

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
