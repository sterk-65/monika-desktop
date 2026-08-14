# -*- coding: utf-8 -*-
"""系统事件通知：下载完成 / 插拔电源 / 设备连接 / 程序退出"""
import os
import threading
import time

try:
    import psutil
except Exception:
    psutil = None


def _dl_folder():
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0C, None, 0, buf) == 0:  # CSIDL_DOWNLOADS
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Downloads")


class EventWatcher(threading.Thread):
    """后台事件监听线程：下载/电源/设备/进程退出，通过 on_event 回调"""

    def __init__(self, on_event):
        super().__init__(daemon=True)
        self.on_event = on_event  # on_event(kind, zh, en, emotion)
        self._known_dl = set()
        self._dl_prev = {}
        self._plugged = None
        self._devices = set()
        self._procs = {}
        self._last = {}

    def _cool(self, key, secs):
        if time.time() - self._last.get(key, 0) < secs:
            return True
        self._last[key] = time.time()
        return False

    def _check_downloads(self):
        try:
            folder = _dl_folder()
            now = time.time()
            cur = {}
            for f in os.scandir(folder):
                if f.is_file() and f.stat().st_size > 200 * 1024:
                    cur[f.name] = (f.stat().st_size, f.stat().st_mtime)
            for name, (size, mtime) in cur.items():
                if name in self._known_dl:
                    continue
                # 新文件：且 10 秒内大小稳定（下载完成）
                prev = self._dl_prev.get(name)
                if prev and prev[0] == size and now - mtime < 30:
                    self._known_dl.add(name)
                    if not self._cool("dl", 120):
                        self.on_event("download", "下载完成啦？是什么好东西，也给我看看？",
                                      "Download finished? What is it — let me see too?", "happy")
                else:
                    self._dl_prev[name] = (size, mtime)
            self._known_dl = {k for k in self._known_dl if k in cur}
            self._dl_prev = {k: v for k, v in self._dl_prev.items() if k in cur}
        except Exception:
            pass

    def _check_power(self):
        try:
            if not psutil:
                return
            b = psutil.sensors_battery()
            if not b:
                return
            plugged = bool(b.power_plugged)
            if self._plugged is not None and plugged != self._plugged:
                if plugged:
                    if not self._cool("plug", 60):
                        self.on_event("power", "插上电源了，这样我就放心啦。",
                                      "You plugged in the power — now I can rest easy.", "happy")
                else:
                    if not self._cool("plug", 60):
                        self.on_event("power", "诶，电源拔了？省着点用哦。",
                                      "Hey, you unplugged it? Use it sparingly.", "neutral")
            self._plugged = plugged
        except Exception:
            pass

    def _check_devices(self):
        try:
            import wmi
            c = getattr(self, "_wmi", None)
            if c is None:
                c = self._wmi = wmi.WMI()
            noise = ("root hub", "host controller", "composite", "usb xhci",
                     "usb root", "monitor", "audio device", "sm bus", "pci")
            cur = set()
            for dev in c.Win32_PnPEntity(ConfigManagerErrorCode=0):
                name = (dev.Name or "").lower()
                if any(n in name for n in noise):
                    continue
                did = dev.DeviceID or ""
                if did:
                    cur.add(did)
            new = cur - self._devices
            if new and self._devices:
                if not self._cool("dev", 120):
                    self.on_event("device", "有新设备连上来了？让我猜猜是U盘还是手机。",
                                  "A new device connected? Let me guess — a USB drive or a phone?", "happy")
            self._devices = cur
        except Exception:
            pass

    def _check_procs(self):
        """进程退出事件（WMI 事件订阅，阻塞式）"""
        try:
            import wmi
            c = getattr(self, "_wmi", None)
            if c is None:
                c = self._wmi = wmi.WMI()
            stop_w = c.watch_for(notification_type="Operation",
                                 wmi_class="Win32_ProcessStopTrace", delay_secs=1)
            start_w = c.watch_for(notification_type="Operation",
                                  wmi_class="Win32_ProcessStartTrace", delay_secs=1)
            while True:
                try:
                    evt = stop_w(timeout_ms=500)
                    if evt and getattr(evt, "ProcessName", None):
                        self._on_stop(evt.ProcessName.lower())
                except Exception:
                    pass
                try:
                    evt2 = start_w(timeout_ms=500)
                    if evt2 and getattr(evt2, "ProcessName", None):
                        self._procs[evt2.ProcessName.lower()] = time.time()
                except Exception:
                    pass
                self._check_downloads()
                self._check_power()
                self._check_devices()
                time.sleep(3)
        except Exception:
            # WMI 不可用时退化为轮询模式
            while True:
                self._check_downloads()
                self._check_power()
                self._check_devices()
                time.sleep(5)

    def _on_stop(self, exe):
        """进程退出：游戏类触发台词"""
        import gamewatch
        if exe not in gamewatch.GAME_PROFILES:
            return
        if self._cool("game_exit", 90):
            return
        start = self._procs.pop(exe, None)
        mins = int((time.time() - start) / 60) if start else 0
        mins = max(1, mins)
        gamewatch.record_session(exe, mins)
        zh, en, emo = gamewatch.game_line(exe, mins)
        self.on_event("game", zh, en, emo)

    def run(self):
        # 先做一轮下载/电源/设备基线
        self._check_downloads()
        self._check_power()
        self._check_devices()
        self._check_procs()
