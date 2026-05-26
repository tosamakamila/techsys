"""
knowledge_panel.py —— 知识地图可视化面板

启动本地 HTTP 服务器，在浏览器中呈现 DOL 风格界面：
- 知识地图（Canvas 依赖关系图、拓扑分层布局、节点详情浮动面板）
- 闪卡复习（全部/间隔模式、SM-2 算法）
- 课程进度（课堂状态、阅读计划、学习者档案）

地图导航和教学对话由终端 map.py + Claude Code 完成，本网站作为知识和进度的可视化仪表盘。

用法：
    python web/knowledge_panel.py
    python web/knowledge_panel.py --port 8765
    python web/knowledge_panel.py --no-browser
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
from datetime import datetime, date, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs as _stdlib_parse_qs, unquote

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "function" / "scripts"))

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
#  群聊解析
# ═══════════════════════════════════════════════════════════

def _parse_chat_messages(text: str) -> list:
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
                content = content[end + 1:].strip()

        messages.append({"sender": sender, "text": content, "action": action})

    return messages


# ═══════════════════════════════════════════════════════════
#  闪卡逻辑（从 review.py 移植核心算法）
# ═══════════════════════════════════════════════════════════

# 内存中的闪卡会话: {session_id: session_data}
flashcard_sessions = {}
SESSION_MAX_AGE_SECONDS = 7200  # 2 小时过期


def _cleanup_stale_sessions():
    """清理过期会话，防止内存泄漏。"""
    now_ts = datetime.now().timestamp()
    stale = [
        sid for sid, s in flashcard_sessions.items()
        if now_ts - s.get("_created", 0) > SESSION_MAX_AGE_SECONDS
    ]
    for sid in stale:
        del flashcard_sessions[sid]


def parse_cards(course_id):
    """解析 cards.md，返回卡片列表。格式与 review.py parse_cards 一致。"""
    cards_path = PROJECT_ROOT / "function" / "card" / course_id / "cards.md"
    if not cards_path.exists():
        return []
    text = cards_path.read_text(encoding="utf-8")
    blocks = re.split(r'\n---\s*\n', text)
    cards = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        if not lines or not lines[0].startswith("## "):
            continue
        card = {"question": "", "category": "", "answer": "", "explanation": ""}
        card["question"] = lines[0][3:].strip()
        current_field = None
        current_lines = []
        for line in lines[1:]:
            matched = False
            for field in ("category", "answer", "explanation"):
                prefix = f"- {field}:"
                if line.startswith(prefix):
                    if current_field:
                        card[current_field] = "\n".join(current_lines).strip()
                    val = line[len(prefix):].strip()
                    if val in ("", "|"):
                        current_field = field
                        current_lines = []
                    else:
                        card[field] = val
                        current_field = None
                        current_lines = []
                    matched = True
                    break
            if not matched and current_field:
                current_lines.append(line.strip())
        if current_field:
            card[current_field] = "\n".join(current_lines).strip()
        if card["question"] and (card["answer"] or card["explanation"]):
            card["id"] = card["question"][:60]
            cards.append(card)
    return cards


def load_review_state(course_id):
    path = PROJECT_ROOT / "function" / "card" / course_id / "review_state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    return {"cards": {}, "last_session": ""}


def save_review_state(course_id, state):
    path = PROJECT_ROOT / "function" / "card" / course_id / "review_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def filter_due_cards(cards, state):
    today = date.today().isoformat()
    due = []
    for c in cards:
        cid = c["id"]
        if cid not in state["cards"]:
            due.append(c)
        elif state["cards"][cid].get("next_review") and state["cards"][cid].get("next_review", "") <= today:
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


def _get_lesson_count(course_id):
    """从 progress.md 历史归档条目数推算已上课次数。"""
    pg_path = PROJECT_ROOT / "courses" / course_id / "progress.md"
    if not pg_path.exists():
        return 0
    try:
        text = pg_path.read_text(encoding="utf-8")
        count = 0
        for m in re.finditer(r"^[-*]\s*\d{4}-\d{2}-\d{2}\s*[|（(]", text, re.MULTILINE):
            count += 1
        return count
    except (OSError, ValueError):
        return 0


# ═══════════════════════════════════════════════════════════
#  统计计算
# ═══════════════════════════════════════════════════════════

def _compute_stats(course_id):
    """计算指定课程的学习统计数据。"""
    result = {
        "study_dates": [],
        "streak": 0,
        "lesson_count": 0,
        "current_lesson": 0,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "concept_stats": {"stable": 0, "unstable": 0, "stuck": 0, "unlearned": 0},
        "total_concepts": 0,
        "hardest_concepts": [],
    }
    status_map = {"稳固": "stable", "不稳": "unstable", "卡住": "stuck", "未学": "unlearned"}

    # ── 课次统计 ──
    lesson_count = _get_lesson_count(course_id)
    result["lesson_count"] = lesson_count
    result["current_lesson"] = lesson_count + 1  # 当前是第几节

    # ── 一次性读取知识地图 ──
    km_path = PROJECT_ROOT / "courses" / course_id / "knowledge_map_state.json"
    km_nodes = {}
    if km_path.exists():
        try:
            km = json.loads(km_path.read_text(encoding="utf-8"))
            km_nodes = km.get("nodes", {})
        except (json.JSONDecodeError, KeyError):
            pass

    # ── 1. 概念状态统计 ──
    result["total_concepts"] = len(km_nodes)
    for n in km_nodes.values():
        s = n.get("status", "未学")
        key = status_map.get(s, "unlearned")
        result["concept_stats"][key] += 1

    # ── 2. 学习日期和连续天数 ──
    pg_path = PROJECT_ROOT / "courses" / course_id / "progress.md"
    if pg_path.exists():
        try:
            text = pg_path.read_text(encoding="utf-8")
            dates = set()
            for m in re.finditer(r"日期[：:]\s*(\d{4}-\d{2}-\d{2})", text):
                d = m.group(1)
                try:
                    date.fromisoformat(d)
                    dates.add(d)
                except ValueError:
                    pass
            for m in re.finditer(r"^[-*]\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE):
                d = m.group(1)
                try:
                    date.fromisoformat(d)
                    dates.add(d)
                except ValueError:
                    pass

            result["study_dates"] = sorted(dates)

            if dates:
                sorted_dates = sorted(dates, reverse=True)
                today = date.today()
                streak = 0
                check = today
                if check.isoformat() not in sorted_dates:
                    check = check - timedelta(days=1)
                for d_str in sorted_dates:
                    if d_str == check.isoformat():
                        streak += 1
                        check = check - timedelta(days=1)
                    elif d_str < check.isoformat():
                        break
                result["streak"] = streak
        except (OSError, ValueError):
            pass

    # ── 3. 最难概念 ──
    hardest = []
    seen_names = set()

    # 3a. 从知识地图取"卡住"节点（按影响面排序）
    for nid, n in km_nodes.items():
        if n.get("status") == "卡住":
            impact = len(n.get("needed_by", []))
            hardest.append({
                "name": n.get("name", nid),
                "node_id": nid,
                "status": "卡住",
                "review_rounds": 0,
                "impact": impact,
            })
    hardest.sort(key=lambda x: -x["impact"])
    for sn in hardest:
        seen_names.add(sn["name"])

    # 3b. 从 review_state 取复习轮次最多的卡片
    rs_path = PROJECT_ROOT / "function" / "card" / course_id / "review_state.json"
    if rs_path.exists():
        try:
            rs = json.loads(rs_path.read_text(encoding="utf-8"))
            rv_cards = []
            for cid, cs in rs.get("cards", {}).items():
                rounds = len(cs.get("history", []))
                if rounds >= 2:
                    rv_cards.append((cid[:40], rounds))
            rv_cards.sort(key=lambda x: -x[1])
            for name, rounds in rv_cards[:5]:
                if name not in seen_names:
                    hardest.append({
                        "name": name,
                        "node_id": "",
                        "status": "不稳",
                        "review_rounds": rounds,
                        "impact": 0,
                    })
                    seen_names.add(name)
        except (json.JSONDecodeError, KeyError):
            pass

    # 按 review_rounds 降序 + impact 降序，取 top 5
    hardest.sort(key=lambda x: (-x["review_rounds"], -x["impact"]))
    result["hardest_concepts"] = hardest[:5]

    return result


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
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send_html(get_html_page())

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

        elif self.path.startswith("/api/stats"):
            params = _get_params(self.path)
            course_id = params.get("course", "")
            err = validate_course_id(course_id)
            if err:
                self._send_json({"error": err}, 400)
                return
            stats = _compute_stats(course_id)
            self._send_json(stats)

        elif self.path.startswith("/api/learner-profile"):
            lp_path = PROJECT_ROOT / "teacher" / "learner_profile.md"
            if lp_path.exists():
                self._send_json({"content": lp_path.read_text(encoding="utf-8")})
            else:
                self._send_json({"content": ""})

        elif self.path.startswith("/assets/"):
            asset_path = TEMPLATE_DIR / unquote(self.path.lstrip("/"))
            if asset_path.exists() and asset_path.is_file():
                content_type = "image/png"
                if asset_path.suffix == ".jpg" or asset_path.suffix == ".jpeg":
                    content_type = "image/jpeg"
                elif asset_path.suffix == ".svg":
                    content_type = "image/svg+xml"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(asset_path.read_bytes())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Asset Not Found")

        elif self.path.startswith("/api/group-chat"):
            params = _get_params(self.path)
            mode = params.get("mode", "all")  # all / unread
            result = {"messages": [], "unread_count": 0}

            # 读取未读消息
            unread_path = PROJECT_ROOT / "function" / "scripts" / "state" / "group_chat_unread.md"
            if unread_path.exists():
                unread_msgs = _parse_chat_messages(unread_path.read_text(encoding="utf-8"))
                result["unread_count"] = len(unread_msgs)
                result["unread_messages"] = unread_msgs

            # 读取完整历史
            if mode == "all":
                chat_path = PROJECT_ROOT / "function" / "scripts" / "state" / "group_chat.md"
                if chat_path.exists():
                    result["messages"] = _parse_chat_messages(chat_path.read_text(encoding="utf-8"))

            self._send_json(result)

        elif self.path == "/api/health":
            self._send_json({"status": "ok"})

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "无效的 JSON"}, 400)
            return

        if self.path == "/api/group-chat/mark-read":
            unread_path = PROJECT_ROOT / "function" / "scripts" / "state" / "group_chat_unread.md"
            chat_path = PROJECT_ROOT / "function" / "scripts" / "state" / "group_chat.md"

            if not unread_path.exists():
                self._send_json({"ok": True, "count": 0})
                return

            unread_text = unread_path.read_text(encoding="utf-8")
            unread_msgs = _parse_chat_messages(unread_text)

            if unread_msgs:
                # 追加到完整历史
                lines = []
                for msg in unread_msgs:
                    if msg["action"]:
                        lines.append(f"{msg['sender']}：（{msg['action']}）{msg['text']}")
                    else:
                        lines.append(f"{msg['sender']}：{msg['text']}")
                append_block = "\n\n" + "\n\n".join(lines)

                chat_content = ""
                if chat_path.exists():
                    chat_content = chat_path.read_text(encoding="utf-8")
                chat_path.write_text(chat_content + append_block, encoding="utf-8")

            # 重置未读文件
            unread_template = "# 未读消息\n\n> 下课后自动生成。学习者说“看看消息”时展示。查看并回复后清空本文件。\n\n---\n\n"
            unread_path.write_text(unread_template, encoding="utf-8")

            self._send_json({"ok": True, "count": len(unread_msgs)})

        elif self.path == "/api/flashcard/start":
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

            _cleanup_stale_sessions()
            flashcard_sessions[session_id] = {
                "_created": datetime.now().timestamp(),
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
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ═══════════════════════════════════════════════════════════
#  HTML 页面（延迟加载）
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def get_html_page():
    # 每次请求都重新读取，方便开发调试
    return (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")


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
