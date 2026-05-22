"""
map_server.py —— 知识地图可视化面板

启动本地 HTTP 服务器，在浏览器中呈现 DOL 风格界面：
- 知识地图（Canvas 依赖关系图、拓扑分层布局、节点详情浮动面板）
- 闪卡复习（全部/间隔模式、SM-2 算法）
- 课程进度（课堂状态、阅读计划、学习者档案）

地图导航和教学对话由终端 map.py + Claude Code 完成，本网站作为知识和进度的可视化仪表盘。

用法：
    python scripts/map_server.py
    python scripts/map_server.py --port 8765
    python scripts/map_server.py --no-browser
"""

import os
import sys
import json
import argparse
import webbrowser
import subprocess
import re
import random
from pathlib import Path
from datetime import datetime, date
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs as _stdlib_parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


from _shared import scan_courses


def validate_course_id(course_id: str) -> str:
    """校验 course_id 不含路径遍历字符，返回错误信息或空字符串。"""
    if not course_id:
        return "缺少 course 参数"
    if ".." in course_id or "/" in course_id or "\\" in course_id:
        return "无效的 course 参数"
    return ""


# ═══════════════════════════════════════════════════════════
#  闪卡逻辑（从 review.py 移植核心算法）
# ═══════════════════════════════════════════════════════════

# 内存中的闪卡会话: {session_id: session_data}
flashcard_sessions = {}


def parse_cards(course_id):
    """解析 cards.md，返回卡片列表。"""
    cards_path = PROJECT_ROOT / "card" / course_id / "cards.md"
    if not cards_path.exists():
        return []
    text = cards_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n---\n", text)
    cards = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        qm = re.search(r"##\s+问题\s*\n(.+)", block)
        cm = re.search(r"- category:\s*(.+)", block)
        am = re.search(r"- answer:\s*(.+?)(?:\n|$)", block)
        em = re.search(r"- explanation:\s*(.+?)(?:\n|$)", block)
        if qm:
            cards.append({
                "id": qm.group(1).strip()[:60],
                "question": qm.group(1).strip(),
                "category": cm.group(1).strip() if cm else "",
                "answer": am.group(1).strip() if am else "",
                "explanation": em.group(1).strip() if em else "",
            })
    return cards


def load_review_state(course_id):
    path = PROJECT_ROOT / "card" / course_id / "review_state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    return {"cards": {}, "last_session": ""}


def save_review_state(course_id, state):
    path = PROJECT_ROOT / "card" / course_id / "review_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def filter_due_cards(cards, state):
    today = date.today().isoformat()
    due = []
    for c in cards:
        cid = c["id"]
        if cid not in state["cards"]:
            due.append(c)
        elif state["cards"][cid].get("next_review", "") <= today:
            due.append(c)
    return due


def update_spaced_state(card_id, session_ratings, state):
    """SM-2 简化算法更新间隔。"""
    card_state = state["cards"].get(card_id, {
        "interval": 1, "ease": 2.5, "next_review": "", "last_review": "", "history": []
    })

    if not session_ratings:
        return

    quality_map = {1: 1, 2: 3, 3: 5}
    avg_quality = sum(quality_map.get(r, 3) for r in session_ratings) / len(session_ratings)

    card_state["history"].append(round(avg_quality, 1))
    card_state["last_review"] = date.today().isoformat()

    if avg_quality < 3:
        card_state["interval"] = 1
    else:
        card_state["interval"] = int(card_state["interval"] * card_state["ease"])
        card_state["ease"] = max(1.3, card_state["ease"] + (0.1 - (5 - avg_quality) * (0.08 + (5 - avg_quality) * 0.02)))

    from datetime import timedelta
    next_date = date.today() + timedelta(days=card_state["interval"])
    card_state["next_review"] = next_date.isoformat()

    state["cards"][card_id] = card_state


# ═══════════════════════════════════════════════════════════
#  HTTP 请求处理
# ═══════════════════════════════════════════════════════════

def _get_params(path):
    """从URL路径解析查询参数，值展平为字符串。"""
    parsed = urlparse(path)
    raw = _stdlib_parse_qs(parsed.query)
    return {k: v[0] if v else "" for k, v in raw.items()}


