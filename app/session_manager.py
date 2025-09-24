import os, psutil
from .mt5_handler import create_instance, start_mt5, stop_process, instance_dir_for

class SessionManager:
    def __init__(self, instances_root: str, profile_source: str, terminal_path: str):
        self.instances_root = instances_root
        self.profile_source = profile_source
        self.terminal_path = terminal_path

    def is_alive(self, pid: int) -> bool:
        if not pid: return False
        try:
            p = psutil.Process(pid)
            return p.is_running() and (p.status() != psutil.STATUS_ZOMBIE)
        except Exception:
            return False

    def ensure_instance(self, account: str):
        inst_dir = instance_dir_for(self.instances_root, account)
        if not os.path.exists(inst_dir) or not os.listdir(inst_dir):
            create_instance(self.instances_root, self.profile_source, account)
        return inst_dir

    def open(self, account: str):
        inst = self.ensure_instance(account)
        return start_mt5(self.terminal_path, inst)

    def restart(self, pid: int, account: str):
        if pid:
            try: stop_process(pid)
            except Exception: pass
        return self.open(account)

    def stop(self, pid: int):
        stop_process(pid)
