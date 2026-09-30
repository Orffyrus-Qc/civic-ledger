from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import BACKUP_DIR, DB_PATH


def backup_db(keep: int = 7) -> Path | None:
    if not DB_PATH.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"cpl-{stamp}.sqlite"
    shutil.copy2(DB_PATH, dest)
    old = sorted(BACKUP_DIR.glob("cpl-*.sqlite"))
    for extra in old[:-keep]:
        extra.unlink(missing_ok=True)
    return dest
