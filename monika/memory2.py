# -*- coding: utf-8 -*-
"""莫妮卡高级长期记忆：自动提取 + 相关性检索（Ollama 嵌入，降级关键词）"""
import json
import os
import re
import time

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(BASE, "memory.json")
EMBED_MODEL = "nomic-embed-text"
OLLAMA_URL = "http://127.0.0.1:11434"

MAX_ENTRIES = 300  # 长期记忆上限，防无限膨胀


_PRUNE_AT = 0.0
MAX_ENTRIES = 250


def _score(e, now):
    """记忆存活分数：重要度*20 + 使用*3 + 近期加分"""
    imp = int(e.get("importance", 3))
    uses = int(e.get("uses", 0))
    lu = e.get("last_used", 0) or 0
    s = imp * 20 + min(uses, 10) * 3
    if now - lu < 7 * 86400:
        s += 2
    elif now - lu < 30 * 86400:
        s += 1
    return s


def prune(mem, now=None):
    """遗忘淘汰：低重要度长期未用淡出；超上限淘汰低分"""
    now = now or time.time()
    lt = mem.get("longterm", [])
    if not lt:
        return False
    before = len(lt)
    lt = [e for e in lt
          if not (int(e.get("importance", 3)) <= 2
                  and (now - (e.get("last_used", 0) or 0)) > 60 * 86400)]
    if len(lt) > MAX_ENTRIES:
        lt.sort(key=lambda e: -_score(e, now))
        lt = lt[:MAX_ENTRIES]
    if len(lt) != before:
        mem["longterm"] = lt
        return True
    return False


def load_memory():
    global _PRUNE_AT
    try:
        with open(MEMORY_PATH, encoding="utf-8") as f:
            mem = json.load(f)
    except Exception:
        mem = {"history": [], "facts": [], "longterm": []}
    changed = False
    for e in mem.get("longterm", []):
        if "importance" not in e:
            e["importance"] = 3
            changed = True
        if "uses" not in e:
            e["uses"] = 0
            changed = True
        if "last_used" not in e:
            e["last_used"] = 0.0
            changed = True
    if "topics" not in mem:
        mem["topics"] = []
    if time.time() - _PRUNE_AT > 3600:
        _PRUNE_AT = time.time()
        if prune(mem):
            changed = True
    if changed:
        save_memory(mem)
    return mem


def save_memory(mem):
    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def embed_available():
    try:
        r = requests.get(OLLAMA_URL + "/api/tags", timeout=5)
        if r.status_code == 200:
            return any(m.get("name", "").startswith(EMBED_MODEL)
                       for m in r.json().get("models", []))
    except Exception:
        pass
    return False


def _embed_batch(texts):
    """返回 [vector,...] 或 None"""
    try:
        r = requests.post(OLLAMA_URL + "/api/embed",
                          json={"model": EMBED_MODEL, "input": texts}, timeout=60)
        if r.status_code == 200:
            return r.json().get("embeddings")
    except Exception:
        pass
    return None


def _cosine(a, b):
    try:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
    except Exception:
        return 0.0


def merge_topics(mem, topics):
    """未完结话题入库：去重、上限20、5天没续聊自动过期"""
    changed = False
    ts = mem.setdefault("topics", [])
    for t in topics:
        t = (t or "").strip()[:40]
        if not t:
            continue
        dup = False
        for x in ts:
            if _jaccard(_bigrams(x["text"]), _bigrams(t)) > 0.7:
                dup = True
                break
        if not dup:
            ts.append({"text": t, "time": time.strftime("%Y-%m-%d %H:%M"),
                        "last_used": time.time()})
            changed = True
    before = len(ts)
    ts[:] = [x for x in ts
             if time.time() - (x.get("last_used", 0) or 0) <= 5 * 86400][-20:]
    if len(ts) != before:
        changed = True
    if changed:
        save_memory(mem)
    return changed


def get_open_topics(mem, k=3):
    """返回最近未完结话题文本列表"""
    ts = [x["text"] for x in mem.get("topics", [])
          if time.time() - (x.get("last_used", 0) or 0) <= 5 * 86400]
    return ts[-k:]


def _mark_used(entries, idxs):
    """被检索命中的记忆：使用次数+1、刷新最后访问时间"""
    now = time.time()
    for i in idxs:
        try:
            entries[i]["uses"] = int(entries[i].get("uses", 0)) + 1
            entries[i]["last_used"] = now
        except Exception:
            pass


