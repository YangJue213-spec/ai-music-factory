"""State Management - SQLite-based persistent state"""
import sqlite3
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """SQLite-based state manager for tracking processed songs and tasks"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "./data/state.db"
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._lock = asyncio.Lock()
        
    def _init_db(self):
        """Initialize database tables"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS processed_songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT,
                    source TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_hash ON processed_songs(hash);
                CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_songs(processed_at);
                
                CREATE TABLE IF NOT EXISTS suno_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    song_hash TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result TEXT,
                    error TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_task_id ON suno_tasks(task_id);
                CREATE INDEX IF NOT EXISTS idx_song_hash ON suno_tasks(song_hash);
                
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_fetched INTEGER DEFAULT 0,
                    total_cleaned INTEGER DEFAULT 0,
                    total_generated INTEGER DEFAULT 0,
                    total_failed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS artist_albums (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artist TEXT NOT NULL,
                    album_id TEXT NOT NULL,
                    album_name TEXT,
                    publish_date TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(artist, album_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_artist ON artist_albums(artist);
            """)
            
    @contextmanager
    def _get_conn(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    async def is_processed(self, song_hash: str) -> bool:
        """Check if a song has been processed"""
        async with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM processed_songs WHERE hash = ?",
                    (song_hash,)
                )
                return cursor.fetchone() is not None
                
    async def mark_processed(self, song_hash: str, title: str, artist: str = "",
                           source: str = "", metadata: Optional[Dict] = None):
        """Mark a song as processed"""
        async with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO processed_songs 
                       (hash, title, artist, source, metadata, processed_at)
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (song_hash, title, artist, source, 
                     json.dumps(metadata) if metadata else None)
                )
                logger.debug(f"Marked as processed: {title} ({song_hash})")
                
    async def get_processed_hashes(self, days: int = 30) -> List[str]:
        """Get list of processed song hashes within N days"""
        async with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """SELECT hash FROM processed_songs 
                       WHERE processed_at > datetime('now', ?)
                       ORDER BY processed_at DESC""",
                    (f"-{days} days",)
                )
                return [row["hash"] for row in cursor.fetchall()]
                
    async def create_suno_task(self, task_id: str, song_hash: str) -> bool:
        """Create a new Suno generation task"""
        async with self._lock:
            try:
                with self._get_conn() as conn:
                    conn.execute(
                        """INSERT INTO suno_tasks (task_id, song_hash, status)
                           VALUES (?, ?, 'pending')""",
                        (task_id, song_hash)
                    )
                return True
            except sqlite3.IntegrityError:
                logger.warning(f"Task {task_id} already exists")
                return False
                
    async def update_suno_task(self, task_id: str, status: str, 
                              result: Optional[str] = None,
                              error: Optional[str] = None):
        """Update Suno task status"""
        async with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    """UPDATE suno_tasks 
                       SET status = ?, result = ?, error = ?, 
                           updated_at = CURRENT_TIMESTAMP
                       WHERE task_id = ?""",
                    (status, result, error, task_id)
                )
                
    async def get_suno_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get Suno task by ID"""
        async with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM suno_tasks WHERE task_id = ?",
                    (task_id,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
    async def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending Suno tasks"""
        async with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """SELECT * FROM suno_tasks 
                       WHERE status IN ('pending', 'queued', 'running')
                       ORDER BY created_at ASC"""
                )
                return [dict(row) for row in cursor.fetchall()]
                
    async def is_artist_album_processed(self, artist: str, album_id: str) -> bool:
        """Check if an artist album has been processed"""
        async with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """SELECT 1 FROM artist_albums 
                       WHERE artist = ? AND album_id = ?""",
                    (artist, album_id)
                )
                return cursor.fetchone() is not None
                
    async def mark_artist_album_processed(self, artist: str, album_id: str,
                                         album_name: str = "", 
                                         publish_date: str = ""):
        """Mark artist album as processed"""
        async with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO artist_albums 
                       (artist, album_id, album_name, publish_date, processed_at)
                       VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (artist, album_id, album_name, publish_date)
                )
                
    async def update_daily_stats(self, date: Optional[str] = None, **kwargs):
        """Update daily statistics"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        async with self._lock:
            with self._get_conn() as conn:
                # Insert or update stats
                columns = ", ".join(kwargs.keys())
                placeholders = ", ".join(["?"] * len(kwargs))
                updates = ", ".join([f"{k} = {k} + ?" for k in kwargs.keys()])
                
                conn.execute(f"""
                    INSERT INTO daily_stats (date, {columns})
                    VALUES (?, {placeholders})
                    ON CONFLICT(date) DO UPDATE SET
                        {updates},
                        updated_at = CURRENT_TIMESTAMP
                """, (date, *kwargs.values(), *kwargs.values()))
                
    async def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get daily statistics"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        async with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "SELECT * FROM daily_stats WHERE date = ?",
                    (date,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return {
                    "date": date,
                    "total_fetched": 0,
                    "total_cleaned": 0,
                    "total_generated": 0,
                    "total_failed": 0
                }
                
    async def cleanup_old_records(self, days: int = 90):
        """Clean up old processed song records"""
        async with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """DELETE FROM processed_songs 
                       WHERE processed_at < datetime('now', ?)""",
                    (f"-{days} days",)
                )
                deleted = cursor.rowcount
                logger.info(f"Cleaned up {deleted} old records")
                return deleted