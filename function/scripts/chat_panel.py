"""
chat_panel.py —— 群聊 Web 面板

独立 HTTP 服务器，浏览器中展示灵、夏、柠的群聊记录。
用法：
    python function/scripts/chat_panel.py
    python function/scripts/chat_panel.py --port 8766
    python function/scripts/chat_panel.py --no-browser
"""

import os
import sys
import re
import json
import argparse
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATE_DIR = Path(__file__).resolve().parent / "state"

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_chat_messages(text: str) -> list[dict]:
    """从 markdown 文本中提取聊天消息。"""
    messages = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(灵|夏|柠)[：:]\s*(.*)", line)
        if not m:
            continue
        sender = m.group(1)
        content = m.group(2)

        action = ""
        if content.startswith("（"):
            end = content.find("）")
            if end != -1:
                action = content[1:end]
                content = content[end + 1 :].strip()

        messages.append({"sender": sender, "text": content, "action": action})

    return messages


def read_chat_data(mode: str = "all") -> dict:
    """读取群聊数据，返回 {messages, unread_messages, unread_count}。"""
    result = {"messages": [], "unread_messages": [], "unread_count": 0}

    unread_path = STATE_DIR / "group_chat_unread.md"
    if unread_path.exists():
        unread = parse_chat_messages(unread_path.read_text(encoding="utf-8"))
        result["unread_messages"] = unread
        result["unread_count"] = len(unread)

    if mode == "all":
        chat_path = STATE_DIR / "group_chat.md"
        if chat_path.exists():
            result["messages"] = parse_chat_messages(chat_path.read_text(encoding="utf-8"))

    return result


class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write(f"  [{self.command}] {args[0]}\n")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html = (TEMPLATE_DIR / "chat.html").read_text(encoding="utf-8")
            self._send_html(html)

        elif self.path == "/api/chat":
            mode = "all"
            if "?mode=unread" in self.path:
                mode = "unread"
            self._send_json(read_chat_data(mode))

        elif self.path.startswith("/avatars/"):
            filename = self.path.split("/")[-1]
            avatar_path = TEMPLATE_DIR / "assets" / "avatars" / filename
            if avatar_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(avatar_path.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

        elif self.path == "/api/health":
            self._send_json({"status": "ok"})

        else:
            self.send_response(404)
            self.end_headers()


def main():
    parser = argparse.ArgumentParser(description="群聊 Web 面板")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), ChatHandler)
    url = f"http://127.0.0.1:{args.port}"

    print(f"""
╭──────────────────────────────────────╮
│        群聊面板 —— 灵 · 夏 · 柠       │
│                                      │
│  服务器: {url}              │
│  按 Ctrl+C 停止。                    │
╰──────────────────────────────────────╯
""")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务器已停止。")
        server.server_close()


if __name__ == "__main__":
    main()
