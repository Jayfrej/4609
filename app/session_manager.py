# app/session_manager.py
import os
import re
import shutil
import subprocess
import logging
import psutil

logger = logging.getLogger(__name__)

def _safe(name: str) -> str:
    """ทำชื่อโฟลเดอร์ให้ปลอดภัย"""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name).strip())[:80]

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _avoid_bad_roots(instances_root: str) -> str:
    """ถ้า instances_root อยู่ใน OneDrive/Desktop/Downloads ให้ย้ายไปที่ %USERPROFILE%\\MT5\\instances"""
    bad = ["\\OneDrive\\", "\\Desktop\\", "\\Downloads\\"]
    if any(b in instances_root for b in bad):
        user_root = os.path.join(os.path.expanduser("~"), "MT5", "instances")
        _ensure_dir(user_root)
        return user_root
    _ensure_dir(instances_root)
    return instances_root

class SessionManager:
    """
    รุ่นที่คุณต้องการ:
    - โคลน MT5 ทั้งชุดจากโฟลเดอร์ master (โฟลเดอร์เดียวกับ terminal64.exe)
    - วางไว้ที่ MT5_INSTANCES_DIR/<ACCOUNT>
    - เปิดด้วย terminal64.exe ของ instance นั้น (ใช้ /portable)
    - ไม่ auto-login, คุณล็อกอินเองใน MT5
    หมายเหตุ: server.py เรียก __init__(instances_root, profile_source, terminal_path)
    เราจะตีความ:
        instances_root = MT5_INSTANCES_DIR
        terminal_path  = MT5_MAIN_PATH (เช่น C:\\MT5\\master\\terminal64.exe)
        profile_source ไม่ใช้แล้ว (คงพารามิเตอร์ไว้เพื่อไม่ต้องแก้ server.py)
    """
    def __init__(self, instances_root: str, _profile_source_unused: str, terminal_path: str):
        self.instances_root = _avoid_bad_roots(instances_root)
        self.terminal_path = terminal_path
        # master_dir = โฟลเดอร์ที่มี terminal64.exe (คือโปรแกรม MT5 ต้นทางที่เซ็ตค่า default ไว้แล้ว)
        self.master_dir = os.path.dirname(os.path.abspath(self.terminal_path))

        if not os.path.exists(self.terminal_path):
            raise FileNotFoundError(f"MT5_MAIN_PATH (terminal64.exe) not found: {self.terminal_path}")
        if not os.path.isdir(self.master_dir):
            raise FileNotFoundError(f"Master directory not found: {self.master_dir}")

    def _instance_dir(self, account: str) -> str:
        return os.path.join(self.instances_root, _safe(account))

    def is_alive(self, pid: int) -> bool:
        if not pid:
            return False
        try:
            p = psutil.Process(pid)
            return p.is_running() and (p.status() != psutil.STATUS_ZOMBIE)
        except Exception:
            return False

    def ensure_instance(self, account: str) -> str:
        """
        โคลน MT5 master ไปเป็น instance ของบัญชี
        ถ้ามีอยู่แล้ว จะลบทิ้งแล้วโคลนใหม่ (เพื่อให้ได้ default ล่าสุดตามต้องการ)
        """
        inst = self._instance_dir(account)
        # ลบทิ้งถ้ามีของเก่า (ตามที่คุณต้องการให้ “คัดลอกทั้งชุดทุกครั้ง”)
        if os.path.exists(inst):
            try:
                logger.info("Removing old instance at %s", inst)
                shutil.rmtree(inst)
            except Exception as e:
                logger.warning("Failed to remove old instance: %s", e)
        logger.info("Cloning MT5 master -> %s", inst)
        shutil.copytree(self.master_dir, inst)

        # กัน error EBWebView โดยเตรียม temp/EBWebView ที่ datapath ของ instance
        _ensure_dir(os.path.join(inst, "temp", "EBWebView"))
        return inst

    def open(self, account: str) -> int:
        """
        เปิด MT5 instance ของบัญชีนั้น
        """
        inst = self._instance_dir(account)
        if not os.path.exists(inst):
            # ถ้ายังไม่เคย ensure ก็โคลนให้เลย
            inst = self.ensure_instance(account)

        exe_path = os.path.join(inst, "terminal64.exe")
        if not os.path.exists(exe_path):
            # ถ้าไม่มี exe ใน instance (เช่น โคลนไม่ครบ) ให้สำรองไปเรียก exe จาก master แต่ใช้ datapath=inst
            exe_path = self.terminal_path

        # ใช้ /portable ให้ชัวร์ว่าข้อมูลอยู่ใต้ inst เอง
        cmd = [exe_path, "/portable"]
        # ถ้า exe_path ไม่ใช่ของ instance (เช่นใช้ตัว master) ก็ยังโอเค เพราะเราคัดลอกทั้งชุดแล้ว
        logger.info("Starting MT5: %s", " ".join(cmd))
        proc = subprocess.Popen(cmd, cwd=inst, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.pid

    def restart(self, pid: int, account: str) -> int:
        if pid:
            self.stop(pid)
        return self.open(account)

    def stop(self, pid: int):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)
            else:
                os.kill(pid, 9)
        except Exception as e:
            logger.error("Error stopping process %s: %s", pid, e)
