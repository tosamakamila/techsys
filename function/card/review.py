#!/usr/bin/env python3
"""知识闪卡复习工具 —— 命令行交互式间隔复习。

用法:
    python review.py <课程名>              # 全部复习模式（默认）
    python review.py <课程名> --mode spaced # 按时间复习模式
    python review.py <课程名> --help        # 查看帮助
"""

import sys
import os
import re
import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Windows GBK 终端兼容：强制 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Rich 依赖检查 ─────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.align import Align
    from rich.rule import Rule
    from rich.box import ROUNDED
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("请先安装 rich 库: pip install rich")
    sys.exit(1)

console = Console()

# ── 路径工具 ───────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent


def course_dir(course_name: str) -> Path:
    return SCRIPT_DIR / course_name


def cards_path(course_name: str) -> Path:
    return course_dir(course_name) / "cards.md"


def state_path(course_name: str) -> Path:
    return course_dir(course_name) / "review_state.json"


# ── 卡片解析 ───────────────────────────────────────────────────
def parse_cards(filepath: Path) -> list[dict]:
    """从 markdown 文件解析卡片。

    格式:
        ## 问题标题
        - category: 分类标签
        - answer: |
          答案内容（可多行）
        - explanation: |
          解释内容（可多行）
        ---
    """
    if not filepath.exists():
        console.print(f"\n[bright_red]✗ 找不到卡片文件: {filepath}[/red]\n")
        return []

    content = filepath.read_text(encoding="utf-8")
    blocks = re.split(r'\n---\s*\n', content)
    cards = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        if not lines or not lines[0].startswith("## "):
            continue

        card = {
            "question": "",
            "category": "",
            "answer": "",
            "explanation": "",
        }
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
            cards.append(card)

    return cards


# ── 状态管理（间隔复习模式）───────────────────────────────────
def load_state(filepath: Path) -> dict:
    if filepath.exists():
        return json.loads(filepath.read_text(encoding="utf-8"))
    return {"cards": {}, "last_session": ""}


