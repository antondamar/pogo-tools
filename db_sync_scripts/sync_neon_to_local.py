import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_sync import confirm, dump_db, load_urls, parse_yes, restore_db


def main() -> None:
    neon, local = load_urls()
    confirm("This will OVERWRITE your local database with Neon data.", parse_yes())
    print("Dumping Neon...")
    dump_db(neon)
    print("Restoring into local...")
    restore_db(local)
    print("Done: Neon -> local")


if __name__ == "__main__":
    main()
