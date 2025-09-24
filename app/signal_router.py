import os, json, time, uuid, difflib
from typing import Dict, Any, List
from .mt5_handler import instance_dir_for

def load_symbol_list(instances_root: str, account: str) -> List[str]:
    inst = instance_dir_for(instances_root, account)
    path = os.path.join(inst, "symbols_list.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def auto_map_symbol(input_symbol: str, available: List[str], cutoff: float=0.65) -> str:
    s = (input_symbol or "").strip().upper()
    if not s: return s
    av = [a.upper() for a in available] if available else []
    if not av: return s
    matches = difflib.get_close_matches(s, av, n=1, cutoff=cutoff)
    if matches: return matches[0]
    return s

ACTION_MAP = {
    "BUY": "BUY",
    "SELL": "SELL",
    "BUY_LIMIT": "BUY_LIMIT",
    "SELL_LIMIT": "SELL_LIMIT",
    "BUY_STOP": "BUY_STOP",
    "SELL_STOP": "SELL_STOP",
    "LONG": "BUY",
    "SHORT": "SELL",
}

REQUIRED = ["account_number","symbol","action","volume"]

def normalize_payload(payload: Dict[str, Any], instances_root: str, cutoff: float=0.65) -> Dict[str, Any]:
    for f in REQUIRED:
        if f not in payload:
            raise ValueError(f"Missing field: {f}")
    account = str(payload.get("account_number")).strip()
    action_in = str(payload.get("action") or "").strip().upper()
    action = ACTION_MAP.get(action_in, action_in)
    if action in ("BUY_LIMIT","SELL_LIMIT","BUY_STOP","SELL_STOP") and payload.get("price") is None:
        raise ValueError("price is required for pending orders")

    available = load_symbol_list(instances_root, account)
    symbol = auto_map_symbol(payload.get("symbol"), available, cutoff=cutoff)

    norm = {
        "account_number": account,
        "symbol": symbol,
        "action": action,
        "volume": float(payload.get("volume", 0)),
        "take_profit": float(payload["take_profit"]) if "take_profit" in payload and payload["take_profit"] is not None else None,
        "stop_loss": float(payload["stop_loss"]) if "stop_loss" in payload and payload["stop_loss"] is not None else None,
        "price": float(payload["price"]) if "price" in payload and payload["price"] is not None else None,
        "comment": payload.get("comment","WebhookBridge"),
        "magic": int(payload.get("magic", 0)),
        "received_ts": int(time.time())
    }
    return norm

def write_signal(instances_root: str, account: str, signal: Dict[str, Any]) -> str:
    inst_dir = instance_dir_for(instances_root, account)
    sig_dir = os.path.join(inst_dir, "MQL5", "Files", "signals")
    os.makedirs(sig_dir, exist_ok=True)
    name = f"signal_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    path = os.path.join(sig_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(signal, f, ensure_ascii=False, indent=2)
    return path
