# -*- coding: utf-8 -*-
"""音乐人格：识别当前播放（SMTC）+ 播放历史 + 时间/情绪化回应"""
import asyncio
import json
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE, "play_history.json")

# 只对音乐类 App 回应（SMTC source 里包含这些关键字）
MUSIC_APPS = ("qqmusic", "cloudmusic", "netease", "spotify", "music", "wmp", "foobar", "potplayer")


def _now_playing_smtc():
    """通过 Windows SMTC 获取当前媒体（title, artist, appid）"""
    try:
        from winsdk.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as Mgr)

        async def _get():
            mgr = await Mgr.request_async()
            session = mgr.get_current_session()
            if not session:
                return None
            props = await session.try_get_media_properties_async()
            appid = (getattr(session, "source_app_user_model_id", "") or "").lower()
            return (props.title or "", props.artist or "", appid)

        return asyncio.run(_get())
    except Exception:
        return None


def _now_playing_window():
    """兜底：读音乐播放器窗口标题（歌名 - 歌手）"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        buf = ctypes.create_unicode_buffer(512)
        hwnd = user32.GetForegroundWindow()
        user32.GetWindowTextW(hwnd, buf, 512)
        t = buf.value
        for kw in ("QQ音乐", "网易云音乐", "CloudMusic"):
            if kw in t:
                title = t.replace(kw, "").strip(" -—|")
                return title, "", kw.lower()
    except Exception:
        pass
    return None


def now_playing():
    """返回 (title, artist, appid) 或 None"""
    try:
        r = _now_playing_smtc()
        if r and r[0]:
            return r
    except Exception:
        pass
    return _now_playing_window()


def is_music_app(appid):
    return any(k in (appid or "").lower() for k in MUSIC_APPS)


def load_history():
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"plays": []}


def save_history(h):
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def record_play(title, artist):
    h = load_history()
    h.setdefault("plays", []).append({
        "title": title[:60], "artist": (artist or "")[:40],
        "time": time.strftime("%Y-%m-%d %H:%M"),
    })
    if len(h["plays"]) > 300:
        h["plays"] = h["plays"][-300:]
    save_history(h)
    # 返回之前是否听过（除本次外）
    prev = [p for p in h["plays"][:-1]
            if p["title"].lower() == title.lower()]
    return len(prev)


def comment_line(title, artist, hour, emotion, repeat):
    """生成个性化回应 (zh, en, emotion)"""
    title = title.strip() or "这首歌"
    artist = artist.strip()
    who = "《%s》" % title
    if emotion == "sad":
        zh = ("你放的%s……心情不好吗？那就让音乐陪着你，我也在。" % who)
        en = ("%s... Feeling down? Let the music stay with you — and so will I." % title)
        return zh, en, "sad"
    if emotion == "angry":
        zh = ("听着%s，火气还没消？来，我陪你骂两句都行。" % who)
        en = ("Listening to %s, still mad? Come on, I will rant with you." % title)
        return zh, en, "neutral"
    if repeat > 0:
        zh = ("这首%s你之前也听过呢……是对你来说特别的一首吗？" % who)
        en = ("You have listened to %s before... Is it special to you?" % title)
        return zh, en, "neutral"
    if 22 <= hour or hour < 6:
        zh = ("晚上听%s……想安静一会儿吗？我陪你。" % who)
        en = ("Listening to %s at night... want some quiet time? I will be here." % title)
        return zh, en, "neutral"
    if hour < 11:
        zh = ("早上就听%s，今天心情不错嘛。" % who)
        en = ("Starting the morning with %s — in a good mood today, huh?" % title)
        return zh, en, "happy"
    zh = ("《%s》%s……你听歌的品味不错嘛。" % (title, (" - " + artist) if artist else ""))
    en = ("%s%s... You have good taste in music." % (title, (" by " + artist) if artist else ""))
    return zh, en, "happy"


class MusicWatcher:
    """后台轮询当前播放，检测到新歌就回调"""

    def __init__(self, on_event):
        self.on_event = on_event  # on_event("music", zh, en, emotion)
        self._last_title = None
        self._last_time = 0.0

    def run(self):
        while True:
            try:
                np = now_playing()
                if np and np[0] and is_music_app(np[2]):
                    title = np[0].strip()
                    if title and title != self._last_title:
                        self._last_title = title
                        self._last_time = time.time()
                        repeat = record_play(title, np[1])
                        h = time.localtime().tm_hour
                        zh, en, emo = comment_line(title, np[1], h, "neutral", repeat)
                        self.on_event("music", zh, en, emo)
                    elif title == self._last_title and self._last_time:
                        # 同一首歌持续播放中，不重复评论
                        pass
                else:
                    self._last_title = None
            except Exception:
                pass
            time.sleep(10)