class MapHandler(BaseHTTPRequestHandler):
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
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send_html(HTML_PAGE)

        elif self.path == "/api/init":
            courses = scan_courses()
            self._send_json({"courses": courses})

        elif self.path.startswith("/api/cards"):
            params = _get_params(self.path)
            course_id = params.get("course", "")
            err = validate_course_id(course_id)
            if err:
                self._send_json({"error": err}, 400)
                return
            cards = parse_cards(course_id)
            self._send_json({"cards": cards, "count": len(cards)})

        elif self.path.startswith("/api/review-state"):
            params = _get_params(self.path)
            course_id = params.get("course", "")
            err = validate_course_id(course_id)
            if err:
                self._send_json({"error": err}, 400)
                return
            state = load_review_state(course_id)
            self._send_json(state)

        elif self.path.startswith("/api/knowledge-map"):
            params = _get_params(self.path)
            course_id = params.get("course", "")
            err = validate_course_id(course_id)
            if err:
                self._send_json({"error": err}, 400)
                return
            km_path = PROJECT_ROOT / "courses" / course_id / "knowledge_map_state.json"
            if km_path.exists():
                try:
                    data = json.loads(km_path.read_text(encoding="utf-8"))
                    self._send_json(data)
                except (json.JSONDecodeError, KeyError):
                    self._send_json({"error": "知识地图文件损坏"}, 500)
            else:
                self._send_json({"error": "该课程没有知识地图"}, 404)

        elif self.path.startswith("/api/progress"):
            params = _get_params(self.path)
            course_id = params.get("course", "")
            err = validate_course_id(course_id)
            if err:
                self._send_json({"error": err}, 400)
                return
            result = {}
            # lesson_state.md
            ls_path = PROJECT_ROOT / "courses" / course_id / "lesson_state.md"
            if ls_path.exists():
                result["lesson_state"] = ls_path.read_text(encoding="utf-8")
            # reading_plan.md
            rp_path = PROJECT_ROOT / "courses" / course_id / "reading_plan.md"
            if rp_path.exists():
                result["reading_plan"] = rp_path.read_text(encoding="utf-8")
            # progress.md
            pg_path = PROJECT_ROOT / "courses" / course_id / "progress.md"
            if pg_path.exists():
                result["progress"] = pg_path.read_text(encoding="utf-8")
            self._send_json(result)

        elif self.path.startswith("/api/learner-profile"):
            lp_path = PROJECT_ROOT / "teacher" / "learner_profile.md"
            if lp_path.exists():
                self._send_json({"content": lp_path.read_text(encoding="utf-8")})
            else:
                self._send_json({"content": ""})

        elif self.path == "/api/health":
            self._send_json({"status": "ok"})

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "无效的 JSON"}, 400)
            return

        if self.path == "/api/flashcard/start":
            course_id = data.get("course", "")
            err = validate_course_id(course_id)
            if err:
                self._send_json({"error": err}, 400)
                return
            mode = data.get("mode", "all")
            cards = parse_cards(course_id)
            if not cards:
                self._send_json({"error": "该课程没有闪卡"}, 404)
                return

            import uuid
            session_id = str(uuid.uuid4())[:8]

            pool = list(cards)
            if mode == "spaced":
                rs = load_review_state(course_id)
                pool = filter_due_cards(cards, rs)
                if not pool:
                    self._send_json({"done": True, "message": "没有到期的卡片，太棒了！"})
                    return

            random.shuffle(pool)

            flashcard_sessions[session_id] = {
                "course_id": course_id,
                "mode": mode,
                "pool": pool,
                "scores": {},
                "ratings_log": {},
                "passed": [],
                "current_idx": 0,
                "total": len(pool),
            }

            card = pool[0]
            self._send_json({
                "session_id": session_id,
                "card": {"id": card["id"], "question": card["question"],
                         "category": card["category"]},
                "progress": {"current": 1, "total": len(pool), "passed": 0},
            })

        elif self.path == "/api/flashcard/rate":
            session_id = data.get("session_id", "")
            rating = data.get("rating", 0)  # 1/2/3
            show_answer = data.get("show_answer", False)

            session = flashcard_sessions.get(session_id)
            if not session:
                self._send_json({"error": "会话不存在或已过期"}, 404)
                return

            card = session["pool"][session["current_idx"]]
            cid = card["id"]

            if show_answer:
                # 用户请求查看答案
                self._send_json({
                    "answer": card["answer"],
                    "explanation": card["explanation"],
                })
                return

            # 记录评分
            if cid not in session["scores"]:
                session["scores"][cid] = 0
            if cid not in session["ratings_log"]:
                session["ratings_log"][cid] = []

            score_map = {1: -1, 2: 0, 3: 1}
            session["scores"][cid] += score_map.get(rating, 0)
            session["ratings_log"][cid].append(rating)

            score = session["scores"][cid]

            if score >= 2:
                # 过关
                session["passed"].append(card)
                session["pool"].pop(session["current_idx"])
            else:
                # 放回池中随机位置
                current_card = session["pool"].pop(session["current_idx"])
                if len(session["pool"]) > 0:
                    insert_pos = random.randint(0, len(session["pool"]))
                    session["pool"].insert(insert_pos, current_card)
                else:
                    session["pool"].append(current_card)

            # 下一张
            if len(session["pool"]) == 0:
                # 全部完成
                course_id = session["course_id"]
                if session["mode"] == "spaced":
                    rs = load_review_state(course_id)
                    for cid2, ratings in session["ratings_log"].items():
                        update_spaced_state(cid2, ratings, rs)
                    rs["last_session"] = datetime.now().isoformat()
                    save_review_state(course_id, rs)

                total = session["total"]
                passed = len(session["passed"])
                failed = total - passed
                del flashcard_sessions[session_id]
                self._send_json({
                    "done": True,
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "passed_cards": [c["question"][:40] for c in session["passed"]],
                })
                return

            # 下一张卡片
            next_card = session["pool"][0]
            session["current_idx"] = 0
            self._send_json({
                "card": {"id": next_card["id"], "question": next_card["question"],
                         "category": next_card["category"]},
                "progress": {
                    "current": len(session["passed"]) + 1,
                    "total": session["total"],
                    "passed": len(session["passed"]),
                    "score": score,
                },
            })

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ═══════════════════════════════════════════════════════════
#  HTML 页面
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
HTML_PAGE = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="苏格拉底式教学系统 - DOL 风格完整客户端")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), MapHandler)
    url = f"http://127.0.0.1:{args.port}"

    print(f"""
╭──────────────────────────────────────────────╮
│     苏格拉底式教学系统 —— 完整客户端         │
│                                              │
│  服务器: {url}                      │
│                                              │
│  功能：地图导航 | 闪卡复习 | 知识地图 | 进度  │
│  教学场景触发后，切到 Claude Code 继续        │
│                                              │
│  按 Ctrl+C 停止服务器。                      │
╰──────────────────────────────────────────────╯
""")

    if not args.no_browser:
        print("  正在打开浏览器...")
        webbrowser.open(url)

    print("  等待连接...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务器已停止。")
        server.server_close()


if __name__ == "__main__":
    main()