def save_state(filepath: Path, state: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def filter_due_cards(cards: list[dict], state: dict) -> list[dict]:
    """筛选到期卡片（含新卡片）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    due = []
    for card in cards:
        card_id = card["question"]
        card_state = state["cards"].get(card_id)
        if card_state is None:
            # 新卡片，始终加入
            due.append(card)
        elif card_state.get("next_review", "2000-01-01") <= today:
            due.append(card)
    return due


def update_spaced_state(state: dict, card_id: str, ratings: list[int]):
    """根据本次会话的评分更新 SM-2 间隔。"""
    if card_id not in state["cards"]:
        state["cards"][card_id] = {
            "interval": 0,
            "ease": 2.5,
            "next_review": None,
            "last_review": None,
            "history": [],
        }

    entry = state["cards"][card_id]
    quality = _calc_quality(ratings)

    if quality < 3:
        entry["interval"] = 1
    else:
        if entry["interval"] == 0:
            entry["interval"] = 1
        elif entry["interval"] == 1:
            entry["interval"] = 6
        else:
            entry["interval"] = int(entry["interval"] * entry["ease"])

    entry["ease"] = max(
        1.3,
        entry["ease"]
        + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    entry["last_review"] = datetime.now().strftime("%Y-%m-%d")
    entry["next_review"] = (
        datetime.now() + timedelta(days=max(1, entry["interval"]))
    ).strftime("%Y-%m-%d")
    entry["history"].append(quality)
    state["last_session"] = datetime.now().strftime("%Y-%m-%d %H:%M")


def _calc_quality(ratings: list[int]) -> float:
    """将会话评分 (1-3) 映射为 SM-2 质量分 (0-5)。"""
    if not ratings:
        return 0
    # 1→1, 2→3, 3→5
    mapped = [1 if r == 1 else (3 if r == 2 else 5) for r in ratings]
    return sum(mapped) / len(mapped)


# ── UI 组件 ────────────────────────────────────────────────────
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def show_card(card: dict, index: int, total: int, score: int):
    """显示卡片的题目面。"""
    clear_screen()

    # ── 顶部状态栏 ──
    console.print()
    bar_width = 40
    done = int(bar_width * (index + 1) / total)
    progress = f"[bold cyan]{'━' * done}[/bold cyan][#555555]{'━' * (bar_width - done)}[/#555555]"
    console.print(
        f"  [bold #cccccc]第 {index + 1}/{total} 张[/bold #cccccc]  {progress}  "
        f"积分: {_score_badge(score)}"
    )
    console.print()
    console.print()

    # ── 分类标签 ──
    if card["category"]:
        console.print(
            Panel(
                Align.center(
                    f"[bold #7eb8ff]▎{card['category']}[/bold #7eb8ff]"
                ),
                box=ROUNDED,
                border_style="#5b8def",
                padding=(0, 4),
            )
        )
        console.print()

    # ── 问题卡片（大字号效果） ──
    question_panel = Panel(
        Align.center(
            Text(card["question"], style="bold #ffffff", justify="center"),
            vertical="middle",
        ),
        box=ROUNDED,
        border_style="bright_cyan",
        padding=(4, 8),
        title="[bold bright_cyan]问题[/bold bright_cyan]",
        title_align="left",
    )
    console.print(question_panel)

    # ── 操作提示 ──
    console.print()
    console.print(
        "  [#b0b0b0]先在脑海中回忆答案，然后按键选择：[/#b0b0b0]"
    )
    console.print()
    console.print()

    # ── 按键按钮（深色背景适配） ──
    btn_style = {
        "1": ("#ff6b6b", "#4a1515", "陌生 — 显示答案与解释"),
        "2": ("#ffc53d", "#4a3500", "有印象 — 显示答案"),
        "3": ("#73d13d", "#0d3b0d", "熟悉 — 跳过"),
    }

    for key, (fg, bg, label) in btn_style.items():
        console.print(
            f"      [{fg} on {bg}] [bold] {key} [/bold] [/]  [#cccccc]{label}[/#cccccc]",
            markup=True,
        )
    console.print()
    console.print()
    console.print("  [#888888]按 [bold #cccccc]Q[/bold #cccccc] 退出复习[/#888888]")


def show_answer(card: dict, rating: int):
    """根据评分显示答案面。"""
    console.print()
    if rating == 1:
        # 陌生：完整答案 + 解释
        console.print(Rule("[bold #7eb8ff]答案与解释[/bold #7eb8ff]", style="#5b8def"))
        console.print()
        if card["answer"]:
            console.print(
                Panel(
                    card["answer"],
                    title="[bold #7eb8ff]答案[/bold #7eb8ff]",
                    title_align="left",
                    border_style="bright_blue",
                    box=ROUNDED,
                    padding=(1, 3),
                )
            )
            console.print()
        if card["explanation"]:
            console.print(
                Panel(
                    card["explanation"],
                    title="[bold #ffc53d]核心得分点[/bold #ffc53d]",
                    title_align="left",
                    border_style="bright_yellow",
                    box=ROUNDED,
                    padding=(1, 3),
                )
            )
    elif rating == 2:
        # 有印象：仅答案
        console.print(Rule("[bold #ffc53d]答案[/bold #ffc53d]", style="#d4a017"))
        console.print()
        if card["answer"]:
            console.print(
                Panel(
                    card["answer"],
                    title="[bold #7eb8ff]答案[/bold #7eb8ff]",
                    title_align="left",
                    border_style="bright_blue",
                    box=ROUNDED,
                    padding=(1, 3),
                )
            )
    else:
        # 熟悉：简短确认
        console.print()
        console.print(
            Panel(
                Align.center("[bold #73d13d]已掌握[/bold #73d13d]"),
                border_style="bright_green",
                box=ROUNDED,
            )
        )


def show_summary(
    passed: list[dict], scores: dict, mode: str, course_name: str
):
    """显示本次复习总结。"""
    clear_screen()
    console.print()
    console.print(
        Panel(
            Align.center("[bold #ffffff]复习完成[/bold #ffffff]"),
            border_style="bright_cyan",
            box=ROUNDED,
        )
    )

    total = len(scores)
    if total == 0:
        console.print("\n  [#888888]本次没有复习任何卡片。[/#888888]\n")
        return

    passed_count = len(passed)
    avg_rounds = sum(len(v) for v in scores.values()) / max(total, 1)

    table = Table(title="[bold #ffffff]本次复习统计[/bold #ffffff]", box=ROUNDED)
    table.add_column("指标", style="bright_cyan")
    table.add_column("数值", style="#ffffff")
    table.add_row("复习模式", "全部复习" if mode == "all" else "按时间复习")
    table.add_row("课程", course_name)
    table.add_row("总卡片数", str(total))
    table.add_row("过关数", str(passed_count))
    table.add_row("未过关数", str(total - passed_count))
    table.add_row("过关率", f"{passed_count * 100 // total}%")
    table.add_row("平均轮次", f"{avg_rounds:.1f}")
    console.print(table)

    failed = [
        (card_id, ratings)
        for card_id, ratings in scores.items()
        if _final_score(ratings) < 2
    ]
    if failed:
        console.print()
        console.print(
            Panel(
                "\n".join(
                    f"  [bold #ffc53d]!![/bold #ffc53d] {cid}  [#888888](当前积分: {_final_score(r)})[/#888888]"
                    for cid, r in failed
                ),
                title="[bold #ffc53d]仍需复习[/bold #ffc53d]",
                title_align="left",
                border_style="bright_yellow",
                box=ROUNDED,
            )
        )

    console.print()
    console.print("  [#888888]按任意键退出...[/#888888]", end="")


def _score_badge(score: int) -> str:
    color = {2: "bright_green", 1: "bright_yellow", 0: "#888888", -1: "bright_red"}.get(score, "#888888")
    return f"[{color} bold]{score}[/{color} bold]"


# ── 核心复习循环 ──────────────────────────────────────────────
def review_session(cards: list[dict]) -> tuple[list[dict], dict]:
    """执行一次复习会话。返回 (过关卡片列表, 卡片评分记录)。"""
    if not cards:
        console.print("\n[bright_yellow]没有需要复习的卡片。[/yellow]\n")
        return [], {}

    # 初始化：每张卡片 score=0，评分记录为空
    scores: dict[str, int] = {c["question"]: 0 for c in cards}
    ratings_log: dict[str, list[int]] = {c["question"]: [] for c in cards}
    passed: list[dict] = []

    # 构建池并洗牌
    pool: list[dict] = list(cards)
    random.shuffle(pool)
    total_original = len(pool)
    index = 0

    while pool:
        card = pool.pop(0)
        card_id = card["question"]
        current_score = scores[card_id]

        show_card(card, index, total_original, current_score)

        # ── 获取用户输入 ──
        key = _get_key()
        if key == "q":
            console.print("\n[bright_yellow]提前退出复习。[/yellow]\n")
            break

        rating = int(key)
        ratings_log[card_id].append(rating)

        # ── 更新积分 ──
        delta = {1: -1, 2: 0, 3: 1}[rating]
        scores[card_id] = max(-1, scores[card_id] + delta)

        # ── 显示答案 ──
        show_answer(card, rating)

        # ── 判断过关 ──
        if scores[card_id] >= 2:
            passed.append(card)
            console.print()
            console.print(f"  [bold bright_green]已掌握  积分: {scores[card_id]}[/bold bright_green]")
        else:
            insert_at = random.randint(0, len(pool))
            pool.insert(insert_at, card)
            console.print()
            console.print(
                f"  [bold bright_yellow]回到复习池  积分: {scores[card_id]}[/bold bright_yellow]"
            )

        console.print()
        console.print("  [#888888]按任意键继续...[/#888888]", end="")
        _wait_key()
        index = (index + 1) % total_original

    return passed, ratings_log


def _final_score(ratings: list[int]) -> int:
    """根据评分历史计算最终积分。"""
    score = 0
    for r in ratings:
        if r == 1:
            score = max(-1, score - 1)
        elif r == 2:
            pass  # score unchanged
        elif r == 3:
            score += 1
    return score


def _get_key() -> str:
    """获取用户按键（仅接受 1/2/3/Q）。"""
    import msvcrt as m

    while True:
        key = m.getch().decode("utf-8", errors="ignore").lower()
        if key in ("1", "2", "3", "q"):
            return key


def _wait_key():
    """等待任意按键。"""
    import msvcrt as m

    m.getch()


# ── 课程选择 ───────────────────────────────────────────────────
def scan_available_courses() -> list[str]:
    """扫描 card/ 下包含 cards.md 的课程文件夹。"""
    courses = []
    if not SCRIPT_DIR.exists():
        return courses
    for d in sorted(SCRIPT_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("_") and not d.name.startswith("."):
            if (d / "cards.md").exists():
                courses.append(d.name)
    return courses


def select_course() -> Optional[str]:
    """交互式课程选择界面，返回课程名或 None（退出）。"""
    courses = scan_available_courses()
    if not courses:
        console.print("\n[bright_red]✗ 没有找到任何课程，请先在 card/ 下创建课程文件夹和 cards.md[/red]\n")
        return None

    clear_screen()
    console.print()
    console.print(
        Panel(
            Align.center("[bold #ffffff]选择要复习的课程[/bold #ffffff]"),
            border_style="bright_cyan",
            box=ROUNDED,
        )
    )
    console.print()

    for i, name in enumerate(courses, 1):
        cp = cards_path(name)
        card_count = len(parse_cards(cp))
        console.print(f"  [bold bright_cyan]{i}[/bold bright_cyan]  {name}  [#888888]({card_count} 张卡片)[/#888888]")

    console.print()
    console.print("  [#888888]按数字选择，或按 [bold #cccccc]Q[/bold #cccccc] 退出[/#888888]")

    import msvcrt as m
    while True:
        key = m.getch().decode("utf-8", errors="ignore").lower()
        if key == "q":
            return None
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(courses):
                return courses[idx]


# ── 入口 ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="知识闪卡复习工具",
        usage="python review.py [课程名] [--mode {all,spaced}]",
    )
    parser.add_argument("course", nargs="?", default=None, help="课程名称（card/ 下的文件夹名），不填则从列表选择")
    parser.add_argument(
        "--mode",
        choices=["all", "spaced"],
        default="all",
        help="复习模式: all=全部复习, spaced=按时间复习 (默认: all)",
    )
    args = parser.parse_args()

    # 未指定课程 → 交互式选择
    if args.course is None:
        chosen = select_course()
        if chosen is None:
            console.print("\n[#888888]已取消。[/#888888]\n")
            sys.exit(0)
        args.course = chosen

    # 检查课程目录
    cd = course_dir(args.course)
    if not cd.exists():
        console.print(f"\n[bright_red]✗ 课程目录不存在: {cd}[/red]")
        console.print(
            f"  请先在 card/ 下创建 [bold]{args.course}[/bold] 文件夹并放入 cards.md\n"
        )
        sys.exit(1)

    # 加载卡片
    cp = cards_path(args.course)
    all_cards = parse_cards(cp)
    if not all_cards:
        console.print(f"\n[bright_red]✗ 没有找到有效卡片，请检查: {cp}[/red]\n")
        sys.exit(1)

    # 按模式筛选
    if args.mode == "spaced":
        st = load_state(state_path(args.course))
        cards_to_review = filter_due_cards(all_cards, st)
        if not cards_to_review:
            console.print(
                "\n[bright_green]🎉 当前没有到期的卡片，休息一下吧！[/green]\n"
            )
            # 显示下次复习信息
            upcoming = []
            for c in all_cards:
                cs = st["cards"].get(c["question"])
                if cs and cs.get("next_review"):
                    upcoming.append((c["question"], cs["next_review"]))
            if upcoming:
                upcoming.sort(key=lambda x: x[1])
                console.print("[#888888]即将到来的复习:[/#888888]")
                for q, d in upcoming[:5]:
                    console.print(f"  [#888888]• {q} → {d}[/#888888]")
            console.print()
            sys.exit(0)
    else:
        st = None
        cards_to_review = list(all_cards)

    console.print(
        f"\n[bold bright_cyan]课程: {args.course}[/bold bright_cyan]"
        f"  |  模式: {'全部复习' if args.mode == 'all' else '按时间复习'}"
        f"  |  卡片: {len(cards_to_review)} 张"
    )
    console.print(
        "[#b0b0b0]规则: 1=陌生(-1)  2=有印象(0)  3=熟悉(+1)  "
        "累积到 +2 过关  最低 -1[/#b0b0b0]\n"
    )

    if args.mode == "spaced":
        console.print(
            f"[#b0b0b0]上次复习: {st.get('last_session') or '从未'}[/#b0b0b0]\n"
        )

    console.print("[#b0b0b0]按任意键开始...[/#b0b0b0]", end="")
    _wait_key()

    # 执行复习
    passed, ratings_log = review_session(cards_to_review)

    # 显示总结
    scores_map = {
        cid: ratings_log.get(cid, [])
        for cid in {c["question"] for c in cards_to_review}
    }
    show_summary(
        passed, {k: v for k, v in scores_map.items() if v}, args.mode, args.course
    )
    _wait_key()

    # 保存状态（间隔模式）
    if args.mode == "spaced" and ratings_log:
        for card_id, ratings in ratings_log.items():
            if ratings:
                update_spaced_state(st, card_id, ratings)
        save_state(state_path(args.course), st)
        console.print("\n[#888888]✓ 复习状态已保存[/#888888]")


if __name__ == "__main__":
    main()
