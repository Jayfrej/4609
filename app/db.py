import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            nickname TEXT,
            pid INTEGER,
            last_state TEXT DEFAULT 'offline',
            created_at TEXT DEFAULT (datetime('now'))
        )"""
    )
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

def add_account(account, nickname):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO accounts (account, nickname) VALUES (?, ?)", (account, nickname))
    conn.commit()
    conn.close()

def list_accounts():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, account, nickname, pid, last_state, created_at FROM accounts ORDER BY id DESC")
    rows = [{"id": r[0], "account": r[1], "nickname": r[2], "pid": r[3], "last_state": r[4], "created_at": r[5]} for r in c.fetchall()]
    conn.close()
    return rows

def get_account(acc_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, account, nickname, pid, last_state FROM accounts WHERE id=?", (acc_id,))
    r = c.fetchone()
    conn.close()
    if not r: return None
    return {"id": r[0], "account": r[1], "nickname": r[2], "pid": r[3], "last_state": r[4]}

def set_state(acc_id, state):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE accounts SET last_state=? WHERE id=?", (state, acc_id))
    conn.commit()
    conn.close()

def set_pid(acc_id, pid):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE accounts SET pid=? WHERE id=?", (pid, acc_id))
    conn.commit()
    conn.close()

def delete_account(acc_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
    conn.commit()
    conn.close()
