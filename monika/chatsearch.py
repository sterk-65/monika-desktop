# -*- coding: utf-8 -*-
"""对话搜索：按关键词定位历史聊天（brain.log + memory.json）"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(BASE, "memory.json")
LOG_PATH = os.path.join(BASE, "brain.log")


def _parse_log():
    """解析 brain.log → [{time, role, text}]（兼容带日期/不带日期两种格式）"""
    entries = []
    pat_new = re.compile(r"\[(chat|reply)\] (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?:user=)?(.*)")
    pat_old = re.compile(r"\[(chat|reply)\] (\d{2}:\d{2}:\d{2}) (?:user=)?(.*)")
    try:
        with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pat_new.match(line) or pat_old.match(line)
                if not m:
                    continue
                kind, ts, rest = m.group(1), m.group(2), m.group(3)
                text = re.sub(r"'\s*peek=\S+$", "", rest.strip()).strip("'\"")
                entries.append({"time": ts,
                                "role": "user" if kind == "chat" else "assistant",
                                "text": text})
    except Exception:
        pass
    return entries


def search(keyword, limit=30):
    """返回 [{time, role, text, ctx}]，ctx 带下一条回复作为上下文"""
    kw = (keyword or "").lower().strip()
    if not kw:
        return []
    results = []
    entries = _parse_log()
    for i, e in enumerate(entries):
        if kw in e["text"].lower():
            ctx = e["text"]
            if e["role"] == "user" and i + 1 < len(entries):
                ctx += " || " + entries[i + 1]["text"]
            results.append({"time": e["time"], "role": e["role"],
                            "text": e["text"], "ctx": ctx[:300]})
    try:
        with open(MEMORY_PATH, encoding="utf-8") as f:
            mem = json.load(f)
        hist = mem.get("history", [])
        for i, item in enumerate(hist):
            role, text = item[0], item[1]
            if kw in text.lower():
                ctx = text
                if role == "user" and i + 1 < len(hist):
                    ctx += " || " + hist[i + 1][1]
                results.append({"time": "近期", "role": role,
                                "text": text, "ctx": ctx[:300]})
    except Exception:
        pass
    # 去重（log 与 memory 可能重叠），log 优先
    seen, out = set(), []
    for r in results:
        k = (r["role"], r["text"][:50])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out[:limit]


def format_results(results):
    if not results:
        return "没有找到相关的聊天记录"
    lines = []
    for r in results[:15]:
        who = "我" if r["role"] == "user" else "莫妮卡"
        lines.append("[%s] %s：%s" % (r["time"], who, r["text"][:60]))
    return "找到这些聊天记录：\n" + "\n".join(lines)
