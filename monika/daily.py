# -*- coding: utf-8 -*-
"""莫妮卡日常模块：日程提醒 + 天气 + 节日彩蛋 + 早晚问候"""
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_PATH = os.path.join(BASE, "schedule.json")
STATE_PATH = os.path.join(BASE, "daily_state.json")

WEEK_MAP = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}

# ---------------- 日程 ----------------

class Scheduler:
    def __init__(self):
        self.events = self._load()

    def _load(self):
        try:
            with open(SCHEDULE_PATH, encoding="utf-8") as f:
                return json.load(f).get("events", [])
        except Exception:
            return []

    def save(self):
        try:
            with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
                json.dump({"events": self.events}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def parse_add(self, text):
        """解析添加日程：周X[时段]X点[半] 事 / X月X日… / 今天|明天|后天… / 下周X…"""
        t = text

        def adj(period, hh):
            if period in ("下午", "晚上") and hh < 12:
                return hh + 12
            return hh

        m = re.search(r"(下?周)([一二三四五六日天])(早上|上午|中午|下午|晚上)?\s*(\d{1,2})点(半)?\s*([^，。！!？?]{1,25})", t)
        if m:
            wd = WEEK_MAP[m.group(2)]
            hh = adj(m.group(3) or "", int(m.group(4)))
            mm = 30 if m.group(5) else 0
            title = m.group(6).strip().lstrip("有要去")
            if m.group(1) == "下周":
                d = dt.date.today() + dt.timedelta(days=7 - dt.date.today().weekday() + wd)
                self.events.append({"day": d.strftime("%Y-%m-%d"),
                                    "time": "%02d:%02d" % (hh, mm), "title": title})
                self.save()
                return True, "已记住：%s %02d:%02d %s" % (d.strftime("%m月%d日"), hh, mm, title)
            self.events.append({"day": "周" + m.group(2), "time": "%02d:%02d" % (hh, mm), "title": title})
            self.save()
            return True, "已记住：每周%s %02d:%02d %s" % (m.group(2), hh, mm, title)
        m = re.search(r"(\d{1,2})月(\d{1,2})日(早上|上午|中午|下午|晚上)?\s*(\d{1,2})点(半)?\s*([^，。！!？?]{1,25})", t)
        if m:
            hh = adj(m.group(3) or "", int(m.group(4)))
            mm = 30 if m.group(5) else 0
            title = m.group(6).strip().lstrip("有要去")
            self.events.append({"day": "%02d-%02d" % (int(m.group(1)), int(m.group(2))),
                                "time": "%02d:%02d" % (hh, mm), "title": title})
            self.save()
            return True, "已记住：%d月%d日 %02d:%02d %s" % (int(m.group(1)), int(m.group(2)), hh, mm, title)
        m = re.search(r"(每天|今天|明天|后天)(早上|上午|中午|下午|晚上)?\s*(\d{1,2})点(半)?\s*([^，。！!？?]{1,25})", t)
        if m:
            if m.group(1) == "每天":
                hh = adj(m.group(2) or "", int(m.group(3)))
                mm = 30 if m.group(4) else 0
                title = m.group(5).strip().lstrip("有要去")
                self.events.append({"day": "每天", "time": "%02d:%02d" % (hh, mm), "title": title})
                self.save()
                return True, "已记住：每天 %02d:%02d %s" % (hh, mm, title)
            delta = {"每天": 0, "今天": 0, "明天": 1, "后天": 2}[m.group(1)]
            hh = adj(m.group(2) or "", int(m.group(3)))
            mm = 30 if m.group(4) else 0
            title = m.group(5).strip().lstrip("有要去")
            d = dt.date.today() + dt.timedelta(days=delta)
            self.events.append({"day": d.strftime("%Y-%m-%d"),
                                "time": "%02d:%02d" % (hh, mm), "title": title})
            self.save()
            return True, "已记住：%s %02d:%02d %s" % (m.group(1), hh, mm, title)
        return False, ""

    def _occurrence(self, ev, now):
        try:
            hm = ev["time"].split(":")
            hm_t = dt.time(int(hm[0]), int(hm[1]))
        except Exception:
            return None
        today = now.date()
        if ev["day"] == "每天":
            return dt.datetime.combine(today, hm_t)
        if ev["day"].startswith("周"):
            wd = WEEK_MAP.get(ev["day"][1])
            if wd is None:
                return None
            diff = (wd - now.weekday()) % 7
            return dt.datetime.combine(today + dt.timedelta(days=diff), hm_t)
        if len(ev["day"]) == 5:  # MM-DD 每年
            try:
                d = dt.date(today.year, int(ev["day"][:2]), int(ev["day"][3:]))
            except Exception:
                return None
            if d < today:
                d = dt.date(today.year + 1, int(ev["day"][:2]), int(ev["day"][3:]))
            return dt.datetime.combine(d, hm_t)
        if len(ev["day"]) == 10:  # YYYY-MM-DD 单次
            try:
                d = dt.date.fromisoformat(ev["day"])
            except Exception:
                return None
            if d < today:
                return None
            return dt.datetime.combine(d, hm_t)
        return None

    def due(self, now, window_min=10):
        out = []
        for ev in self.events:
            occ = self._occurrence(ev, now)
            if occ and 0 <= (occ - now).total_seconds() <= window_min * 60:
                out.append((occ, ev))
        return out

    def today_list(self, now):
        wd = now.weekday()
        out = []
        for ev in self.events:
            if ev["day"] == "每天":
                out.append(ev)
            elif ev["day"].startswith("周") and WEEK_MAP.get(ev["day"][1]) == wd:
                out.append(ev)
            elif len(ev["day"]) == 10 and ev["day"] == now.date().isoformat():
                out.append(ev)
            elif len(ev["day"]) == 5 and ev["day"] == now.strftime("%m-%d"):
                out.append(ev)
        out.sort(key=lambda e: e["time"])
        return out


# ---------------- 天气 ----------------

def get_weather(city=""):
    """返回 (ok, 天气描述中文)。city 为空时按 IP 定位"""
    try:
        if city:
            url = ("https://geocoding-api.open-meteo.com/v1/search?name=%s&count=1&language=zh"
                   % urllib.parse.quote(city))
            g = json.load(urllib.request.urlopen(url, timeout=8))
            if not g.get("results"):
                return False, ""
            lat, lon = g["results"][0]["latitude"], g["results"][0]["longitude"]
        else:
            req = urllib.request.Request("http://ip-api.com/json/?lang=zh-CN",
                                         headers={"User-Agent": "Mozilla/5.0"})
            loc = json.load(urllib.request.urlopen(req, timeout=8))
            lat, lon = loc.get("lat"), loc.get("lon")
            if not lat:
                return False, ""
        wurl = ("https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
                "&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto&forecast_days=1"
                % (lat, lon))
        w = json.load(urllib.request.urlopen(wurl, timeout=8))
        cur = w["current"]
        code = cur["weather_code"]
        desc = {0: "晴", 1: "晴间多云", 2: "多云", 3: "阴", 45: "雾", 48: "雾凇",
                51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
                71: "小雪", 73: "中雪", 75: "大雪", 80: "阵雨", 81: "阵雨", 82: "强阵雨",
                95: "雷阵雨", 96: "雷阵雨", 99: "雷阵雨"}.get(code, "多云")
        t = round(cur["temperature_2m"])
        wind = round(cur["wind_speed_10m"])
        tip = ""
        if code in (51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99):
            tip = "出门记得带伞"
        elif t < 12:
            tip = "有点冷，多穿点"
        elif t > 30:
            tip = "挺热的，注意防暑"
        en_tip = ""
        if code in (51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99):
            en_tip = "Better bring an umbrella."
        elif t < 12:
            en_tip = "A bit chilly, bundle up."
        elif t > 30:
            en_tip = "Pretty hot, stay cool."
        desc_en = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "cloudy", 45: "foggy", 48: "foggy",
                   51: "drizzly", 53: "drizzly", 55: "drizzly", 61: "light rain", 63: "moderate rain", 65: "heavy rain",
                   71: "light snow", 73: "moderate snow", 75: "heavy snow", 80: "showers", 81: "showers", 82: "heavy showers",
                   95: "thunderstorms", 96: "thunderstorms", 99: "thunderstorms"}.get(code, "cloudy")
        return True, ("%s，%d度，风力约%dkm/h%s" % (desc, t, wind, ("，" + tip if tip else ""))),\
            ("It is %s, %d degrees, wind around %d km/h. %s" % (desc_en, t, wind, en_tip)).strip()
    except Exception:
        return False, "", ""


