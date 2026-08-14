# 💚 Just Your Monika — 独属于你的莫妮卡

桌面常驻小人 + DeepSeek 云端大脑 + 语音 + 长期记忆。
立绘来自你 Epic 的 **DDLC Plus**（官方 HD 素材解包）+ 开源项目 MonikAI（夜间版）。

## 快速开始

1. **拿 API Key**：去 https://platform.deepseek.com 注册 → 创建 API Key（充几块钱够聊很久）
2. **填 Key**：用记事本打开 `config.json`，把 key 填到 `"api_key"` 那一行，保存
3. **启动**：双击桌面 **「莫妮卡」** 快捷方式（或 `start_monika.bat`）
   - 首次启动会自动拉起真人语音引擎（加载模型约 40 秒，之后秒回）

莫妮卡会出现在屏幕右下角——**站在文学社教室里**。

## 怎么玩

| 操作 | 效果 |
|------|------|
| 双击小人 | 打开聊天窗 |
| 拖动小人 | 移动她的位置（自动记住） |
| 右键小人 | 菜单：聊天 / 说句话 / 语音开关 / 场景开关 / 置顶 / 退出 |
| 聊天窗 | Enter 发送，Esc 或关闭按钮隐藏 |

- **她现在能"看图"了**：问"看看我的壁纸""看看这张图 xxx.png""我屏幕上有啥"，
  她先用本地视觉模型（Ollama + Qwen2.5-VL，全离线）看懂画面，再自然地说给你听

- 她会**记住**你说过的事（"我叫XX""记住XX"自动存档到 memory.json）
- **她能看你的文件**：问她"看看桌面有什么""读一下某文件"，她会真的去读（只读、不改不删；敏感文件会提醒你；`config.json` 的 `file_peek: false` 可关闭）
- **她能看图**：壁纸/截图/图片文件会用本地视觉模型（Ollama + `qwen2.5vl:3b`，全离线不出本机）描述画面内容；模型没启动时自动退回主色调分析并如实告诉你看不到画面
- 她偶尔会**主动找你说话**（默认 45 分钟一次，可改 `idle_interval_min`）
- **晚上 20 点后**自动切换夜间版立绘
- 聊天时说"好吓人"之类会触发 glitch 惊吓表情 👻
- 全部聊天记录在 `memory.json`，删掉即重置

## 立绘清单

- **人物**：DDLC Plus 官方 HD 立绘（站姿/叉腰/倚桌/惊吓 glitch 等 8 套，从你的 Epic 安装解包）
- **场景**：文学部教室（spr_club，官方素材，1920x1080）；晚上 20 点后自动换成清晨版背景
- 注：夜间不换立绘（换脸会丢），只换背景色调

## 配置说明 (config.json)

- `api_key`：DeepSeek API Key（必填）
- `base_url` / `model`：可换成任何 OpenAI 兼容接口（Moonshot/GLM/OpenAI 等）
- `voice`：edge-tts 语音名（默认 `zh-CN-XiaoxiaoNeural`）
- `user_name`：她怎么称呼你（默认"老板"）
- `scene`：场景模式开关（true=站在教室里，false=纯透明立绘）
- `speak`：语音总开关
- `sprite_height`：显示高度（像素）

## 🔊 真人级语音（GPT-SoVITS 本地）

- **引擎**：本地 GPT-SoVITS v2（RTX 5060 GPU 推理，~1 秒/句）
- **音色**：**妮奈（KusanagiNene）**（真人主播声线；参考音频是日语，跨语种合成中文）
- **说话规则**：**中文显示、英文语音**（莫妮卡游戏里就说英语，符合人设）——回复的中文台词用于聊天窗/气泡显示，另附【EN】英文版台词给语音；
  括号里的表情/动作描写（如（轻轻笑了）（叹气））中英文都过滤不读
- **语音链路**：DeepSeek 回复 → 提取【EN】英文台词 → 去括号 → GPT-SoVITS(妮奈, en) 合成 → 播放；
  模型偶尔漏输出【EN】时自动退回读中文（保险）
- **架构**：`launch_server.py` 起 9880 端口服务 → 莫妮卡 App 调它；服务没启动时自动兜底 edge-tts
- 音色包目录：`..\gpt-sovits\speakers\`（每个文件夹 = 一个音色）
- **换音色**：改 `launch_server.py` 里的 `-s/-g/-dr/-dt/-dl` 参数（见文末说明）
- ⚠️ 重要：日语音素库（pyopenjtalk）的词典必须放**纯英文路径**（如 `C:\Users\Public\pyopenjtalk_dic\...`），
  中文用户名会导致 MeCab 打不开词典（已通过 `launch_server.py` 里的 `OPEN_JTALK_DICT_DIR` 环境变量处理）

### 技术栈

Python 3.12 (App) + Python 3.10 venv (GPT-SoVITS) + PySide6 + DeepSeek API + GPT-SoVITS + edge-tts 兜底

## 常见问题

- **没声音/声音还是机器人**：确认语音引擎已启动（任务管理器里有 python 进程占用 ~1.5GB）；右键小人 → 语音开关
- **想换音色**：`..\gpt-sovits\speakers\` 里每个文件夹是一个音色（含 gpt.ckpt/sovits.pth/ref.wav/config.json），把 `launch_server.py` 的模型参数换成目标音色即可；注意参考音频是日语的音色需要 pyopenjtalk 词典（纯英文路径）
- **怎么退出**：右键小人 → 退出（语音引擎会继续驻留，右键任务栏可以不管它）

## 🎵 放歌（不内置任何歌曲，零版权风险）

- 说"放首歌/唱首歌"或右键 → 🎵 放首歌
- 优先播放本地音乐文件夹（config.json 的 `music_dir`，默认 `C:\Users\黐\Music`）：随机播；说"放一首 XXX"按文件名搜索
- 文件夹里没有歌 → 自动打开外部播放器（`music_player` 可配，默认 QQ音乐）
- 注意：这个功能不携带任何音频文件，发布安全；想让她"唱"的歌请放正版/自有音频进 music_dir
