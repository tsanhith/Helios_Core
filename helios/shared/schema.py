"""SQLite schema definitions for Helios Core."""

CONVERSATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    command TEXT NOT NULL,
    response TEXT,
    actions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CONTACTS_TABLE = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    aliases TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    name TEXT,
    location TEXT,
    timezone TEXT DEFAULT 'UTC',
    preferences TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT,
    context TEXT,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ACTIONS_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS actions_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    params TEXT,
    status TEXT DEFAULT 'pending',
    result TEXT,
    confirmed BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);",
    "CREATE INDEX IF NOT EXISTS idx_actions_session ON actions_history(session_id, created_at);",
]

SCHEMA_VERSION = 1

MIGRATIONS = [
    # Future migrations go here
]