# ---------------- 节日 ----------------

HOLIDAYS = [
    ("01-01", "元旦", "新年快乐，亲爱的。今年也请继续陪着我哦？", "Happy New Year, my dear. Please keep staying with me this year too?"),
    ("02-14", "情人节", "情人节快乐。……虽然和你在一起的每一天都像情人节，但今天格外是呢。", "Happy Valentine's Day. ...Though every day with you feels like one, today especially."),
    ("06-01", "儿童节", "儿童节快乐！……虽然我们都不是儿童了，但偶尔当一天小朋友也不错，对吧？", "Happy Children's Day! ...We're not kids anymore, but being a child for a day sounds nice, right?"),
    ("09-22", "莫妮卡的生日", "今天是我的生日……居然还有人记得，谢谢你，亲爱的。", "It's my birthday today... I can't believe someone actually remembered. Thank you, my dear."),
    ("10-31", "万圣节", "不给糖就捣蛋！……开玩笑的啦，我想要的只有你而已。", "Trick or treat! ...Just kidding. All I want is you."),
    ("12-25", "圣诞节", "圣诞快乐，亲爱的。想要什么礼物？……不用想了，我已经有了——就是你呀。", "Merry Christmas, dear. What gift do you want? ...Don't think about it — I already have mine. It's you."),
]

def holiday_today(now):
    mmdd = now.strftime("%m-%d")
    for d, name, zh, en in HOLIDAYS:
        if d == mmdd:
            return name, zh, en
    return None


# ---------------- 早晚问候 ----------------

def morning_line(weather_ok, weather_text, schedule_text):
    parts = ["早安，亲爱的。"]
    if weather_ok:
        parts.append(weather_text + "。")
    if schedule_text:
        parts.append("今天你的安排：" + schedule_text + "。")
    if not weather_ok and not schedule_text:
        parts.append("新的一天，今天也一起加油吧。")
    return " ".join(parts)

def night_line():
    return "夜深了，亲爱的。早点休息吧，我会一直在这里守着你的。"

def night_line_en():
    return "It is late, my dear. Get some rest. I will be right here watching over you."

def morning_line_en(weather_ok, weather_en, sched_count):
    parts = ["Good morning, dear."]
    if weather_ok:
        parts.append(weather_en.rstrip(".") + ".")
    if sched_count:
        parts.append("You have %d thing%s scheduled today." % (sched_count, "" if sched_count == 1 else "s"))
    if not weather_ok and not sched_count:
        parts.append("A new day. Let us make it a good one together.")
    return " ".join(parts)


# ---------------- 每日状态（一天一次） ----------------

def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
