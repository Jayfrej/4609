import os, json
import MetaTrader5 as mt5
from .mt5_handler import instance_dir_for

def fetch_symbols(terminal_path: str, instances_root: str, account: str) -> list[str]:
    """Initialize MT5 in portable mode for this instance and fetch symbols.
    Requires MT5 installed; does not store passwords.
    """
    inst_dir = instance_dir_for(instances_root, account)
    ok = mt5.initialize(path=terminal_path, portable=True, data_path=inst_dir)
    if not ok:
        return []
    try:
        infos = mt5.symbols_get()
        symbols = sorted({s.name for s in infos}) if infos else []
    finally:
        mt5.shutdown()
    # save to file
    out = os.path.join(inst_dir, "symbols_list.json")
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(symbols, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return symbols
