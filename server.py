import os, time, functools, base64, threading, logging
from flask import Flask, request, jsonify, send_from_directory, render_template, Response
from dotenv import load_dotenv

from app.db import init_db, add_account, list_accounts, delete_account, get_account, set_pid, set_state
from app.session_manager import SessionManager
from app.email_handler import send_email
from app.signal_router import normalize_payload, write_signal
from app.symbol_fetcher import fetch_symbols

load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")

# Logging
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "trading_bot.log")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()])
log = logging.getLogger("mt5")

# Config
BASIC_USER = os.getenv("BASIC_USER", "admin")
BASIC_PASS = os.getenv("BASIC_PASS", "admin")
BASIC_IDLE_TIMEOUT = int(os.getenv("BASIC_IDLE_TIMEOUT", "900"))

WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "dev-token")
EXTERNAL_BASE_URL = os.getenv("EXTERNAL_BASE_URL", "http://127.0.0.1:5000")

FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

MT5_MAIN_PATH = os.getenv("MT5_MAIN_PATH", "C:\\Program Files\\MetaTrader 5\\terminal64.exe")
MT5_INSTANCES_DIR = os.getenv("MT5_INSTANCES_DIR", "C:\\MT5\\instances")
MT5_PROFILE_SOURCE = os.getenv("MT5_PROFILE_SOURCE", "")

SYMBOL_AUTO_FETCH = os.getenv("SYMBOL_AUTO_FETCH", "true").lower() == "true"
SYMBOL_MATCH_CUTOFF = float(os.getenv("SYMBOL_MATCH_CUTOFF", "0.65"))

MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "10"))

# Init DB and session manager
init_db()
session_mgr = SessionManager(MT5_INSTANCES_DIR, MT5_PROFILE_SOURCE, MT5_MAIN_PATH)

# In-memory rate limit (IP+token)
RATE_LIMIT_WINDOW = 10
RATE_LIMIT_MAX = 5
_rate_mem = {}

# Basic auth + idle timeout (method 2)
_last_seen = {}

def _auth_fail():
    return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="mt5-admin"'})

def requires_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.headers.get("CF-Connecting-IP") or request.remote_addr or "0.0.0.0"
        now = time.time()
        # idle timeout check
        last = _last_seen.get(ip, 0)
        if last and (now - last > BASIC_IDLE_TIMEOUT):
            _last_seen.pop(ip, None)
            return _auth_fail()
        # check auth header
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return _auth_fail()
        try:
            user, pwd = base64.b64decode(auth.split(" ",1)[1]).decode("utf-8").split(":",1)
        except Exception:
            return _auth_fail()
        if user != BASIC_USER or pwd != BASIC_PASS:
            return _auth_fail()
        _last_seen[ip] = now
        return f(*args, **kwargs)
    return wrapper

# --------- Routes ---------
@app.get("/")
@requires_auth
def index():
    return render_template("index.html")

@app.get("/webhook-url")
@requires_auth
def get_webhook_url():
    return jsonify({"url": f"{EXTERNAL_BASE_URL.rstrip('/')}/webhook/{WEBHOOK_TOKEN}"})

@app.get("/accounts")
@requires_auth
def accounts():
    rows = list_accounts()
    for r in rows:
        r["alive"] = session_mgr.is_alive(r.get("pid"))
    return jsonify({"accounts": rows})

@app.post("/register")
@requires_auth
def register():
    data = request.get_json(force=True)
    account = str(data.get("account","")).strip()
    nickname = str(data.get("nickname","")).strip()
    if not account:
        return jsonify({"ok": False, "error": "Missing account"}), 400
    try:
        session_mgr.ensure_instance(account)
    except Exception as e:
        log.exception("Create instance failed")
        return jsonify({"ok": False, "error": f"Create instance failed: {e}"}), 500
    add_account(account, nickname)
    # Auto open MT5 after add
    try:
        pid = session_mgr.open(account)
        # fetch symbols for this account (optional)
        if SYMBOL_AUTO_FETCH:
            _ = fetch_symbols(MT5_MAIN_PATH, MT5_INSTANCES_DIR, account)
        # update pid/state
        from app.db import get_conn
        set_pid(get_account_id_by_account(account), pid)  # helper below
        set_state(get_account_id_by_account(account), "online")
        send_email("MT5 Instance Online", f"Account {account} ({nickname}) is online (PID {pid}).")
        log.info("[ONLINE] account=%s pid=%s", account, pid)
    except Exception as e:
        log.exception("Auto open failed")
    return jsonify({"ok": True})

def get_account_id_by_account(account: str) -> int:
    # helper to map account->id
    rows = list_accounts()
    for r in rows:
        if r["account"] == account:
            return r["id"]
    return -1

@app.post("/open/<int:acc_id>")
@requires_auth
def open_acc(acc_id: int):
    acc = get_account(acc_id)
    if not acc: return jsonify({"ok": False, "error": "Not found"}), 404
    pid = session_mgr.open(acc["account"])
    set_pid(acc_id, pid)
    if SYMBOL_AUTO_FETCH:
        _ = fetch_symbols(MT5_MAIN_PATH, MT5_INSTANCES_DIR, acc["account"])
    set_state(acc_id, "online")
    send_email("MT5 Instance Online", f"Account {acc['account']} ({acc['nickname']}) is online (PID {pid}).")
    log.info("[ONLINE] account=%s pid=%s", acc["account"], pid)
    return jsonify({"ok": True, "pid": pid})

