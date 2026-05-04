"""OCR 히스토리 저장소 (SQLite).

- DB 파일: `<repo>/logs/history.db`
- 캡처 이미지: `<repo>/logs/captures/<timestamp>.png` (파일로 저장, DB엔 경로만)
- 외부 의존성 없음 (sqlite3는 표준 라이브러리)
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parents[2] / "logs"
_DB_PATH = _BASE_DIR / "history.db"
_CAPTURES_DIR = _BASE_DIR / "captures"


@dataclass
class HistoryEntry:
    id: int
    created_at: str           # ISO 8601 UTC
    mode: str                 # 'fullscreen' | 'region' | 'browser' | 'file' | 'unknown'
    source_url: str | None
    image_path: str | None
    text: str
    avg_confidence: float
    engine: str
    translation_target: str | None = None
    translation_text: str | None = None


# ── DB lifecycle ──────────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS history (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at          TEXT    NOT NULL,
                mode                TEXT    NOT NULL DEFAULT 'unknown',
                source_url          TEXT,
                image_path          TEXT,
                text                TEXT    NOT NULL DEFAULT '',
                avg_confidence      REAL    NOT NULL DEFAULT 0,
                engine              TEXT    NOT NULL DEFAULT '',
                translation_target  TEXT,
                translation_text    TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_history_created
                ON history(created_at DESC);
            """
        )


# ── CRUD ──────────────────────────────────────────────────────────────────────
def add_entry(
    *,
    text: str,
    image: Image.Image | None = None,
    mode: str = "unknown",
    source_url: str | None = None,
    avg_confidence: float = 0.0,
    engine: str = "",
    translation_target: str | None = None,
    translation_text: str | None = None,
) -> int:
    """새 OCR 결과를 히스토리에 추가. 이미지가 있으면 PNG로 저장하고 경로 기록."""
    init_db()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    image_path: str | None = None
    if image is not None:
        _CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        # 파일명 안전화: ISO timestamp의 ':' 제거
        safe = created_at.replace(":", "-").replace("+", "_")
        path = _CAPTURES_DIR / f"{safe}.png"
        # 동일 timestamp가 있으면 _2, _3 ... 접미사
        suffix = 1
        while path.exists():
            suffix += 1
            path = _CAPTURES_DIR / f"{safe}_{suffix}.png"
        try:
            image.save(path, format="PNG")
            image_path = str(path)
        except Exception:  # noqa: BLE001
            log.exception("history: failed to save capture image")

    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO history (
                created_at, mode, source_url, image_path, text,
                avg_confidence, engine, translation_target, translation_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                created_at,
                mode,
                source_url,
                image_path,
                text,
                avg_confidence,
                engine,
                translation_target,
                translation_text,
            ),
        )
        entry_id = int(cur.lastrowid or 0)
    log.info("history: added id=%d mode=%s text_len=%d", entry_id, mode, len(text))
    return entry_id


def update_translation(entry_id: int, target: str, text: str) -> None:
    """기존 항목에 번역 결과 추가/갱신."""
    init_db()
    with _connect() as conn:
        conn.execute(
            "UPDATE history SET translation_target=?, translation_text=? WHERE id=?",
            (target, text, entry_id),
        )
    log.debug("history: translation updated id=%d target=%s", entry_id, target)


def list_recent(limit: int = 200) -> list[HistoryEntry]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY datetime(created_at) DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_entry(r) for r in rows]


def get_entry(entry_id: int) -> HistoryEntry | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM history WHERE id=?", (entry_id,)
        ).fetchone()
    return _row_to_entry(row) if row else None


def delete_entry(entry_id: int) -> None:
    init_db()
    entry = get_entry(entry_id)
    if entry and entry.image_path:
        try:
            Path(entry.image_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            log.exception("history: failed to remove image %s", entry.image_path)
    with _connect() as conn:
        conn.execute("DELETE FROM history WHERE id=?", (entry_id,))
    log.info("history: deleted id=%d", entry_id)


def clear_all() -> None:
    init_db()
    entries = list_recent(limit=10_000_000)
    for e in entries:
        if e.image_path:
            try:
                Path(e.image_path).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
    with _connect() as conn:
        conn.execute("DELETE FROM history")
    log.info("history: cleared all (%d entries)", len(entries))


def _row_to_entry(row: sqlite3.Row) -> HistoryEntry:
    return HistoryEntry(
        id=row["id"],
        created_at=row["created_at"],
        mode=row["mode"] or "unknown",
        source_url=row["source_url"],
        image_path=row["image_path"],
        text=row["text"] or "",
        avg_confidence=row["avg_confidence"] or 0.0,
        engine=row["engine"] or "",
        translation_target=row["translation_target"],
        translation_text=row["translation_text"],
    )
