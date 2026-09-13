import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT DEFAULT '',
            marital_status TEXT DEFAULT '',
            mood TEXT DEFAULT '',
            conditions TEXT DEFAULT '',
            allergies TEXT DEFAULT '',
            mobility TEXT DEFAULT '',
            behavioral_traits TEXT DEFAULT '',
            preferences TEXT DEFAULT '',
            routines TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS relatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT DEFAULT '',
            relationship TEXT DEFAULT '',
            personality TEXT DEFAULT '',
            communication_style TEXT DEFAULT '',
            preferences TEXT DEFAULT '',
            memories TEXT DEFAULT '',
            voice_name TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT DEFAULT '',
            risk_level TEXT DEFAULT 'low',
            user_role TEXT NOT NULL DEFAULT 'legacy',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS doctor_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            target TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
        );
        """
    )
    # Backwards-compatible migration for databases created by the previous MVP.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(patients)").fetchall()}
    if "updated_at" not in cols:
        conn.execute("ALTER TABLE patients ADD COLUMN updated_at TEXT")
    cols = {row[1] for row in conn.execute("PRAGMA table_info(relatives)").fetchall()}
    if "updated_at" not in cols:
        conn.execute("ALTER TABLE relatives ADD COLUMN updated_at TEXT")

    cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
    if "user_role" not in cols:
        conn.execute("ALTER TABLE messages ADD COLUMN user_role TEXT NOT NULL DEFAULT 'legacy'")

    count = conn.execute("SELECT COUNT(*) AS n FROM patients").fetchone()[0]
    if count == 0:
        conn.execute(
            """INSERT INTO patients
            (name, age, gender, marital_status, mood, conditions, allergies, mobility,
             behavioral_traits, preferences, routines, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Maria Demo", 82, "Female", "Widowed", "Generally calm",
                "Hypertension (demo data only)", "None recorded", "Walks independently",
                "Warm, occasionally lonely, enjoys familiar stories",
                "Family, gardening, old photographs, soft music, simple home cooking",
                "Morning tea around 9; light breakfast; short afternoon walk for steps; early supper",
                "DEMO PROFILE — not real clinical data."
            )
        )
        patient_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """INSERT INTO relatives
            (patient_id, name, age, gender, relationship, personality, communication_style, preferences, memories, voice_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                patient_id, "Sarah Demo", 48, "Female", "daughter",
                "Warm, reassuring, lightly humorous", "Gentle, familiar, short sentences",
                "Family, gardening, memories",
                "DEMO MEMORY: Sarah and Maria enjoy talking about the garden and family gatherings.",
                "Browser default voice"
            )
        )
    conn.commit()
    conn.close()
