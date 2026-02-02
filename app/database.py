import sqlite3
from typing import Optional
from .config import DATABASE_FILE, MAX_MEMORY_MESSAGES, logger


def get_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_FILE)


def init_database():
    """Initialize the database tables"""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT,
            first_name TEXT,
            username TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Messages table for conversation memory
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Create index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_user_id
        ON messages (user_id, created_at DESC)
    ''')

    # Suggestions table for storing button suggestions temporarily
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            suggestion_id TEXT PRIMARY KEY,
            text TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")


# ==================== USER FUNCTIONS ====================

def get_user_language(user_id: int) -> Optional[str]:
    """Get user's selected language"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def set_user_language(user_id: int, language: str, first_name: str = None, username: str = None):
    """Set or update user's language preference"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO users (user_id, language, first_name, username)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            language = excluded.language,
            first_name = COALESCE(excluded.first_name, users.first_name),
            username = COALESCE(excluded.username, users.username)
    ''', (user_id, language, first_name, username))

    conn.commit()
    conn.close()
    logger.info(f"👤 User {user_id} language set to: {language}")


def user_exists(user_id: int) -> bool:
    """Check if user exists in database"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


# ==================== MEMORY FUNCTIONS ====================

def add_message(user_id: int, role: str, content: str):
    """Add a message to conversation history"""
    conn = get_connection()
    cursor = conn.cursor()

    # Insert new message
    cursor.execute('''
        INSERT INTO messages (user_id, role, content)
        VALUES (?, ?, ?)
    ''', (user_id, role, content))

    # Clean up old messages (keep only last MAX_MEMORY_MESSAGES * 2 to have buffer)
    cursor.execute('''
        DELETE FROM messages
        WHERE user_id = ? AND id NOT IN (
            SELECT id FROM messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        )
    ''', (user_id, user_id, MAX_MEMORY_MESSAGES * 2))

    conn.commit()
    conn.close()


def get_conversation_history(user_id: int, limit: int = None) -> list:
    """Get recent conversation history for a user"""
    if limit is None:
        limit = MAX_MEMORY_MESSAGES

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT role, content FROM (
            SELECT role, content, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ) ORDER BY created_at ASC
    ''', (user_id, limit))

    messages = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
    conn.close()

    return messages


def clear_user_history(user_id: int):
    """Clear conversation history for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    logger.info(f"🗑️ Cleared history for user {user_id}")


# ==================== SUGGESTION FUNCTIONS ====================

def store_suggestion(suggestion_id: str, text: str):
    """Store a suggestion text for later retrieval"""
    conn = get_connection()
    cursor = conn.cursor()

    # Insert or replace suggestion
    cursor.execute('''
        INSERT OR REPLACE INTO suggestions (suggestion_id, text)
        VALUES (?, ?)
    ''', (suggestion_id, text))

    # Clean up old suggestions (older than 24 hours)
    cursor.execute('''
        DELETE FROM suggestions
        WHERE created_at < datetime('now', '-24 hours')
    ''')

    conn.commit()
    conn.close()


def get_suggestion(suggestion_id: str) -> Optional[str]:
    """Get suggestion text by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT text FROM suggestions WHERE suggestion_id = ?', (suggestion_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
