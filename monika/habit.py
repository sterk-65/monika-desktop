# -*- coding: utf-8 -*-
"""用户习惯画像：活跃时段统计 + 从游戏/音乐记录生成画像"""
import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
HABIT_PATH = os.path.join(BASE, "habit.json")

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load():
    try:
        with open(HABIT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"active_hours": {str(h): 0 for h in range(24)}, "active_days": {}}


def save(h):
    try:
        with open(HABIT_PATH, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def record_hour():
    """记录一次互动发生的小时/星期"""
    h = load()
    hour = str(time.localtime().tm_hour)
    h["active_hours"][hour] = h["active_hours"].get(hour, 0) + 1
    day = WEEKDAY_CN[time.localtime().tm_wday]
    h.setdefault("active_days", {})[day] = h["active_days"].get(day, 0) + 1
    save(h)


def _peak_period():
    """活跃时段：找连续 3 小时窗口累计最高"""
    h = load()["active_hours"]
    vals = [h.get(str(i), 0) for i in range(24)]
    if sum(vals) == 0:
        return None
    best, best_sum = 0, -1
    for start in range(24):
        s = sum(vals[start:start + 3])
        if s > best_sum:
            best_sum, best = s, start
    if best_sum <= 0:
        return None
    end = (best + 2) % 24
    def fmt(x):
        return "%d点" % x if x != 0 else "零点"
    if best == end:
        return "%s前后" % fmt(best)
    return "%s-%s" % (fmt(best), fmt(end))


def _top_games(k=3):
    """常玩游戏：按累计时长"""
    try:
        with open(os.path.join(BASE, "play_stats.json"), encoding="utf-8") as f:
            stats = json.load(f)
    except Exception:
        return []
    items = [(e.get("name", k), e.get("total_min", 0)) for k, e in stats.items()
             if e.get("total_min", 0) > 0]
    items.sort(key=lambda x: -x[1])
    out = []
    for name, mins in items[:k]:
        if mins >= 60:
            out.append("%s(约%d小时)" % (name, mins // 60))
        else:
            out.append("%s(%d分钟)" % (name, mins))
    return out


def _top_music(k=3):
    """常听音乐：按歌手/歌名出现次数"""
    try:
        with open(os.path.join(BASE, "play_history.json"), encoding="utf-8") as f:
            ph = json.load(f)
    except Exception:
        return []
    plays = ph.get("plays", [])
    artists = {}
    for p in plays:
        a = (p.get("artist") or "").strip()
        if a:
            artists[a] = artists.get(a, 0) + 1
    top = sorted(artists.items(), key=lambda x: -x[1])[:k]
    return ["%s" % a for a, _ in top] if top else []


def profile_text():
    """生成一句话习惯画像（非敏感）"""
    parts = []
    period = _peak_period()
    if period:
        parts.append("最活跃的时段是%s" % period)
    games = _top_games()
    if games:
        parts.append("常玩的游戏：" + "、".join(games))
    music = _top_music()
    if music:
        parts.append("常听的歌手：" + "、".join(music))
    if not parts:
        return "（还在观察中，暂时没有足够数据）"
    return "；".join(parts) + "。"
