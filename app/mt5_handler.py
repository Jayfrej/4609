import os, shutil, subprocess, re

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def copy_tree(src: str, dst: str):
    if not os.path.exists(src):
        raise FileNotFoundError(f"Profile source not found: {src}")
    shutil.copytree(src, dst, dirs_exist_ok=True)

def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())[:80]

def instance_dir_for(instances_root: str, account: str):
    return os.path.join(instances_root, _safe(account))

def create_instance(instances_root: str, profile_source: str, account: str):
    inst = instance_dir_for(instances_root, account)
    ensure_dir(inst)
    copy_tree(profile_source, inst)
    return inst

def start_mt5(terminal_path: str, instance_dir: str):
    cmd = [terminal_path, "/portable", f"/datapath:{instance_dir}"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.pid

def stop_process(pid: int):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill","/PID",str(pid),"/F"], check=False)
        else:
            os.kill(pid, 9)
    except Exception:
        pass
