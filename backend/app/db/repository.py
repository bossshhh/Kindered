from .database import get_connection

PATIENT_FIELDS = ["name", "age", "gender", "marital_status", "mood", "conditions", "allergies", "mobility", "behavioral_traits", "preferences", "routines", "notes"]
RELATIVE_FIELDS = ["patient_id", "name", "age", "gender", "relationship", "personality", "communication_style", "preferences", "memories", "voice_name"]


def row_dict(row):
    return dict(row) if row else None


def create_patient(data):
    conn = get_connection()
    cur = conn.execute(
        f"INSERT INTO patients ({', '.join(PATIENT_FIELDS)}) VALUES ({', '.join('?' for _ in PATIENT_FIELDS)})",
        tuple(data.get(k, "") for k in PATIENT_FIELDS),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM patients WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_dict(row)


def update_patient(patient_id, data):
    conn = get_connection()
    assignments = ", ".join(f"{k}=?" for k in PATIENT_FIELDS)
    values = [data.get(k, "") for k in PATIENT_FIELDS] + [patient_id]
    conn.execute(f"UPDATE patients SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    conn.close()
    return row_dict(row)


def delete_patient(patient_id):
    conn = get_connection()
    cur = conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def list_patients():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    conn.close()
    return [row_dict(r) for r in rows]


def get_patient(patient_id):
    conn = get_connection()
    patient = conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    if not patient:
        conn.close()
        return None
    relatives = conn.execute("SELECT * FROM relatives WHERE patient_id=? ORDER BY id", (patient_id,)).fetchall()
    notes = conn.execute("SELECT * FROM doctor_notes WHERE patient_id=? ORDER BY id DESC", (patient_id,)).fetchall()
    suggestions = conn.execute("SELECT * FROM suggestions WHERE patient_id=? ORDER BY id DESC", (patient_id,)).fetchall()
    conn.close()
    result = row_dict(patient)
    result["relatives"] = [row_dict(r) for r in relatives]
    result["doctor_notes"] = [row_dict(n) for n in notes]
    result["suggestions"] = [row_dict(s) for s in suggestions]
    return result


def create_relative(data):
    conn = get_connection()
    cur = conn.execute(
        f"INSERT INTO relatives ({', '.join(RELATIVE_FIELDS)}) VALUES ({', '.join('?' for _ in RELATIVE_FIELDS)})",
        tuple(data.get(k, "") for k in RELATIVE_FIELDS),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM relatives WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_dict(row)


def update_relative(relative_id, data):
    conn = get_connection()
    fields = [k for k in RELATIVE_FIELDS if k != "patient_id"]
    assignments = ", ".join(f"{k}=?" for k in fields)
    values = [data.get(k, "") for k in fields] + [relative_id]
    conn.execute(f"UPDATE relatives SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM relatives WHERE id=?", (relative_id,)).fetchone()
    conn.close()
    return row_dict(row)


def delete_relative(relative_id):
    conn = get_connection()
    cur = conn.execute("DELETE FROM relatives WHERE id=?", (relative_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def add_note(patient_id, author, content):
    conn = get_connection()
    cur = conn.execute("INSERT INTO doctor_notes (patient_id, author, content) VALUES (?, ?, ?)", (patient_id, author, content))
    conn.commit()
    row = conn.execute("SELECT * FROM doctor_notes WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_dict(row)


def delete_note(note_id):
    conn = get_connection()
    cur = conn.execute("DELETE FROM doctor_notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def add_message(patient_id, role, content, intent="", risk_level="low", user_role="legacy"):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO messages (patient_id, role, content, intent, risk_level, user_role) VALUES (?, ?, ?, ?, ?, ?)",
        (patient_id, role, content, intent, risk_level, user_role),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_dict(row)


def get_recent_messages(patient_id, limit=12, user_role="legacy"):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, role, content, intent, risk_level, created_at FROM messages "
        "WHERE patient_id=? AND user_role=? ORDER BY id DESC LIMIT ?",
        (patient_id, user_role, limit),
    ).fetchall()
    conn.close()
    return [row_dict(r) for r in reversed(rows)]


def clear_messages(patient_id, user_role="elderly"):
    conn = get_connection()
    cur = conn.execute(
        "DELETE FROM messages WHERE patient_id=? AND user_role=?",
        (patient_id, user_role),
    )
    conn.commit()
    conn.close()
    return cur.rowcount


def add_suggestion(patient_id, author, target, content):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO suggestions (patient_id, author, target, content) VALUES (?, ?, ?, ?)",
        (patient_id, author, target, content),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM suggestions WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_dict(row)


def list_suggestions(patient_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM suggestions WHERE patient_id=? ORDER BY id DESC",
        (patient_id,),
    ).fetchall()
    conn.close()
    return [row_dict(r) for r in rows]


def analytics(patient_id):
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM messages WHERE patient_id=?", (patient_id,)).fetchone()[0]
    user_messages = conn.execute("SELECT COUNT(*) FROM messages WHERE patient_id=? AND role='user'", (patient_id,)).fetchone()[0]
    assistant_messages = conn.execute("SELECT COUNT(*) FROM messages WHERE patient_id=? AND role='assistant'", (patient_id,)).fetchone()[0]
    safety_flags = conn.execute("SELECT COUNT(*) FROM messages WHERE patient_id=? AND risk_level IN ('medium','critical')", (patient_id,)).fetchone()[0]
    intents = conn.execute("SELECT intent, COUNT(*) n FROM messages WHERE patient_id=? AND role='assistant' AND intent!='' GROUP BY intent ORDER BY n DESC", (patient_id,)).fetchall()
    daily = conn.execute("SELECT substr(created_at,1,10) day, COUNT(*) n FROM messages WHERE patient_id=? GROUP BY day ORDER BY day DESC LIMIT 14", (patient_id,)).fetchall()
    conn.close()
    return {
        "total_messages": total,
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "safety_flags": safety_flags,
        "intent_distribution": [row_dict(r) for r in intents],
        "daily_messages": [row_dict(r) for r in reversed(daily)],
    }
