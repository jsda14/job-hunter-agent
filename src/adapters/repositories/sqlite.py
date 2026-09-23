import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
from typing import List, Optional, Union

from src.domain.models.job import JobEvaluation, JobRaw
from src.domain.ports.repository import JobRepositoryPort


class SQLiteJobRepositoryAdapter(JobRepositoryPort):
    """Adapter for persisting and deduplicating jobs using native SQLite with thread-safe execution."""

    def __init__(self, db_path: Union[str, Path] = "data/job_hunter.db") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            path_obj = Path(self.db_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._lock = threading.Lock()

        # RN-01: Initialize database schema
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_jobs (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    is_actionable INTEGER NOT NULL,
                    fit_score REAL,
                    first_seen_at TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

    async def is_seen(self, job_id: str) -> bool:
        """RN-02: Check if a job ID already exists in processed_jobs."""
        def _sync_is_seen() -> bool:
            with self._lock:
                cursor = self._conn.execute(
                    "SELECT 1 FROM processed_jobs WHERE id = ?", (job_id,)
                )
                return cursor.fetchone() is not None

        return await asyncio.to_thread(_sync_is_seen)

    async def save_job(self, job: JobRaw, evaluation: Optional[JobEvaluation] = None) -> None:
        """RN-04: Persist or update job record idempotently."""
        def _sync_save() -> None:
            now_utc = datetime.now(timezone.utc).isoformat()
            is_actionable = 1 if (evaluation and evaluation.is_actionable) else 0
            fit_score = evaluation.fit_score if evaluation else None
            platform_str = job.platform.value if hasattr(job.platform, "value") else str(job.platform)

            with self._lock:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO processed_jobs (
                        id, platform, company, title, url, is_actionable, fit_score, first_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.id,
                        platform_str,
                        job.company,
                        job.title,
                        str(job.url),
                        is_actionable,
                        fit_score,
                        now_utc,
                    ),
                )
                self._conn.commit()

        await asyncio.to_thread(_sync_save)

    async def filter_unseen(self, jobs: List[JobRaw]) -> List[JobRaw]:
        """RN-03, CB-02: Filter and return only previously unseen jobs preserving original order."""
        if not jobs:
            return []

        def _sync_filter() -> List[JobRaw]:
            with self._lock:
                placeholders = ",".join("?" for _ in jobs)
                cursor = self._conn.execute(
                    f"SELECT id FROM processed_jobs WHERE id IN ({placeholders})",
                    [job.id for job in jobs],
                )
                seen_ids = {row[0] for row in cursor.fetchall()}
                return [job for job in jobs if job.id not in seen_ids]

        return await asyncio.to_thread(_sync_filter)