@app.post("/restart/<int:acc_id>")
@requires_auth
def restart(acc_id: int):
    acc = get_account(acc_id)
    if not acc: return jsonify({"ok": False, "error": "Not found"}), 404
    pid = session_mgr.restart(acc.get("pid"), acc["account"])
    set_pid(acc_id, pid)
    if SYMBOL_AUTO_FETCH:
        _ = fetch_symbols(MT5_MAIN_PATH, MT5_INSTANCES_DIR, acc["account"])
    set_state(acc_id, "online")
    send_email("MT5 Instance Online", f"Account {acc['account']} ({acc['nickname']}) restarted (PID {pid}).")
    log.info("[RESTART] account=%s pid=%s", acc["account"], pid)
    return jsonify({"ok": True, "pid": pid})

@app.post("/stop/<int:acc_id>")
@requires_auth
def stop(acc_id: int):
    acc = get_account(acc_id)
    if not acc: return jsonify({"ok": False, "error": "Not found"}), 404
    if acc.get("pid"):
        session_mgr.stop(acc["pid"])
        set_pid(acc_id, None)
    set_state(acc_id, "offline")
    send_email("MT5 Instance Offline", f"Account {acc['account']} ({acc['nickname']}) stopped.")
    log.info("[OFFLINE] account=%s", acc["account"])
    return jsonify({"ok": True})

@app.delete("/delete/<int:acc_id>")
@requires_auth
def delete_acc(acc_id: int):
    acc = get_account(acc_id)
    if not acc: return jsonify({"ok": False, "error": "Not found"}), 404
    if acc.get("pid"):
        session_mgr.stop(acc["pid"])
    delete_account(acc_id)
    log.info("[DELETE] account=%s", acc["account"])
    return jsonify({"ok": True})

# ---------- Webhook ----------
@app.post("/webhook/<token>")
def webhook(token):
    client_ip = request.headers.get("CF-Connecting-IP") or request.remote_addr or "0.0.0.0"
    if token != WEBHOOK_TOKEN:
        send_email("Unauthorized Webhook", f"Bad token from {client_ip}")
        logging.warning("[UNAUTHORIZED] ip=%s", client_ip)
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    # rate-limit
    now = time.time()
    key = f"{client_ip}:{token}"
    arr = [t for t in _rate_mem.get(key, []) if now - t <= RATE_LIMIT_WINDOW]
    if len(arr) >= RATE_LIMIT_MAX:
        _rate_mem[key] = arr
        return jsonify({"ok": False, "error": "Too Many Requests"}), 429
    arr.append(now); _rate_mem[key] = arr

    try:
        raw = request.get_json(force=True)
    except Exception:
        send_email("Bad Payload", f"Invalid JSON from {client_ip}")
        logging.error("[BAD_PAYLOAD] ip=%s json=parse_error", client_ip)
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400

    try:
        norm = normalize_payload(raw, MT5_INSTANCES_DIR, cutoff=SYMBOL_MATCH_CUTOFF)
    except Exception as e:
        send_email("Bad Payload", f"{e} | from {client_ip} | raw={raw}")
        logging.error("[BAD_PAYLOAD] ip=%s err=%s raw=%s", client_ip, e, raw)
        return jsonify({"ok": False, "error": str(e)}), 400

    # ensure account exists
    account = None; acc_id = None
    for r in list_accounts():
        if str(r["account"]) == norm["account_number"]:
            account = r; acc_id = r["id"]; break
    if not account:
        return jsonify({"ok": False, "error": "Account not registered"}), 404

    try:
        path = write_signal(MT5_INSTANCES_DIR, norm["account_number"], norm)
        logging.info("[WEBHOOK] acc=%s sym_in=%s sym_out=%s action=%s vol=%s",
                     norm["account_number"], raw.get("symbol"), norm["symbol"], norm["action"], norm["volume"])
        return jsonify({"ok": True, "signal_path": path, "normalized": norm})
    except Exception as e:
        send_email("Signal Write Error", f"{e} | acc={norm['account_number']}")
        logging.exception("Signal write failed")
        return jsonify({"ok": False, "error": f"Signal write failed: {e}"}), 500

# ---------- Health ----------
@app.route("/health", methods=["GET","HEAD"])
def health():
    return jsonify({"status":"ok"}), 200

# ---------- Logs ----------
@app.get("/logs")
@requires_auth
def logs_view():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-200:]
        return jsonify({"logs": lines})
    except Exception as e:
        return jsonify({"logs": [f"log read error: {e}\n"]})

# ---------- Background monitor for Online/Offline ----------
def monitor_loop():
    from app.db import get_conn
    while True:
        try:
            rows = list_accounts()
            for r in rows:
                alive = session_mgr.is_alive(r.get("pid"))
                state = "online" if alive else "offline"
                if state != r.get("last_state"):
                    # update and notify
                    set_state(r["id"], state)
                    subj = f"MT5 Instance {'Online' if alive else 'Offline'}"
                    body = f"Account {r['account']} ({r['nickname']}) is now {state.upper()}."
                    send_email(subj, body)
                    log.info("[STATE] account=%s -> %s", r["account"], state)
        except Exception:
            log.exception("monitor loop error")
        time.sleep(max(5, MONITOR_INTERVAL))

threading.Thread(target=monitor_loop, daemon=True).start()

@app.get("/static/<path:path>")
def static_proxy(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG)
