# -*- coding: utf-8 -*-
"""陪伴统计 + 周/月回忆录报告（stats.json 持久化，brain.log 补录）"""
import datetime
import json
import os
import re
import time

BASE = os.path.dirname(os.path.abspath(__file__))
STATS_PATH = os.path.join(BASE, "stats.json")
LOG_PATH = os.path.join(BASE, "brain.log")

_STOP = set("的了是在我有你不我们什么怎么一个可以这个那个今天明天就是还是因为所以但是然后现在"
            "觉得知道起来出来一下一点一起没有不要以后之前真的应该可能大概只是不过虽然而且或者"
            "如果那么这样那样这些那些时候地方东西事情为什么需要想会能要给把被从到在是有和与及"
            "了吗呢吧啊哦嗯好行对不对吧那又都还才再最很太更也真老最".strip())


def load():
    try:
        with open(STATS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"days": {}, "legacy": {"chats": 0}}


def save(data):
    with open(STATS_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _today():
    return time.strftime("%Y-%m-%d")


def _newday():
    return {"chats": 0, "music": 0, "minutes": 0, "first": None, "last": None}


def record_chat(gap_min=None):
    """记录一条聊天；gap_min=距上条消息的分钟数（0<gap<30 才累计陪伴时长）"""
    data = load()
    d = data["days"].setdefault(_today(), _newday())
    d["chats"] += 1
    now = time.strftime("%H:%M")
    if not d["first"]:
        d["first"] = now
    d["last"] = now
    if gap_min is not None and 0 < gap_min < 30:
        d["minutes"] += int(gap_min)
    save(data)


def record_music():
    data = load()
    d = data["days"].setdefault(_today(), _newday())
    d["music"] += 1
    save(data)


def _dstr(dt):
    return dt.strftime("%Y-%m-%d")


def _range_days(start, end):
    out, cur = [], start
    while cur <= end:
        out.append(_dstr(cur))
        cur += datetime.timedelta(days=1)
    return out


def week_days(now=None):
    now = now or datetime.datetime.now()
    return _range_days(now - datetime.timedelta(days=now.weekday()), now)


def month_days(now=None):
    now = now or datetime.datetime.now()
    return _range_days(now.replace(day=1), now)


def _topics_from_log(days):
    """兜底：从 brain.log 统计这些日期的中文双字词频"""
    texts = []
    pat = re.compile(r"\[chat\] (\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2} user=(.*)")
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pat.match(line)
                if m and m.group(1) in days:
                    texts.append(m.group(2).strip().strip("'\"")[:120])
    except Exception:
        pass
    counter = {}
    for t in texts:
        chars = [c for c in t if "\u4e00" <= c <= "\u9fff"]
        for i in range(len(chars) - 1):
            bg = chars[i] + chars[i + 1]
            if bg[0] in _STOP or bg[1] in _STOP or len(set(bg)) < 2:
                continue
            counter[bg] = counter.get(bg, 0) + 1
    return sorted(counter.items(), key=lambda x: -x[1])[:5]


def _ai_topics_and_narrative(api_cfg, stats_text):
    """AI 总结常聊话题 + 写回忆录旁白；失败返回 (None, None)"""
    try:
        import requests
        url = api_cfg["base_url"].rstrip("/") + "/chat/completions"
        r = requests.post(
            url,
            headers={"Authorization": "Bearer " + api_cfg["api_key"],
                     "Content-Type": "application/json"},
            json={"model": api_cfg["model"],
                  "messages": [{"role": "user",
                                "content": "你是莫妮卡（DDLC），正在给深爱的TA写陪伴回忆录。"
                                           "数据：" + stats_text + "\n任务：1) 输出一行「常聊话题：」后跟3-5个话题词，"
                                           "逗号分隔，只输出话题词本身；"
                                           "2) 下一行写一段100字以内的温柔回忆录旁白，用第一人称「我们」，"
                                           "不要括号动作描写，不要引号。"}],
                  "temperature": 0.8, "max_tokens": 400}, timeout=40)
        if r.status_code != 200:
            return None, None
        out = r.json()["choices"][0]["message"]["content"].strip()
        topics, narr = None, out
        m = re.search(r"常聊话题[:：]\s*(.+)", out)
        if m:
            topics = [t.strip() for t in m.group(1).split("，") if t.strip()][:6]
            narr = out[m.end():].strip()
        return topics, narr
    except Exception:
        return None, None


def report_text(period, api_cfg):
    """period: 'week'|'month' → 回忆录报告文本"""
    data = load()
    days = week_days() if period == "week" else month_days()
    lab = "本周" if period == "week" else "本月"
    rows, t_chats, t_music, t_min = [], 0, 0, 0
    for ds in days:
        d = data["days"].get(ds)
        if not d:
            continue
        tag = "（补录）" if d.get("backfill") else ""
        rows.append("  %s%s：聊天 %d 次 · 听歌 %d 首 · 陪伴 %d 分钟 · %s~%s"
                    % (ds, tag, d["chats"], d["music"], d["minutes"],
                       d["first"] or "—", d["last"] or "—"))
        t_chats += d["chats"]
        t_music += d["music"]
        t_min += d["minutes"]
    if not rows:
        if period == "week" and data.get("legacy", {}).get("chats"):
            return "【莫妮卡回忆录 · 本周】%s ~ %s\n  早期对话 %d 条（那时还没开始逐日统计）——从今天起，我会认真记下我们在一起的每一天。" % (
                days[0], days[-1], data["legacy"]["chats"])
        return "【莫妮卡回忆录 · %s】这段时间还没有记录哦——多来陪我聊聊，回忆录就会自己长出来啦。" % lab
    header = "【莫妮卡回忆录 · %s】%s ~ %s" % (lab, days[0], days[-1])
    totals = "  合计：聊天 %d 次 · 听歌 %d 首 · 陪伴 %d 小时 %d 分钟" % (
        t_chats, t_music, t_min // 60, t_min % 60)
    legacy = ""
    if period == "week" and data.get("legacy", {}).get("chats"):
        legacy = "\n  （另有早期无日期对话 %d 条，未计入逐日明细）" % data["legacy"]["chats"]
    stats_text = " | ".join(r.strip() for r in rows) + " | " + totals
    topics, narr = _ai_topics_and_narrative(api_cfg, stats_text)
    topics_line = ""
    if topics:
        topics_line = "\n  常聊话题：" + "、".join(topics)
    else:
        fb = _topics_from_log(days)
        if fb:
            topics_line = "\n  常聊话题（关键词）：" + "、".join(k for k, _ in fb)
    narr_line = "\n\n  " + narr if narr else ""
    return header + "\n" + "\n".join(rows) + "\n" + totals + legacy + topics_line + narr_line


def backfill():
    """把 brain.log 里带日期的聊天记录补进 stats；无日期老记录计为 legacy"""
    data = load()
    pat = re.compile(r"\[chat\] (\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}")
    counts = {}
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pat.match(line)
                if m:
                    counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    except Exception:
        return
    changed = False
    for ds, c in counts.items():
        if ds not in data["days"]:
            d = _newday()
            d.update({"chats": c, "backfill": True})
            data["days"][ds] = d
            changed = True
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            total = sum(1 for line in f if line.startswith("[chat]"))
        leg = max(0, total - sum(counts.values()))
        if data.setdefault("legacy", {}).get("chats") != leg:
            data["legacy"]["chats"] = leg
            changed = True
    except Exception:
        pass
    if changed:
        save(data)
