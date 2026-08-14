# -*- coding: utf-8 -*-
"""统一角色状态机：心情/场景/话题/最近事件/关系阶段 —— 单一事实源。

解决"各功能各自判断导致行为冲突"：
- 心情：带来源权重仲裁（对话 > 台词情绪 > 场景 > 事件 > 系统），低权威不能覆盖高权威刚设置的心情，超时自动回落
- 场景：desktop / game / fullscreen / away，场景变更联动心情
- 话题：AI 每轮提取当前话题，1 小时过期
- 最近事件：环形缓冲 12 条，主动内容统一登记
- 关系阶段：config 持久化，这里持有运行时副本
"""
import time
from collections import deque


class RoleState:
    """统一角色状态（每个 app 一个实例，作为唯一状态源）"""

    # 心情来源权威度：数字越大越权威
    MOOD_W = {"user": 3, "emotion": 2, "scene": 2, "event": 1, "system": 0}
    MOOD_CN = {"happy": "开心", "sad": "难过", "angry": "生气",
               "surprised": "惊讶", "neutral": "平静", "idle": "悠闲"}
    SCENE_CN = {"desktop": "桌面陪伴", "game": "陪你玩游戏",
                "fullscreen": "全屏应用中", "away": "TA暂时离开"}
    KIND_CN = {"music": "音乐", "system": "系统", "game": "游戏",
               "chat": "闲聊", "event": "事件", "schedule": "日程",
               "conflict": "冲突询问"}

    def __init__(self, cfg=None):
        cfg = cfg or {}
        self.mood = "neutral"
        self.mood_src = ""
        self.mood_t = 0.0
        self.mood_w = -1
        self.scene = "desktop"
        self.scene_meta = ""
        self.scene_t = 0.0
        self.topic = None          # {"text", "t", "src"}
        self.topic_cnt = 0
        self.events = deque(maxlen=12)
        self.rel_stage = cfg.get("relationship", "热恋中（满好感）")
        self.rel_hist = []         # [(date, old, new)]

    # ---------- 心情 ----------
    def set_mood(self, mood, src="system", weight=None, force=False):
        """写心情。仲裁规则：权重更高直接覆盖；同级/低权重需等 3 分钟让位；
        force 无条件覆盖（仅限用户直接指定）。返回是否生效。"""
        w = self.MOOD_W.get(src, 0) if weight is None else weight
        age = time.time() - self.mood_t
        if force or w >= self.mood_w or age > 180:
            self.mood = mood
            self.mood_src = src
            self.mood_w = w
            self.mood_t = time.time()
            return True
        return False

    def get_mood(self):
        """读心情：10 分钟无新设置回落 neutral（长时间无交互，表情自然归位）"""
        if time.time() - self.mood_t > 600:
            return "neutral"
        return self.mood

    def sync_sprite(self, sprite):
        """把仲裁后的心情同步到立绘"""
        try:
            sprite.set_mood(self.get_mood())
        except Exception:
            pass

    # ---------- 场景 ----------
    def set_scene(self, scene, meta=""):
        """写场景。返回是否有变化。场景联动心情：进入游戏 → 开心（权威度 2）。"""
        if scene == self.scene and meta == self.scene_meta:
            return False
        old = self.scene
        self.scene = scene
        self.scene_meta = meta
        self.scene_t = time.time()
        if scene == "game" and old != "game":
            self.set_mood("happy", src="scene")
        return True

    def is_quiet(self):
        """静默场景：游戏/全屏/离开 —— 主动内容应闭嘴"""
        return self.scene in ("game", "fullscreen", "away")

    # ---------- 话题 ----------
    def set_topic(self, text, src="ai"):
        text = (text or "").strip()
        if not text or text == "无":
            return
        self.topic = {"text": text, "t": time.time(), "src": src}
        self.topic_cnt += 1

    def touch_topic(self):
        if self.topic:
            self.topic["t"] = time.time()

    def get_topic(self, window=3600):
        """读当前话题：超过 1 小时未触碰视为话题已散"""
        if self.topic and time.time() - self.topic["t"] < window:
            return self.topic
        return None

    # ---------- 事件 ----------
    def push_event(self, kind, zh, priority=0, emotion=""):
        self.events.append({"time": time.time(), "kind": kind,
                            "zh": (zh or "")[:50], "prio": priority,
                            "emotion": emotion})

    def recent_events(self, n=5):
        return list(self.events)[-n:]

    # ---------- 关系 ----------
    def set_rel_stage(self, stage):
        if stage and stage != self.rel_stage:
            old = self.rel_stage
            self.rel_stage = stage
            self.rel_hist.append((time.strftime("%Y-%m-%d %H:%M"), old, stage))
            return (old, stage)
        return None

    # ---------- 统一状态摘要（注入 AI，保证言行一致） ----------
    def to_prompt(self):
        t = self.get_topic()
        if t:
            who = "TA" if t["src"] == "user" else "你"
            topic_s = "「%s」（%s提到）" % (t["text"], who)
        else:
            topic_s = "无"
        evs = self.recent_events(3)
        ev_s = "；".join("%s:%s" % (self.KIND_CN.get(e["kind"], e["kind"]), e["zh"])
                         for e in evs) if evs else "无"
        meta_s = "（%s）" % self.scene_meta if self.scene_meta else ""
        return ("【当前状态】心情=%s；场景=%s%s；当前话题=%s；最近事件：%s；关系阶段=%s"
                % (self.MOOD_CN.get(self.get_mood(), self.get_mood()),
                   self.SCENE_CN.get(self.scene, self.scene), meta_s,
                   topic_s, ev_s, self.rel_stage))
