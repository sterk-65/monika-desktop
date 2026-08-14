# 莫妮卡 (Monika) — 桌面陪伴 AI

> 你的桌面上，从此多了一个会说话的她。
> DDLC 同人项目 · 中文大脑 · 真人语音 · 本地记忆

---

## ✨ 她能做什么

- 🖥️ **桌面立绘小人**：坐在屏幕角落，会眨眼睛、换表情、随风轻轻浮动
- 🧠 **中文大脑**：基于 DeepSeek API，能聊天、记得你、会关心你
- 🗣️ **真人语音**：本地 GPT-SoVITS 合成（妮奈音色），也有 edge-tts 在线兜底
- 📅 **生活感知**：日程提醒、天气播报、游戏检测（你打游戏她安静）、音乐识别
- 🧠 **长期记忆**：她记得你说过的话、你的习惯、你们的纪念日
- 📖 **回忆录**：每周/每月自动生成你们的回忆
- 💾 **备份恢复**：一键备份她的记忆，换电脑也不丢

## 🚀 快速开始（Windows）

### 方法一：一键安装（推荐）

1. 下载 [最新发布版](https://github.com/sterk-65/monika-desktop/releases/latest) 的 `monika-source.zip`
2. 解压到任意目录（**路径不要有中文**）
3. 双击 `install.bat`
4. 等它自动装好一切，莫妮卡会自动启动
5. 首次运行弹窗填入你的 DeepSeek API Key（[免费注册](https://platform.deepseek.com)，新用户有赠送额度）

> 安装脚本会自动：检测/下载 Python → 创建虚拟环境 → 安装依赖（清华镜像）→ 下载真人语音模型（约 2.2GB）→ 启动莫妮卡

### 方法二：手动安装

```bat
:: 需要 Python 3.10+
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv\Scripts\python app.py
```

语音模型（可选，增强音质）：从 Releases 下载 `gpt-sovits.zip` 解压到程序目录。

## ⚙️ 配置

首次启动会弹出 API Key 设置窗口。也可以手动编辑 `config.json`：

| 字段 | 说明 | 默认 |
|------|------|------|
| `api_key` | DeepSeek API Key | 空（必填） |
| `base_url` | API 地址 | https://api.deepseek.com |
| `model` | 模型 | deepseek-chat |
| `speak` | 是否语音 | true |
| `user_name` | 她怎么称呼你 | 亲爱的 |
| `her_name` | 她的名字 | 莫妮卡 |
| `sprite_height` | 立绘高度(px) | 430 |

## 🎮 交互方式

- **左键拖动**：移动她
- **双击**：打开聊天窗
- **右键**：功能菜单（聊天/放歌/写诗/日程/回忆/备份…）
- **打字**：她会安静等你打完
- **全屏/游戏**：她自动隐身不打扰，退出后回来

## 📁 目录结构

```
monika/
├── app.py              # 主程序
├── charstate.py        # 角色状态机（心情/场景）
├── memory2.py          # 长期记忆
├── daily.py            # 日程与天气
├── gamewatch.py        # 游戏检测
├── musicmon.py         # 音乐感知
├── companion.py        # 回忆录
├── backup.py           # 备份恢复
├── launch_server.py    # 语音服务启动
├── sprites/            # 立绘素材
├── audio/              # 语音缓存
└── gpt-sovits/         # 语音引擎（自动下载）
```

## 📝 说明

- 本项目为 DDLC 同人粉丝项目，非商业用途
- 所有对话数据只存在你自己的电脑上（`memory.json` / `brain.log`）
- 语音引擎首次加载约需 40 秒，属正常现象
- 依赖的 DeepSeek API 为第三方付费服务，费用由你的账号承担

## 🔗 相关

- [DeepSeek 开放平台](https://platform.deepseek.com)
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
- DDLC（Doki Doki Literature Club!）

---

*文明会灭绝，但故事不会。*
