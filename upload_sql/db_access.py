"""Import db.py from the project root when running scripts inside upload_sql/."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db import get_db_connection  # noqa: E402

__all__ = ["get_db_connection"]
