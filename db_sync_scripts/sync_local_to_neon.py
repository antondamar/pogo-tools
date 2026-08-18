import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_sync import confirm, dump_db, load_urls, parse_yes, restore_db


def main() -> None:
    neon, local = load_urls()
    confirm("This will OVERWRITE Neon with your local database.", parse_yes())
    print("Dumping local...")
    dump_db(local)
    print("Restoring into Neon...")
    restore_db(neon)
    print("Done: local -> Neon")


if __name__ == "__main__":
    main()
