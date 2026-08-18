"""Create tables and load Pokemon reference data.

Usage (from the project root, venv activated):

    python scripts/init_db.py
    python scripts/init_db.py --neon
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"
SCHEMA_FILE = SQL_DIR / "schema.sql"

SEED_TABLES = (
    (
        "species",
        "COPY species (id, form, name, type_1, type_2, base_attack, base_defense, base_stamina) "
        "FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')",
    ),
    (
        "moves",
        "COPY moves (id, name, type, is_fast_move, pve_power, pve_energy_delta, duration_ms, "
        "damage_window_start_ms, damage_window_end_ms, pvp_power, pvp_energy_delta) "
        "FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')",
    ),
    (
        "species_moves",
        "COPY species_moves (species_id, species_form, move_id, is_elite_move) "
        "FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')",
    ),
)


def load_target_url(use_neon: bool) -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    if use_neon:
        url = os.getenv("NEON_DATABASE_URL")
        if not url:
            sys.exit("Set NEON_DATABASE_URL in .env")
        return url
    url = os.getenv("LOCAL_DATABASE_URL")
    if not url:
        sys.exit("Set LOCAL_DATABASE_URL in .env")
    return url


def ensure_local_database(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return

    dbname = parsed.path.lstrip("/").split("?")[0]
    if not dbname:
        sys.exit("LOCAL_DATABASE_URL is missing a database name")

    try:
        conn = psycopg2.connect(url)
        conn.close()
        return
    except psycopg2.OperationalError as exc:
        message = str(exc)
        if "does not exist" not in message:
            raise

    admin_url = urlunparse(parsed._replace(path="/postgres"))
    admin = psycopg2.connect(admin_url)
    admin.autocommit = True
    try:
        with admin.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone():
                return
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
            print(f"Created database {dbname}")
    finally:
        admin.close()


def apply_schema(cur) -> None:
    schema = SCHEMA_FILE.read_text(encoding="utf-8")
    cur.execute(schema)


def species_is_empty(cur) -> bool:
    cur.execute("SELECT COUNT(*) FROM species")
    return cur.fetchone()[0] == 0


def load_seed(cur) -> None:
    for name, copy_sql in SEED_TABLES:
        path = SQL_DIR / f"{name}.csv"
        if not path.exists():
            sys.exit(f"Missing seed file: {path}")
        with path.open("r", encoding="utf-8", newline="") as handle:
            cur.copy_expert(copy_sql, handle)
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        print(f"Loaded {cur.fetchone()[0]} rows into {name}")

        cur.execute("SELECT setval('moves_id_seq', (SELECT MAX(id) FROM moves))")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create schema and load Pokemon reference data")
    parser.add_argument(
        "--neon",
        action="store_true",
        help="Initialize NEON_DATABASE_URL instead of LOCAL_DATABASE_URL",
    )
    args = parser.parse_args()

    if not SCHEMA_FILE.exists():
        sys.exit(f"Missing {SCHEMA_FILE}")

    url = load_target_url(args.neon)
    if not args.neon:
        ensure_local_database(url)

    target = "Neon" if args.neon else "local"
    print(f"Initializing {target} database...")

    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            apply_schema(cur)
            print("Schema ready")
            if species_is_empty(cur):
                load_seed(cur)
            else:
                print("Species data already present; skipped seed")
        conn.commit()

    print("Done. You can run: streamlit run app.py")


if __name__ == "__main__":
    main()
