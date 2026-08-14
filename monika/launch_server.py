# -*- coding: utf-8 -*-
"""启动 GPT-SoVITS 真人语音服务（若已在运行则跳过）"""
import os
import socket
import subprocess
import sys

# pythonw 兼容：无控制台时 stdout/stderr 为 None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

PORT = 9880


def port_open(port):
    s = socket.socket()
    try:
        s.settimeout(2)
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def main():
    if port_open(PORT):
        print("真人语音服务已在运行 (127.0.0.1:%d)" % PORT)
        return
    root = os.path.dirname(os.path.abspath(__file__))
    gs = os.path.abspath(os.path.join(root, "..", "gpt-sovits"))
    env = dict(os.environ, PYTHONPATH=os.path.join(gs, "GPT_SoVITS"))
    # 中文用户名机器：pyopenjtalk 词典必须放纯英文路径（MeCab 编码问题），
    # 存在才设置；其他机器用 pyopenjtalk 默认路径即可
    _dict = r"C:\Users\Public\pyopenjtalk_dic\open_jtalk_dic_utf_8-1.11"
    if os.path.isdir(_dict):
        env["OPEN_JTALK_DICT_DIR"] = _dict
    cmd = [
        os.path.join(gs, ".venv", "Scripts", "pythonw.exe"),  # pythonw：无控制台子系统，避免终端关闭时被 forrtl 杀掉
        os.path.join(gs, "api.py"),
        "-s", os.path.join(gs, "GPT_SoVITS", "pretrained_models", "gsv-v2final-pretrained", "s2G2333k.pth"),
        "-g", os.path.join(gs, "GPT_SoVITS", "pretrained_models", "gsv-v2final-pretrained",
                          "s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt"),
        "-dr", os.path.join(gs, "speakers", "KusanagiNene", "ref_nasal2.wav"),
        "-dt", "いいんじゃない。最近、一緒に歌ってる人の声に合わせられるようになってきたし",
        "-dl", "ja",
        "-d", "cuda",
        "-p", str(PORT),
    ]
    print("启动真人语音引擎（首次加载模型约 40 秒）...")
    sys.stdout.flush()
    # 必须在 gpt-sovits 目录下运行（sv.py 等用 os.getcwd() 拼相对路径）
    log = open(os.path.join(gs, "api_server.log"), "a", encoding="utf-8", errors="replace")
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)  # 无控制台窗口，避免 forrtl window-CLOSE 中止
    subprocess.run(cmd, env=env, cwd=gs, stdout=log, stderr=log, creationflags=flags)


if __name__ == "__main__":
    main()
