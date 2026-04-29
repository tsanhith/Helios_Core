"""SQLite database manager for Helios Core."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .schema import (
    CONVERSATIONS_TABLE,
    CONTACTS_TABLE,
    PROFILES_TABLE,
    SESSIONS_TABLE,
    ACTIONS_HISTORY_TABLE,
    INDEXES,
)

DB_PATH = Path(__file__).parent.parent / "data" / "helios.db"


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _ensure_data_dir(self):
        """Create data directory if needed."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        """Get SQLite connection with row factory."""
        self._ensure_data_dir()
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create tables
            cursor.execute(CONVERSATIONS_TABLE)
            cursor.execute(CONTACTS_TABLE)
            cursor.execute(PROFILES_TABLE)
            cursor.execute(SESSIONS_TABLE)
            cursor.execute(ACTIONS_HISTORY_TABLE)

            # Create indexes
            for index_sql in INDEXES:
                cursor.execute(index_sql)

            conn.commit()

    # ========== Conversation Methods ==========

    def save_conversation(
        self,
        session_id: str,
        command: str,
        response: str,
        actions: list[dict],
    ) -> int:
        """Save a conversation exchange."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO conversations
                   (session_id, command, response, actions)
                   VALUES (?, ?, ?, ?)""",
                (session_id, command, response, json.dumps(actions)),
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_conversations(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get recent conversations for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT command, response, actions, created_at
                   FROM conversations
                   WHERE session_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (session_id, limit),
            )
            rows = cursor.fetchall()
            return [
                {
                    "command": row["command"],
                    "response": row["response"],
                    "actions": json.loads(row["actions"]),
                    "created_at": row["created_at"],
                }
                for row in reversed(rows)  # Oldest first
            ]

    # ========== Session Methods ==========

    def create_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        """Create a new session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO sessions
                   (session_id, user_id, last_active)
                   VALUES (?, ?, ?)""",
                (session_id, user_id, datetime.now()),
            )
            conn.commit()

    def update_session_context(
        self,
        session_id: str,
        context: dict,
    ) -> None:
        """Update session context."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE sessions
                   SET context = ?, last_active = ?
                   WHERE session_id = ?""",
                (json.dumps(context), datetime.now(), session_id),
            )
            conn.commit()

    def get_session_context(self, session_id: str) -> Optional[dict]:
        """Get session context."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT context FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if row and row["context"]:
                return json.loads(row["context"])
            return None

    # ========== Contact Methods ==========

    def add_contact(
        self,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        aliases: Optional[list[str]] = None,
    ) -> int:
        """Add a contact."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO contacts (name, phone, email, aliases)
                   VALUES (?, ?, ?, ?)""",
                (name, phone, email, json.dumps(aliases or [])),
            )
            conn.commit()
            return cursor.lastrowid

    def get_contacts(self, search: Optional[str] = None) -> list[dict]:
        """Get contacts, optionally filtered by name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search:
                cursor.execute(
                    """SELECT * FROM contacts
                       WHERE name LIKE ? OR aliases LIKE ?
                       ORDER BY name""",
                    (f"%{search}%", f"%{search}%"),
                )
            else:
                cursor.execute("SELECT * FROM contacts ORDER BY name")
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "phone": row["phone"],
                    "email": row["email"],
                    "aliases": json.loads(row["aliases"] or "[]"),
                }
                for row in rows
            ]

    # ========== Profile Methods ==========

    def create_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        location: Optional[str] = None,
        timezone: str = "UTC",
        preferences: Optional[dict] = None,
    ) -> None:
        """Create or update user profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO profiles
                   (user_id, name, location, timezone, preferences, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                   name = excluded.name,
                   location = excluded.location,
                   timezone = excluded.timezone,
                   preferences = excluded.preferences,
                   updated_at = excluded.updated_at""",
                (user_id, name, location, timezone, json.dumps(preferences or {}), datetime.now()),
            )
            conn.commit()

    def get_profile(self, user_id: str) -> Optional[dict]:
        """Get user profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM profiles WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "location": row["location"],
                    "timezone": row["timezone"],
                    "preferences": json.loads(row["preferences"] or "{}"),
                }
            return None

    # ========== Action History Methods ==========

    def log_action(
        self,
        session_id: str,
        action_type: str,
        params: dict,
        confirmed: bool = False,
    ) -> int:
        """Log an action request."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO actions_history
                   (session_id, action_type, params, status, confirmed)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, action_type, json.dumps(params), "pending", confirmed),
            )
            conn.commit()
            return cursor.lastrowid

    def update_action_status(
        self,
        action_id: int,
        status: str,
        result: Optional[str] = None,
    ) -> None:
        """Update action status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE actions_history
                   SET status = ?, result = ?, completed_at = ?
                   WHERE id = ?""",
                (status, result, datetime.now() if status == "completed" else None, action_id),
            )
            conn.commit()

    def confirm_action(self, action_id: int, confirmed: bool = True) -> None:
        """Mark action as confirmed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE actions_history SET confirmed = ? WHERE id = ?",
                (confirmed, action_id),
            )
            conn.commit()


# Global database instance
db = Database()
