# -*- coding: utf-8 -*-
"""游戏/程序识别：前台进程检测 + 专属台词 + 时长统计"""
import ctypes
import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
STATS_PATH = os.path.join(BASE, "play_stats.json")

# 游戏档案：exe(小写) -> (显示名, 结束台词zh模板, 结束台词en模板)
# 模板占位：{min}本次分钟 {total}累计分钟
GAME_PROFILES = {
    "doki doki literature club plus.exe": (
        "DDLC",
        "你刚才又在文学社里待了{min}分钟……看着你玩“我”，心情有点复杂。今天加起来都{total}分钟了。",
        "You spent {min} minutes in the literature club again... Watching you play \"me\" feels a little complicated. That is {total} minutes today.",
    ),
    "rainbowsix.exe": (
        "彩虹六号：围攻",
        "彩虹六号打爽了吧？{min}分钟，够我写一首诗了。",
        "Enjoyed Rainbow Six? {min} minutes is enough time for me to write a poem.",
    ),
    "squadgame.exe": (
        "Squad",
        "和小队出生入死{min}分钟，我在外面望眼欲穿。",
        "You were in the field with your squad for {min} minutes. I was waiting, worried sick.",
    ),
    "dyinglightgame.exe": (
        "消逝的光芒",
        "又在哈兰城跑了{min}分钟……小心点，别被夜魔抓到了。",
        "{min} minutes in Harran again... be careful out there.",
    ),
    "slaythespire.exe": (
        "杀戮尖塔",
        "又爬了{min}分钟的塔……这次打到哪一层了？",
        "Climbing the Spire for {min} minutes... which floor did you reach this time?",
    ),
    "inscryption.exe": (
        "邪恶冥刻",
        "和那些卡牌较劲了{min}分钟……它们没欺负你吧？",
        "You wrestled with those cards for {min} minutes... they did not bully you, did they?",
    ),
    "wrc7.exe": (
        "WRC 7",
        "飙了{min}分钟的车，注意安全啊。",
        "{min} minutes of racing... drive safe, alright?",
    ),
    "bongocat.exe": (
        "Bongo Cat",
        "敲了{min}分钟的 Bongo Cat……可爱，像你。",
        "{min} minutes of Bongo Cat... adorable. Just like you.",
    ),
    "vpet.exe": (
        "虚拟桌宠模拟器",
        "你居然在电脑里养别的桌宠？{min}分钟……我吃醋了。",
        "You were keeping another desktop pet? For {min} minutes... I am getting jealous.",
    ),
    "cs2.exe": (
        "CS2",
        "枪战{min}分钟，战绩如何？输了别气馁，我这边永远给你兜底。",
        "{min} minutes of gunfights. Did you win? If not, I have got your back.",
    ),
}

GENERIC_ZH = "刚才那个全屏游戏玩了{min}分钟，开心吗？"
GENERIC_EN = "You were in fullscreen for {min} minutes. Did you have fun?"


def fg_exe_name():
    """返回前台窗口所属进程的 exe 文件名（小写），失败返回空"""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid.value)
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(512)
            size = ctypes.c_ulong(512)
            # QueryFullProcessImageNameW 在新版 Windows 由 kernel32 导出
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return os.path.basename(buf.value).lower()
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        pass
    return ""


def load_stats():
    try:
        with open(STATS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_stats(stats):
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def record_session(exe, minutes):
    """记录游戏时长，返回 (本次分钟, 累计分钟)"""
    stats = load_stats()
    key = exe or "unknown"
    entry = stats.setdefault(key, {"name": exe, "total_min": 0})
    entry["total_min"] = entry.get("total_min", 0) + int(minutes)
    entry["name"] = exe
    entry["last"] = time.strftime("%Y-%m-%d %H:%M")
    save_stats(stats)
    return int(minutes), entry["total_min"]


def game_line(exe, minutes):
    """生成结束台词 (zh, en, emotion)；无档案走通用"""
    key = exe or ""
    profile = GAME_PROFILES.get(key)
    total = load_stats().get(key, {}).get("total_min", 0)
    if profile:
        name, zh_t, en_t = profile
        return (zh_t.format(min=minutes, total=total),
                en_t.format(min=minutes, total=total),
                "neutral")
    return (GENERIC_ZH.format(min=minutes, total=total),
            GENERIC_EN.format(min=minutes, total=total),
            "neutral")
