# -*- coding: utf-8 -*-
"""系统状态感知：CPU/内存/磁盘/电量/GPU/网络 + 异常提醒"""
import os
import re
import subprocess
import time


def _gpu_info():
    """nvidia-smi 读 GPU 温度/占用/显存，失败返回 None"""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, creationflags=0x08000000)
        line = r.stdout.strip().splitlines()
        if not line:
            return None
        t, u, mu, mt = [x.strip() for x in line[0].split(",")]
        return {"temp": int(t), "util": int(u),
                "mem_used": int(mu), "mem_total": int(mt)}
    except Exception:
        return None


def sample():
    """采集一次系统状态，返回 dict"""
    out = {}
    try:
        import psutil
        out["cpu"] = psutil.cpu_percent(interval=0.4)
        out["mem"] = psutil.virtual_memory().percent
        try:
            out["disk"] = psutil.disk_usage("C:\\").percent
        except Exception:
            out["disk"] = None
        try:
            b = psutil.sensors_battery()
            if b:
                out["batt"] = round(b.percent)
                out["plugged"] = bool(b.power_plugged)
        except Exception:
            pass
    except Exception:
        pass
    g = _gpu_info()
    if g:
        out["gpu_temp"] = g["temp"]
        out["gpu_util"] = g["util"]
        out["gpu_mem"] = g["mem_used"]
        out["gpu_mem_total"] = g["mem_total"]
    return out


_NET_LAST = {"t": 0.0, "bytes": 0}


def net_speed_kbs():
    """网络实时速率 KB/s（两次调用间差值）"""
    try:
        import psutil
        c = psutil.net_io_counters()
        now = time.time()
        if _NET_LAST["t"] and now - _NET_LAST["t"] > 0:
            d = (c.bytes_sent + c.bytes_recv - _NET_LAST["bytes"]) / (now - _NET_LAST["t"]) / 1024
            _NET_LAST["t"], _NET_LAST["bytes"] = now, c.bytes_sent + c.bytes_recv
            return max(0, round(d))
        _NET_LAST["t"], _NET_LAST["bytes"] = now, c.bytes_sent + c.bytes_recv
    except Exception:
        pass
    return 0


def summary_text():
    """状态查询用的一句话播报"""
    s = sample()
    parts = []
    if "cpu" in s:
        parts.append("CPU %d%%" % s["cpu"])
    if "mem" in s:
        parts.append("内存 %d%%" % s["mem"])
    if s.get("disk") is not None:
        parts.append("C盘 %d%%" % s["disk"])
    if "batt" in s:
        parts.append("电量 %d%%%s" % (s["batt"], "（充电中）" if s.get("plugged") else ""))
    if "gpu_temp" in s:
        parts.append("显卡 %d度/%d%%" % (s["gpu_temp"], s["gpu_util"]))
    net = net_speed_kbs()
    if net:
        parts.append("网络 %.0fKB/s" % net)
    return "，".join(parts) if parts else "状态读取失败"


def check_alerts(sample_series, last_successive_cpu):
    """根据连续采样判断异常，返回提醒文案列表"""
    alerts = []
    s = sample_series[-1] if sample_series else {}
    # CPU 持续高负载：最近 3 次都 ≥ 85%
    if len(sample_series) >= 3:
        recent = [x.get("cpu", 0) for x in sample_series[-3:]]
        if all(c >= 85 for c in recent):
            alerts.append("CPU 持续高负载（%d%%），电脑是不是在跑什么大东西？" % int(recent[-1]))
    if s.get("mem", 0) >= 90:
        alerts.append("内存快满了（%d%%），要不我帮你看看是哪个程序在吃内存？" % int(s["mem"]))
    if s.get("disk") is not None and s["disk"] >= 95:
        alerts.append("C盘快满了（%d%%），该清理啦。" % int(s["disk"]))
    if "batt" in s and s["batt"] <= 20 and not s.get("plugged"):
        alerts.append("电量只剩 %d%% 了，记得插上电源。" % s["batt"])
    if s.get("gpu_temp", 0) >= 90:
        alerts.append("显卡温度 %d 度，有点烫，注意散热。" % s["gpu_temp"])
    return alerts
