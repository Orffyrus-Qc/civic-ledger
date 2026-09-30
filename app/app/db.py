from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH
from .dedup import canonical_key

_lock = threading.Lock()

FINDING_COLUMNS = {
    "origin": "TEXT DEFAULT 'model'",
    "review_status": "TEXT DEFAULT 'pending'",
    "canonical_key": "TEXT",
    "source_date": "TEXT",
    "money_amount": "REAL",
    "language": "TEXT DEFAULT 'en'",
    "updated_at": "TEXT",
    "hidden": "INTEGER DEFAULT 0",
    "country": "TEXT DEFAULT 'CA'",
}

HIT_COLUMNS = {
    "content_hash": "TEXT",
    "fetched_at": "TEXT",
    "raw_text": "TEXT",
    "topic": "TEXT",
    "category_hint": "TEXT",
    "country": "TEXT DEFAULT 'CA'",
}

CLAIM_COLUMNS = {
    "board": "INTEGER DEFAULT 0",
    "cohort": "TEXT",
    "evidence_url": "TEXT",
    "evidence_title": "TEXT",
    "score_note": "TEXT",
    "scored_at": "TEXT",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _migrate_hits_unique(conn: sqlite3.Connection) -> None:
    """Older DBs unique(url, query) blocked later scans. Keep one row per URL."""
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='hits'"
    ).fetchone()
    if not sql or "UNIQUE" not in (sql[0] or "").upper():
        return
    if "url TEXT NOT NULL UNIQUE" in (sql[0] or "") and "url, query" not in (sql[0] or "").lower():
        return
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS hits_migrated (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            query TEXT,
            title TEXT,
            url TEXT NOT NULL UNIQUE,
            snippet TEXT,
            engine TEXT,
            kind TEXT,
            created_at TEXT NOT NULL,
            content_hash TEXT,
            fetched_at TEXT,
            raw_text TEXT,
            topic TEXT,
            category_hint TEXT
        );
        INSERT OR IGNORE INTO hits_migrated(
            id, scan_id, query, title, url, snippet, engine, kind, created_at,
            content_hash, fetched_at, raw_text, topic, category_hint
        )
        SELECT id, scan_id, query, title, url, snippet, engine, kind, created_at,
               content_hash, fetched_at, raw_text, topic, category_hint
        FROM hits;
        DROP TABLE hits;
        ALTER TABLE hits_migrated RENAME TO hits;
        """
    )


def _add_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, decl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def init_db() -> None:
    with session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                reason TEXT,
                queries INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                findings INTEGER DEFAULT 0,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER,
                query TEXT,
                title TEXT,
                url TEXT NOT NULL UNIQUE,
                snippet TEXT,
                engine TEXT,
                kind TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT NOT NULL,
                claim TEXT,
                evidence TEXT,
                entities TEXT,
                money TEXT,
                promise_status TEXT,
                confidence REAL DEFAULT 0.4,
                severity TEXT DEFAULT 'medium',
                sources TEXT NOT NULL,
                url_key TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            );

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                kind TEXT DEFAULT 'institution',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS entity_findings (
                entity_id INTEGER NOT NULL,
                finding_id INTEGER NOT NULL,
                PRIMARY KEY (entity_id, finding_id)
            );

            CREATE TABLE IF NOT EXISTS money_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER,
                finding_id INTEGER,
                role TEXT NOT NULL,
                actor TEXT NOT NULL,
                counterpart TEXT,
                amount REAL,
                currency TEXT DEFAULT 'CAD',
                event_date TEXT,
                source_url TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                minister TEXT,
                status TEXT,
                source_url TEXT,
                source_date TEXT,
                body TEXT,
                language TEXT DEFAULT 'en',
                created_at TEXT NOT NULL,
                UNIQUE(title, minister)
            );

            CREATE TABLE IF NOT EXISTS claim_matches (
                claim_id INTEGER NOT NULL,
                finding_id INTEGER NOT NULL,
                score REAL,
                note TEXT,
                PRIMARY KEY (claim_id, finding_id)
            );
            """
        )
        _add_columns(conn, "findings", FINDING_COLUMNS)
        _add_columns(conn, "hits", HIT_COLUMNS)
        _add_columns(conn, "claims", CLAIM_COLUMNS)
        _add_columns(conn, "scans", {"country": "TEXT DEFAULT 'CA'"})
        _add_columns(conn, "money_events", {"country": "TEXT DEFAULT 'CA'"})
        _migrate_hits_unique(conn)
        conn.execute(
            "UPDATE claims SET board=1, cohort='mandate_2025' "
            "WHERE title LIKE 'Carney 2025 mandate priority%' AND IFNULL(board,0)=0"
        )
        conn.execute(
            "UPDATE claims SET board=1, cohort='platform_2025' "
            "WHERE minister LIKE '%2025 platform%' AND IFNULL(board,0)=0"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_cat ON findings(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_created ON findings(created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_key ON findings(canonical_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hits_url ON hits(url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_money_actor ON money_events(actor)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_slug ON entities(slug)")


def start_scan(reason: str, country: str = "CA") -> int:
    with session() as conn:
        cur = conn.execute(
            "INSERT INTO scans(started_at, status, reason, country) VALUES (?, 'running', ?, ?)",
            (utcnow(), reason, country or "CA"),
        )
        return int(cur.lastrowid)


def finish_scan(
    scan_id: int,
    status: str,
    queries: int,
    hits: int,
    findings: int,
    error: str | None = None,
) -> None:
    with session() as conn:
        conn.execute(
            """
            UPDATE scans
            SET finished_at=?, status=?, queries=?, hits=?, findings=?, error=?
            WHERE id=?
            """,
            (utcnow(), status, queries, hits, findings, error, scan_id),
        )


def upsert_hit(scan_id: int, hit: dict[str, Any]) -> tuple[int, bool]:
    """Return (id, changed). changed means new URL or content hash moved."""
    now = utcnow()
    url = hit["url"]
    new_hash = hit.get("content_hash") or ""
    country = hit.get("country") or "CA"
    with session() as conn:
        row = conn.execute(
            "SELECT * FROM hits WHERE url=? AND IFNULL(country,'CA')=?",
            (url, country),
        ).fetchone()
        if not row:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO hits(
                        scan_id, query, title, url, snippet, engine, kind, created_at,
                        content_hash, fetched_at, raw_text, topic, category_hint, country
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scan_id,
                        hit.get("query") or "",
                        hit.get("title") or "",
                        url,
                        hit.get("snippet") or "",
                        hit.get("engine") or "",
                        hit.get("kind") or "",
                        now,
                        new_hash,
                        now,
                        (hit.get("text") or "")[:8000],
                        hit.get("topic") or "",
                        hit.get("category_hint") or "",
                        country,
                    ),
                )
                return int(cur.lastrowid), True
            except sqlite3.IntegrityError:
                row = conn.execute("SELECT * FROM hits WHERE url=?", (url,)).fetchone()
                if not row:
                    raise
                return int(row["id"]), False
        old_hash = row["content_hash"] or ""
        changed = bool(new_hash) and new_hash != old_hash
        conn.execute(
            """
            UPDATE hits SET scan_id=?, query=?, title=?, snippet=?, engine=?, kind=?,
                content_hash=?, fetched_at=?, raw_text=?, topic=?, category_hint=?, country=?
            WHERE id=?
            """,
            (
                scan_id,
                hit.get("query") or row["query"],
                hit.get("title") or row["title"],
                hit.get("snippet") or row["snippet"],
                hit.get("engine") or row["engine"],
                hit.get("kind") or row["kind"],
                new_hash or old_hash,
                now,
                (hit.get("text") or row["raw_text"] or "")[:8000],
                hit.get("topic") or row["topic"],
                hit.get("category_hint") or row["category_hint"],
                country,
                row["id"],
            ),
        )
        return int(row["id"]), changed or not old_hash


def upsert_finding(scan_id: int, item: dict[str, Any]) -> tuple[int, bool]:
    """Merge on canonical_key. Returns (id, inserted)."""
    sources = item.get("sources") or []
    url_key = str(sources[0].get("url") or "") if sources else ""
    key = item.get("canonical_key") or canonical_key(item)
    now = utcnow()
    with session() as conn:
        existing = conn.execute(
            "SELECT * FROM findings WHERE canonical_key=?",
            (key,),
        ).fetchone()
        if not existing and url_key and (item.get("origin") or "model") != "extracted":
            existing = conn.execute(
                "SELECT * FROM findings WHERE url_key=? AND url_key!=''",
                (url_key,),
            ).fetchone()
        payload = (
            scan_id,
            item.get("title") or "Untitled",
            item.get("category") or "other",
            item.get("summary") or "",
            item.get("claim") or "",
            item.get("evidence") or "",
            json.dumps(item.get("entities") or [], ensure_ascii=False),
            json.dumps(item.get("money") or {}, ensure_ascii=False),
            item.get("promise_status") or "n/a",
            float(item.get("confidence") or 0.4),
            item.get("severity") or "medium",
            json.dumps(sources, ensure_ascii=False),
            url_key,
            item.get("origin") or "model",
            item.get("review_status") or "pending",
            key,
            item.get("source_date"),
            item.get("money_amount"),
            item.get("language") or "en",
            now,
            1 if item.get("hidden") else 0,
        )
        if existing:
            keep_review = existing["review_status"] if existing["review_status"] in {"confirmed", "rejected"} else item.get("review_status") or "pending"
            payload_list = list(payload)
            # origin, review_status are indices 13, 14 in payload
            payload_list[14] = keep_review
            conn.execute(
                """
                UPDATE findings SET
                    scan_id=?, title=?, category=?, summary=?, claim=?, evidence=?,
                    entities=?, money=?, promise_status=?, confidence=?, severity=?,
                    sources=?, url_key=?, origin=?, review_status=?, canonical_key=?,
                    source_date=?, money_amount=?, language=?, updated_at=?, hidden=?
                WHERE id=?
                """,
                tuple(payload_list) + (int(existing["id"]),),
            )
            fid = int(existing["id"])
            inserted = False
        else:
            cur = conn.execute(
                """
                INSERT INTO findings(
                    scan_id, title, category, summary, claim, evidence, entities, money,
                    promise_status, confidence, severity, sources, url_key, origin,
                    review_status, canonical_key, source_date, money_amount, language,
                    updated_at, hidden, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload + (now,),
            )
            fid = int(cur.lastrowid)
            inserted = True
        conn.execute(
            "UPDATE findings SET country=? WHERE id=?",
            (item.get("country") or "CA", fid),
        )
    _link_entities(fid, item.get("entities") or [])
    return fid, inserted


def _link_entities(finding_id: int, entities: list[Any]) -> None:
    from .util import slugify

    if not isinstance(entities, list):
        return
    now = utcnow()
    with session() as conn:
        for raw in entities[:12]:
            name = str(raw).strip()
            if len(name) < 2:
                continue
            slug = slugify(name)
            conn.execute(
                "INSERT OR IGNORE INTO entities(slug, name, kind, created_at) VALUES (?, ?, 'public', ?)",
                (slug, name, now),
            )
            row = conn.execute("SELECT id FROM entities WHERE slug=?", (slug,)).fetchone()
            if row:
                conn.execute(
                    "INSERT OR IGNORE INTO entity_findings(entity_id, finding_id) VALUES (?, ?)",
                    (row["id"], finding_id),
                )


def insert_money_event(scan_id: int, finding_id: int | None, event: dict[str, Any]) -> int:
    with session() as conn:
        cur = conn.execute(
            """
            INSERT INTO money_events(
                scan_id, finding_id, role, actor, counterpart, amount, currency,
                event_date, source_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                finding_id,
                event.get("role") or "unknown",
                event.get("actor") or "",
                event.get("counterpart"),
                event.get("amount"),
                event.get("currency") or "CAD",
                event.get("event_date"),
                event.get("source_url"),
                utcnow(),
            ),
        )
        mid = int(cur.lastrowid)
        conn.execute(
            "UPDATE money_events SET country=? WHERE id=?",
            (event.get("country") or "CA", mid),
        )
        return mid


def upsert_claim(item: dict[str, Any]) -> int:
    with session() as conn:
        conn.execute(
            """
            INSERT INTO claims(
                title, minister, status, source_url, source_date, body, language,
                created_at, board, cohort
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(title, minister) DO UPDATE SET
                body=excluded.body,
                source_date=excluded.source_date,
                source_url=excluded.source_url,
                board=CASE WHEN excluded.board=1 THEN 1 ELSE IFNULL(board,0) END,
                cohort=COALESCE(excluded.cohort, cohort)
            """,
            (
                item.get("title") or "",
                item.get("minister") or "",
                item.get("status") or "unverified",
                item.get("source_url"),
                item.get("source_date"),
                item.get("body") or "",
                item.get("language") or "en",
                utcnow(),
                1 if item.get("board") else 0,
                item.get("cohort"),
            ),
        )
        row = conn.execute(
            "SELECT id FROM claims WHERE title=? AND minister=?",
            (item.get("title") or "", item.get("minister") or ""),
        ).fetchone()
        return int(row["id"])


def update_claim_score(claim_id: int, item: dict[str, Any]) -> None:
    with session() as conn:
        conn.execute(
            """
            UPDATE claims SET
                status=?, evidence_url=?, evidence_title=?, score_note=?, scored_at=?
            WHERE id=?
            """,
            (
                item.get("status") or "unverified",
                item.get("evidence_url"),
                item.get("evidence_title"),
                item.get("score_note"),
                utcnow(),
                claim_id,
            ),
        )


def list_board_claims() -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            "SELECT * FROM claims WHERE IFNULL(board,0)=1 ORDER BY cohort, title"
        ).fetchall()
    return [dict(r) for r in rows]


def list_scoreboard() -> dict[str, Any]:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM claims WHERE IFNULL(board,0)=1
            ORDER BY cohort, title
            """
        ).fetchall()
    items = [dict(r) for r in rows]
    missions = [c for c in items if (c.get("cohort") or "") == "mandate_2025"]
    platform = [c for c in items if (c.get("cohort") or "") == "platform_2025"]
    counts = {"kept": 0, "partial": 0, "broken": 0, "unverified": 0}
    for c in items:
        st = c.get("status") or "unverified"
        if st not in counts:
            st = "unverified"
        counts[st] += 1
    return {
        "missions": missions,
        "platform": platform,
        "counts": counts,
        "scored_at": next((c.get("scored_at") for c in items if c.get("scored_at")), None),
    }


def link_claim(claim_id: int, finding_id: int, score: float, note: str = "") -> None:
    with session() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO claim_matches(claim_id, finding_id, score, note)
            VALUES (?, ?, ?, ?)
            """,
            (claim_id, finding_id, score, note),
        )


def list_findings(
    category: str | None = None,
    q: str | None = None,
    q_terms: list[str] | None = None,
    limit: int = 100,
    hide_low: bool = True,
    hide_unverified: bool = True,
    hide_rejected: bool = True,
    sort: str = "date",
    include_hidden: bool = False,
    country: str = "CA",
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM findings WHERE IFNULL(country,'CA')=?"
    args: list[Any] = [country or "CA"]
    if not include_hidden:
        sql += " AND IFNULL(hidden,0)=0"
    if hide_rejected:
        sql += " AND IFNULL(review_status,'pending')!='rejected'"
    if hide_low:
        sql += " AND IFNULL(confidence,0) >= 0.4"
    if hide_unverified:
        sql += " AND IFNULL(promise_status,'n/a')!='unverified'"
    if category and category != "all":
        sql += " AND category=?"
        args.append(category)
    terms = [t for t in (q_terms or []) if t] or ([q] if q else [])
    if terms:
        parts = []
        for term in terms[:6]:
            parts.append("(title LIKE ? OR summary LIKE ? OR claim LIKE ? OR entities LIKE ?)")
            like = f"%{term}%"
            args.extend([like, like, like, like])
        sql += " AND (" + " OR ".join(parts) + ")"
    if sort == "money":
        sql += " ORDER BY IFNULL(money_amount,0) DESC, created_at DESC"
    elif sort == "confidence":
        sql += " ORDER BY IFNULL(confidence,0) DESC, created_at DESC"
    else:
        sql += " ORDER BY IFNULL(source_date, created_at) DESC, id DESC"
    sql += " LIMIT ?"
    args.append(limit)
    with session() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [_finding_row(r) for r in rows]


def get_finding(finding_id: int) -> dict[str, Any] | None:
    with session() as conn:
        row = conn.execute("SELECT * FROM findings WHERE id=?", (finding_id,)).fetchone()
        if not row:
            return None
        item = _finding_row(row)
        matches = conn.execute(
            """
            SELECT c.id, c.title, c.minister, c.status, m.score, m.note
            FROM claim_matches m JOIN claims c ON c.id=m.claim_id
            WHERE m.finding_id=?
            """,
            (finding_id,),
        ).fetchall()
        item["claims"] = [dict(m) for m in matches]
        money = conn.execute(
            "SELECT * FROM money_events WHERE finding_id=? ORDER BY id DESC",
            (finding_id,),
        ).fetchall()
        item["money_events"] = [dict(m) for m in money]
        return item


def set_review(finding_id: int, status: str) -> bool:
    if status not in {"pending", "confirmed", "rejected"}:
        return False
    with session() as conn:
        cur = conn.execute(
            "UPDATE findings SET review_status=?, updated_at=? WHERE id=?",
            (status, utcnow(), finding_id),
        )
        return cur.rowcount > 0


def quarantine_junk() -> int:
    from .util import looks_like_junk_title

    n = 0
    with session() as conn:
        rows = conn.execute("SELECT id, title, origin, confidence FROM findings").fetchall()
        for row in rows:
            if looks_like_junk_title(row["title"]) or (
                (row["origin"] or "model") == "model" and (row["confidence"] or 0) < 0.3
            ):
                conn.execute(
                    "UPDATE findings SET hidden=1, review_status='rejected', updated_at=? WHERE id=?",
                    (utcnow(), row["id"]),
                )
                n += 1
    return n


def stats(country: str = "CA") -> dict[str, Any]:
    cc = country or "CA"
    with session() as conn:
        visible = conn.execute(
            "SELECT COUNT(*) AS n FROM findings WHERE IFNULL(hidden,0)=0 AND IFNULL(review_status,'pending')!='rejected' AND IFNULL(country,'CA')=?",
            (cc,),
        ).fetchone()["n"]
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM findings WHERE IFNULL(country,'CA')=?", (cc,)
        ).fetchone()["n"]
        hits = conn.execute(
            "SELECT COUNT(*) AS n FROM hits WHERE IFNULL(country,'CA')=?", (cc,)
        ).fetchone()["n"]
        money_n = conn.execute(
            "SELECT COUNT(*) AS n FROM money_events WHERE IFNULL(country,'CA')=?", (cc,)
        ).fetchone()["n"]
        claims_n = (
            conn.execute("SELECT COUNT(*) AS n FROM claims").fetchone()["n"] if cc == "CA" else 0
        )
        cats = {
            r["category"]: r["n"]
            for r in conn.execute(
                """
                SELECT category, COUNT(*) AS n FROM findings
                WHERE IFNULL(hidden,0)=0 AND IFNULL(review_status,'pending')!='rejected'
                  AND IFNULL(country,'CA')=?
                GROUP BY category
                """,
                (cc,),
            )
        }
        last = conn.execute(
            "SELECT * FROM scans WHERE IFNULL(country,'CA')=? ORDER BY id DESC LIMIT 1",
            (cc,),
        ).fetchone()
        running = conn.execute(
            "SELECT COUNT(*) AS n FROM scans WHERE status='running' AND IFNULL(country,'CA')=?",
            (cc,),
        ).fetchone()["n"]
    return {
        "findings": visible,
        "findings_all": total,
        "hits": hits,
        "money_events": money_n,
        "claims": claims_n,
        "categories": cats,
        "running": running > 0,
        "last_scan": dict(last) if last else None,
    }


def list_hits(limit: int = 80, country: str = "CA") -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            "SELECT id, scan_id, query, title, url, snippet, engine, kind, created_at, topic FROM hits WHERE IFNULL(country,'CA')=? ORDER BY id DESC LIMIT ?",
            (country or "CA", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_scans(limit: int = 20, country: str = "CA") -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            "SELECT * FROM scans WHERE IFNULL(country,'CA')=? ORDER BY id DESC LIMIT ?",
            (country or "CA", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_money(limit: int = 100, country: str = "CA") -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            "SELECT * FROM money_events WHERE IFNULL(country,'CA')=? ORDER BY IFNULL(amount,0) DESC, id DESC LIMIT ?",
            (country or "CA", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_claims(
    limit: int = 200,
    q: str | None = None,
    q_terms: list[str] | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM claims WHERE 1=1"
    args: list[Any] = []
    terms = [t for t in (q_terms or []) if t] or ([q] if q else [])
    if terms:
        parts = []
        for term in terms[:6]:
            parts.append("(title LIKE ? OR minister LIKE ? OR body LIKE ?)")
            like = f"%{term}%"
            args.extend([like, like, like])
        sql += " AND (" + " OR ".join(parts) + ")"
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with session() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def get_entity(slug: str) -> dict[str, Any] | None:
    with session() as conn:
        ent = conn.execute("SELECT * FROM entities WHERE slug=?", (slug,)).fetchone()
        if not ent:
            return None
        findings = conn.execute(
            """
            SELECT f.* FROM findings f
            JOIN entity_findings ef ON ef.finding_id=f.id
            WHERE ef.entity_id=? AND IFNULL(f.hidden,0)=0
            ORDER BY IFNULL(f.source_date, f.created_at) DESC
            """,
            (ent["id"],),
        ).fetchall()
        money = conn.execute(
            "SELECT * FROM money_events WHERE actor=? OR counterpart=? ORDER BY id DESC LIMIT 50",
            (ent["name"], ent["name"]),
        ).fetchall()
    return {
        **dict(ent),
        "findings": [_finding_row(r) for r in findings],
        "money_events": [dict(m) for m in money],
    }


def list_entities(limit: int = 80) -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT e.*, COUNT(ef.finding_id) AS n
            FROM entities e
            LEFT JOIN entity_findings ef ON ef.entity_id=e.id
            GROUP BY e.id
            ORDER BY n DESC, e.name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def overlapping_money_actors() -> list[tuple[str, str]]:
    with session() as conn:
        vendors = [
            r["actor"]
            for r in conn.execute(
                "SELECT DISTINCT actor FROM money_events WHERE role='vendor'"
            )
        ]
        lobby = [
            r["actor"]
            for r in conn.execute(
                "SELECT DISTINCT actor FROM money_events WHERE role IN ('lobbyist','client')"
            )
        ]
    pairs = []
    lobby_l = {a.lower(): a for a in lobby}
    for v in vendors:
        if v.lower() in lobby_l:
            pairs.append((v, lobby_l[v.lower()]))
    return pairs


def _finding_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ("entities", "money", "sources"):
        raw = item.get(key)
        if isinstance(raw, str):
            try:
                item[key] = json.loads(raw)
            except json.JSONDecodeError:
                item[key] = [] if key != "money" else {}
    return item
