from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DUMP_DIR = PROJECT_ROOT / "dumps"
DUMP_FILE = DUMP_DIR / "sync.dump"

WIN_PG_BIN_GUESSES = [
    Path(r"C:\Program Files\PostgreSQL\17\bin"),    
    Path(r"C:\Program Files\PostgreSQL\16\bin"),
    Path(r"C:\Program Files\PostgreSQL\15\bin"),
]


def load_urls() -> tuple[str, str]:
    load_dotenv(PROJECT_ROOT / ".env")
    neon = os.getenv("NEON_DATABASE_URL")
    local = os.getenv("LOCAL_DATABASE_URL")
    if not neon:
        sys.exit("Set NEON_DATABASE_URL in .env")
    if not local:
        sys.exit("Set LOCAL_DATABASE_URL (or DATABASE_URL) in .env")
    return neon, local


def _pg_bin(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for folder in WIN_PG_BIN_GUESSES:
        candidate = folder / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    sys.exit(
        f"Could not find {name}. Install PostgreSQL client tools and add them to PATH."
    )


def _run(cmd: list[str]) -> None:
    print(" ".join(cmd[:2]), "...", flush=True)
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        sys.exit(f"{cmd[0]} failed with exit code {completed.returncode}")


def dump_db(source_url: str) -> Path:
    DUMP_DIR.mkdir(exist_ok=True)
    _run(
        [
            _pg_bin("pg_dump"),
            "--no-owner",
            "--no-acl",
            "--format=custom",
            "--file",
            str(DUMP_FILE),
            source_url,
        ]
    )
    return DUMP_FILE


def restore_db(dest_url: str) -> None:
    _run(
        [
            _pg_bin("pg_restore"),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-acl",
            "--dbname",
            dest_url,
            str(DUMP_FILE),
        ]
    )


def parse_yes() -> bool:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation (this overwrites the destination database)",
    )
    return parser.parse_args().yes


def confirm(message: str, assume_yes: bool) -> None:
    if assume_yes:
        return
    answer = input(f"{message}\nType YES to continue: ").strip()
    if answer != "YES":
        sys.exit("Aborted.")