def _bigrams(text):
    t = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text.lower())
    out = set(t[i:i + 2] for i in range(len(t) - 1)) | set(t)
    return out


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def retrieve(query, entries, top_k=5):
    """按相关性返回条目文本列表（优先语义嵌入，降级词面相似）"""
    if not entries:
        return []
    texts = [e["text"] for e in entries]
    use_embed = embed_available()
    if use_embed:
        try:
            embs = _embed_batch(texts)
            if embs:
                qemb = _embed_batch([query])
                if qemb:
                    scored = sorted(
                        ((_cosine(qemb[0], e), i) for i, e in enumerate(embs)),
                        key=lambda x: -x[0])
                    picked = [(s, i) for s, i in scored if s > 0.25][:top_k]
                    if picked:
                        _mark_used(entries, [i for _, i in picked])
                        return [texts[i] for _, i in picked]
        except Exception:
            pass
    # 降级：词面检索
    qb = _bigrams(query)
    scored = sorted((( _jaccard(qb, _bigrams(t)), i) for i, t in enumerate(texts)),
                    key=lambda x: -x[0])
    picked = [(s, i) for s, i in scored if s > 0.05][:top_k]
    _mark_used(entries, [i for _, i in picked])
    return [texts[i] for _, i in picked]


def extract_longterm(user_text, reply, api_cfg, existing=None):
    """从一轮对话中提取值得长期记住的信息
    返回 (items, topics, conflicts, cur_topic)；cur_topic=本条消息在聊什么"""
    old_list = existing or []
    old_block = "\n".join("旧%d：%s" % (i + 1, t) for i, t in enumerate(old_list[-30:])) or "（无）"
    prompt = (
        "你是莫妮卡的记忆系统。从下面这轮对话中，提取值得长期记住的信息：\n"
        "1) 用户的偏好（喜欢/不喜欢/习惯/口味）\n"
        "2) 用户的重要事件（考试/比赛/旅行/生病/生日等）\n"
        "3) 对之前信息的纠正（用户纠正了某个说法时，输出纠正后的完整结论）\n"
        "4) 关于用户的重要事实\n"
        "规则：每行输出一条，每条不超过30字，末尾用【1-5】标注重要度（5=非常重要，1=随口一提的小事）；日常寒暄不记；没有值得记的就只输出\"无\"。\n"
        "另外：如果这轮对话里有没聊完、下次值得接着聊的话题（TA提到想做的事/感兴趣的东西/聊到一半的事），单独输出一行【话题】xxx，没有就不输出。\n"
        "还有：无论有没有值得记的，都输出一行【当前话题】用3-8个字概括TA这条消息在聊什么（如'高数考试'、'壁纸怎么换'），没有就输出'无'。\n"
        "最后：如果新信息与下面的旧记忆矛盾（同一件事的新旧说法相反，比如喜欢→讨厌、A学校→B学校、X岁→Y岁），输出一行【冲突】旧记忆原文｜新内容；旧记忆原文必须照抄旧列表里的原文，分隔符用全角竖线｜；有几条就输出几行；没有就只输出\"无冲突\"。\n"
        "旧记忆列表：\n" + old_block + "\n"
        "用户：" + user_text + "\n"
        "莫妮卡：" + (reply or "")[:200] + "\n"
    )
    try:
        url = api_cfg["base_url"].rstrip("/") + "/chat/completions"
        r = requests.post(url, headers={"Authorization": "Bearer " + api_cfg["api_key"],
                                        "Content-Type": "application/json"},
                          json={"model": api_cfg["model"], "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.3, "max_tokens": 300}, timeout=30)
        if r.status_code != 200:
            return []
        out = r.json()["choices"][0]["message"]["content"].strip()
        items = []
        topics = []
        conflicts = []
        cur_topic = ""
        for line in out.splitlines():
            if line.strip().startswith(("【话题】", "【冲突】", "【当前话题】")):
                continue
            line = line.strip().lstrip("-*•0123456789.、 ")
            if not line or line == "无":
                continue
            kind = "correction" if re.search(r"(纠正|更正|其实|不是.*是|改成)", line) else "fact"
            mimp = re.search(r"【(\d)】", line)
            imp = int(mimp.group(1)) if mimp else 3
            line = re.sub(r"【\d】", "", line).strip()
            items.append({"text": line[:40], "kind": kind, "importance": imp})
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("【冲突】"):
                body = line.replace("【冲突】", "").strip()
                if "｜" in body:
                    old_t, new_t = body.split("｜", 1)
                    old_t, new_t = old_t.strip(), new_t.strip()
                    if new_t and new_t != "无":
                        for t in old_list:
                            if (old_t == t or (old_t and (old_t in t or t in old_t))
                                    or _jaccard(set(_bigrams(old_t)), set(_bigrams(t))) > 0.4):
                                conflicts.append((t, new_t[:40]))
                                break
            elif line.startswith("【话题】"):
                t = line.replace("【话题】", "").strip()[:40]
                if t and t != "无":
                    topics.append(t)
            elif line.startswith("【当前话题】"):
                ct = line.replace("【当前话题】", "").strip()
                if ct and ct != "无":
                    cur_topic = ct[:12]
        # 冲突的新内容不直接入库（等用户确认），从 items 剔除
        if conflicts:
            items = [it for it in items
                     if not any(it["text"] == nt or it["text"] in nt or nt in it["text"]
                               or _jaccard(set(_bigrams(it["text"])), set(_bigrams(nt))) > 0.4
                               for _o, nt in conflicts)]
        return items, topics, conflicts, cur_topic
    except Exception:
        return [], [], [], ""


def _sorted_pairs(lt):
    """返回按时间排序的 (真实下标, 条目) 列表"""
    return sorted(enumerate(lt), key=lambda x: x[1].get("time", ""))


def classify(text):
    """记忆内容分类：偏好/事件/纠正/其他"""
    if re.search(r"(喜欢|爱|爱吃|爱听|不爱|讨厌|偏好|最爱|沉迷|习惯|口味|想学|想试)", text):
        return "偏好"
    if re.search(r"(考试|比赛|生日|旅行|生病|报名|截止|面试|开学|放假|体检|手术|住院|毕业|考研)", text):
        return "事件"
    if re.search(r"(纠正|更正|其实|不是.*是|改成|不是学)", text):
        return "纠正"
    return "其他"


def timeline():
    """按时间升序返回条目列表"""
    mem = load_memory()
    return [e for _, e in _sorted_pairs(mem.get("longterm", []))]


def delete_entry(idx):
    """按时间线序号（1起）删除记忆，返回 (ok, msg)"""
    mem = load_memory()
    lt = mem.get("longterm", [])
    pairs = _sorted_pairs(lt)
    if 0 <= idx < len(pairs):
        real = pairs[idx][0]
        gone = lt.pop(real)
        save_memory(mem)
        return True, "已删除：「%s」" % gone["text"]
    return False, "没有这条记忆"


def edit_entry(idx, new_text):
    """按时间线序号（1起）修改记忆，返回 (ok, msg)"""
    mem = load_memory()
    lt = mem.get("longterm", [])
    pairs = _sorted_pairs(lt)
    if 0 <= idx < len(pairs):
        real = pairs[idx][0]
        old_text = lt[real]["text"]
        lt[real]["text"] = new_text[:40]
        save_memory(mem)
        return True, "已修改：「%s」→「%s」" % (old_text, new_text[:40])
    return False, "没有这条记忆"


def update_entry(old_text, new_text):
    """按旧文本更新条目内容；找不到返回 False"""
    mem = load_memory()
    for e in mem["longterm"]:
        if e["text"] == old_text or old_text in e["text"] or e["text"] in old_text:
            e["text"] = new_text[:40]
            e["time"] = time.strftime("%Y-%m-%d %H:%M")
            e["importance"] = max(e.get("importance", 3), 4)
            save_memory(mem)
            return True
    return False


def clear_all():
    """清空长期记忆"""
    mem = load_memory()
    n = len(mem.get("longterm", []))
    mem["longterm"] = []
    save_memory(mem)
    return "已清空 %d 条记忆" % n


def merge_entries(mem, items):
    """去重入库：与已有条目高度相似则更新时间戳，否则新增"""
    changed = False
    for it in items:
        dup = False
        for e in mem.get("longterm", []):
            if _jaccard(_bigrams(e["text"]), _bigrams(it["text"])) > 0.75:
                dup = True
                break
        if not dup:
            mem.setdefault("longterm", []).append({
                "text": it["text"], "kind": it.get("kind", "fact"),
                "time": time.strftime("%Y-%m-%d %H:%M"),
                "importance": int(it.get("importance", 3)),
                "uses": 0, "last_used": 0.0,
            })
            changed = True
    lt = mem.get("longterm", [])
    if len(lt) > MAX_ENTRIES:
        mem["longterm"] = lt[-MAX_ENTRIES:]
        changed = True
    if changed:
        save_memory(mem)
    return changed
