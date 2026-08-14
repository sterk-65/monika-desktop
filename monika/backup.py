# -*- coding: utf-8 -*-
"""本地备份与恢复：版本化 zip 备份全部长期数据，防误操作毁档

- do_backup(): 一键备份（含全部数据文件，时间戳版本化）
- list_backups(): 按时间倒序列出备份
- restore_backup(): 恢复指定备份（恢复前自动先备份当前状态，选错能退回）
- auto_backup_if_due(): 每天最多一次自动备份（启动时调用）
"""
import os
import re
import time
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE, "backups")
AUTO_MARK = os.path.join(BACKUP_DIR, ".auto_mark")
KEEP = 30  # 最多保留份数，超出删最旧

# 长期数据文件（全部在 monika/ 根目录）
DATA_FILES = [
    "config.json",      # 设置（含 API key、称呼、关系状态）
    "memory.json",      # 长期记忆
    "brain.log",        # 全部对话历史
    "stats.json",       # 周/月陪伴报告统计
    "habit.json",       # 习惯画像
    "play_stats.json",  # 听歌统计
    "play_history.json",  # 听歌历史
    "schedule.json",    # 日程
    "daily_state.json",  # 日程提醒状态
]


def _stamp():
    return time.strftime("%Y%m%d_%H%M%S")


def do_backup(comment=""):
    """一键备份全部长期数据 → backups/backup_<时间戳>_<注释>.zip
    返回 (ok, msg)"""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        base = "backup_%s" % _stamp()
        if comment:
            base += "_" + comment
        name = base + ".zip"
        _i = 2
        while os.path.exists(os.path.join(BACKUP_DIR, name)):
            name = "%s_%d.zip" % (base, _i)  # 同秒冲突：追加序号
            _i += 1
        path = os.path.join(BACKUP_DIR, name)
        n = 0
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for fn in DATA_FILES:
                fp = os.path.join(BASE, fn)
                if os.path.isfile(fp):
                    z.write(fp, fn)
                    n += 1
        if n == 0:
            os.remove(path)
            return False, "没有找到任何数据文件，没备份"
        _cleanup()
        return True, "%s（%d 个文件）" % (name, n)
    except Exception as e:
        return False, "备份失败：%s" % e


def _cleanup():
    """保留最近 KEEP 份，删最旧"""
    try:
        lst = list_backups()
        for _path, _name, _mtime, _size, _n in lst[KEEP:]:
            try:
                os.remove(_path)
            except Exception:
                pass
    except Exception:
        pass


def list_backups():
    """返回按时间倒序的备份列表：
    [(path, name, 显示时间, 大小文本, 文件数), ...]"""
    out = []
    try:
        for fn in os.listdir(BACKUP_DIR):
            if not fn.startswith("backup_") or not fn.endswith(".zip"):
                continue
            path = os.path.join(BACKUP_DIR, fn)
            m = re.match(r"backup_(\d{8})_(\d{6})", fn)
            if m:
                dt = "%s-%s-%s %s:%s" % (m.group(1)[:4], m.group(1)[4:6], m.group(1)[6:8],
                                         m.group(2)[:2], m.group(2)[2:4])
            else:
                dt = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
            size = os.path.getsize(path)
            sz = ("%.1f KB" % (size / 1024)) if size < 1024 * 1024 else ("%.2f MB" % (size / 1024 / 1024))
            try:
                with zipfile.ZipFile(path) as z:
                    n = len(z.namelist())
            except Exception:
                n = 0
            out.append((path, fn, dt, sz, n))
    except OSError:
        pass
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def restore_backup(path):
    """用指定备份覆盖当前数据。恢复前自动先备份当前状态（防误操作）
    返回 (ok, msg)"""
    try:
        if not os.path.isfile(path):
            return False, "找不到备份文件：%s" % path
        # 先存档当前状态，选错能退回
        do_backup()
        restored = 0
        with zipfile.ZipFile(path) as z:
            for fn in z.namelist():
                # 白名单 + 防路径穿越：只恢复数据文件本身
                if fn in DATA_FILES and "/" not in fn and "\\" not in fn:
                    data = z.read(fn)
                    with open(os.path.join(BASE, fn), "wb") as f:
                        f.write(data)
                    restored += 1
        return True, "已从「%s」恢复 %d 个文件\n（恢复前已自动备份当前状态）" % (
            os.path.basename(path), restored)
    except Exception as e:
        return False, "恢复失败：%s" % e


def auto_backup_if_due():
    """每天最多一次自动备份；返回 (是否执行了, 消息)"""
    try:
        today = time.strftime("%Y-%m-%d")
        if os.path.isfile(AUTO_MARK):
            try:
                with open(AUTO_MARK, encoding="utf-8") as f:
                    if f.read().strip() == today:
                        return False, "今天已自动备份过"
            except Exception:
                pass
        ok, msg = do_backup()
        if ok:
            try:
                os.makedirs(BACKUP_DIR, exist_ok=True)
                with open(AUTO_MARK, "w", encoding="utf-8") as f:
                    f.write(today)
            except Exception:
                pass
            return True, "自动备份完成：%s" % msg
        return False, msg
    except Exception as e:
        return False, "自动备份出错：%s" % e


def list_text(limit=5):
    """聊天用的备份列表文本"""
    lst = list_backups()
    if not lst:
        return "还没有备份。对我说「备份」或右键菜单「💾 备份与恢复」"
    lines = []
    for i, (_p, _n, dt, sz, cnt) in enumerate(lst[:limit], 1):
        lines.append("%d. %s · %s · %d 个文件" % (i, dt, sz, cnt))
    if len(lst) > limit:
        lines.append("……共 %d 份" % len(lst))
    return "\n".join(lines)


def restore_text(idx):
    """聊天用的恢复命令：恢复第 idx 份备份（1 起）"""
    lst = list_backups()
    if not lst:
        return "还没有任何备份"
    if idx < 1 or idx > len(lst):
        return "没有第 %d 份（共 %d 份）。说「看看备份」列出版本" % (idx, len(lst))
    ok, msg = restore_backup(lst[idx - 1][0])
    return msg
