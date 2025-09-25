# app/session_manager.py
# -*- coding: utf-8 -*-
"""
SessionManager – clone MT5 program + overlay profile, then run per-account instance.

Workflow
--------
- instances_root/<ACCOUNT>/  จะถูกสร้างใหม่ทุกครั้ง (โคลนโปรแกรม + โปรไฟล์)
- โคลน "โปรแกรม" มาจากโฟลเดอร์ที่มี MT5_MAIN_PATH (terminal64.exe)
- overlay โปรไฟล์/ค่า Default จาก MT5_PROFILE_SOURCE (Data Folder ที่คุณตั้งไว้จริง)
- เปิดด้วย terminal64.exe /portable โดย cwd=instance
- ไม่ทำ auto-login (คุณล็อกอินเอง)
"""

import os
import re
import shutil
import subprocess
import logging
import psutil
from typing import Optional

logger = logging.getLogger(__name__)

# ------------------------ helpers ------------------------ #

def _safe(name: str) -> str:
    """Sanitize account/nickname to safe folder name."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name).strip())[:80]

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _copy_tree(src: str, dst: str) -> None:
    """
    Copy a directory tree (merge/overwrite).
    Requires Python 3.8+: shutil.copytree(..., dirs_exist_ok=True)
    """
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source path not found: {src}")
    shutil.copytree(src, dst, dirs_exist_ok=True)

def _copy_if_exists(src: str, dst: str) -> None:
    """Copy file or directory if exists."""
    if not os.path.exists(src):
        return
    if os.path.isdir(src):
        _copy_tree(src, dst)
    else:
        _ensure_dir(os.path.dirname(dst))
        shutil.copy2(src, dst)

# ------------------------ core class ------------------------ #

class SessionManager:
    """
    สร้าง/เปิด/ปิด MT5 instance ต่อบัญชี
    - โคลนโฟลเดอร์ "โปรแกรม" จากโฟลเดอร์ของ MT5_MAIN_PATH
    - overlay โปรไฟล์/Default/EA จาก MT5_PROFILE_SOURCE
    - เปิดด้วย /portable (cwd=instance)
    """

    def __init__(self, instances_root: str, profile_source: str, terminal_path: str):
        """
        Parameters
        ----------
        instances_root : str
            รากโฟลเดอร์สำหรับเก็บอินสแตนซ์ทั้งหมด (ต้องเขียนได้)
        profile_source : str
            Data Folder ต้นทางที่ตั้งค่าไว้จริง (มี config/servers.dat, profiles หรือ MQL5/Profiles/Default)
            ตัวอย่าง: C:\\Users\\User\\AppData\\Roaming\\MetaQuotes\\Terminal\\<HASH>
        terminal_path : str
            เส้นทางไปยัง terminal64.exe ของ MT5 หลัก (เช่น C:\\Program Files\\MetaTrader 5\\terminal64.exe)
            เราจะใช้โฟลเดอร์ของไฟล์นี้เป็น "โฟลเดอร์โปรแกรมต้นทาง"
        """
        self.instances_root = os.path.abspath(instances_root)
        _ensure_dir(self.instances_root)

        self.profile_source = os.path.abspath(profile_source)
        self.terminal_path = os.path.abspath(terminal_path)
        self.program_source = os.path.dirname(self.terminal_path)

        if not os.path.isfile(self.terminal_path):
            raise FileNotFoundError(f"terminal64.exe not found: {self.terminal_path}")
        if not os.path.isdir(self.program_source):
            raise FileNotFoundError(f"Program source folder not found: {self.program_source}")
        if not os.path.isdir(self.profile_source):
            raise FileNotFoundError(f"Profile source folder not found: {self.profile_source}")

        # เตือนหากไม่มี servers.dat ในโปรไฟล์ (จะทำให้ขึ้น wizard Open an account)
        servers_dat = os.path.join(self.profile_source, "config", "servers.dat")
        if not os.path.isfile(servers_dat):
            logger.warning("servers.dat not found in MT5_PROFILE_SOURCE: %s", servers_dat)

    # ------------------------ paths ------------------------ #

    def _instance_dir(self, account: str) -> str:
        return os.path.join(self.instances_root, _safe(account))

    # ------------------------ lifecycle ------------------------ #

    def ensure_instance(self, account: str) -> str:
        """
        สร้างอินสแตนซ์ใหม่ (ลบของเก่าออก เพื่อให้ได้ค่า Default ล่าสุดเสมอ)
        - โคลนโฟลเดอร์โปรแกรมทั้งหมด
        - overlay โปรไฟล์/ค่า default/EA จาก profile_source
        - เตรียม temp/EBWebView กัน error
        """
        inst = self._instance_dir(account)

        # ลบทิ้งถ้ามีของเก่า
        if os.path.exists(inst):
            try:
                shutil.rmtree(inst)
            except Exception as e:
                logger.warning("Remove old instance failed (%s): %s", inst, e)

        logger.info("Clone MT5 program → %s", inst)
        _copy_tree(self.program_source, inst)

        # overlay เฉพาะส่วนที่เกี่ยวกับโปรไฟล์/ค่า default
        # 1) config (servers.dat, terminal.ini, ฯลฯ)
        _copy_if_exists(os.path.join(self.profile_source, "config"), os.path.join(inst, "config"))

        # 2) profiles (root profiles ของ MT5 รุ่นเก่า/บาง build ใช้โฟลเดอร์นี้)
        _copy_if_exists(os.path.join(self.profile_source, "profiles"), os.path.join(inst, "profiles"))

        # 3) MQL5/Profiles/Default (MT5 รุ่นใหม่/ส่วนใหญ่ใช้โฟลเดอร์นี้เป็น layout หลัก)
        _copy_if_exists(
            os.path.join(self.profile_source, "MQL5", "Profiles"),
            os.path.join(inst, "MQL5", "Profiles")
        )

        # 4) Experts/Indicators/Files ที่คุณเตรียมไว้ใน profile_source (ถ้ามี)
        for sub in ["MQL5\\Experts", "MQL5\\Indicators", "MQL5\\Files", "MQL5\\Libraries", "MQL5\\Include"]:
            _copy_if_exists(
                os.path.join(self.profile_source, *sub.split("\\")),
                os.path.join(inst, *sub.split("\\"))
            )

        # ป้องกัน EBWebView error
        _ensure_dir(os.path.join(inst, "temp", "EBWebView"))

        return inst

    def open(self, account: str) -> int:
        """
        เปิดอินสแตนซ์สำหรับบัญชี (ใช้ exe ของอินสแตนซ์ + /portable)
        """
        inst = self._instance_dir(account)
        if not os.path.exists(inst):
            inst = self.ensure_instance(account)

        exe = os.path.join(inst, "terminal64.exe")
        if not os.path.isfile(exe):
            # สำรอง (ไม่น่าจะเกิด ถ้าโคลนโปรแกรมสำเร็จ)
            exe = self.terminal_path

        cmd = [exe, "/portable"]
        logger.info("Starting MT5 (account=%s): %s", account, " ".join(cmd))
        proc = subprocess.Popen(cmd, cwd=inst, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.pid

    def restart(self, pid: Optional[int], account: str) -> int:
        """หยุดตัวเดิม (ถ้ามี) แล้วเปิดใหม่"""
        if pid:
            self.stop(pid)
        return self.open(account)

    def stop(self, pid: Optional[int]) -> None:
        """หยุดโปรเซสตาม PID"""
        if not pid:
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)
            else:
                os.kill(int(pid), 9)
        except Exception as e:
            logger.error("Error stopping process %s: %s", pid, e)

    def is_alive(self, pid: Optional[int]) -> bool:
        """
        ตรวจสอบว่า process MT5 (PID) ยังทำงานอยู่หรือไม่
        ใช้โดย monitor_loop ใน server.py
        """
        if not pid:
            return False
        try:
            p = psutil.Process(int(pid))
            return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            return False
