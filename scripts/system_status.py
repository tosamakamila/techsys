"""
system_status.py —— 输出系统状态摘要

避免将完整 knowledge_map_state.json 加载到 LLM 上下文。

用法：
    python scripts/system_status.py [--json]
"""

import json
import sys
from pathlib import Path
from datetime import date

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent


def get_status(json_mode: bool = False):
    """收集系统状态，返回 dict 或打印文本"""
    result = {}

    # 1. map_state.json
    ms_path = SCRIPT_DIR / "state" / "map_state.json"
    if ms_path.exists():
        ms = json.loads(ms_path.read_text(encoding="utf-8"))
        result["location"] = ms.get("last_location", "?")
        result["teacher"] = ms.get("last_teacher", "?")
        result["course"] = ms.get("last_course", "")
        result["classmate"] = ms.get("last_classmate", False)
    else:
        result["location"] = "?"
        result["teacher"] = "?"
        result["course"] = ""
        result["classmate"] = False

    course = result.get("course", "")

    # 2. knowledge_map_state.json（统计摘要）
    if course:
        km_path = ROOT / "courses" / course / "knowledge_map_state.json"
        if km_path.exists():
            km = json.loads(km_path.read_text(encoding="utf-8"))
            nodes = km.get("nodes", {})
            status_count = {}
            for n in nodes.values():
                s = n["status"]
                status_count[s] = status_count.get(s, 0) + 1
            result["total_nodes"] = len(nodes)
            result["status_summary"] = status_count
            result["last_updated"] = km.get("last_updated", "")
        else:
            result["total_nodes"] = 0
            result["status_summary"] = {}
            result["last_updated"] = ""

    # 3. progress.md（课次统计）
    if course:
        pg_path = ROOT / "courses" / course / "progress.md"
        if pg_path.exists():
            lines = pg_path.read_text(encoding="utf-8").split("\n")
            archive_count = sum(1 for l in lines if l.startswith("- 20"))
            result["session_count"] = archive_count
        else:
            result["session_count"] = 0

    # 4. 连续天数（从 progress.md 归档日期推算）
    result["streak"] = _calc_streak(course) if course else 0

    if json_mode:
        return result
    else:
        _print_status(result)
        return result


def _calc_streak(course: str) -> int:
    """从 progress.md 归档推算连续学习天数"""
    pg_path = ROOT / "courses" / course / "progress.md"
    if not pg_path.exists():
        return 0

    import re
    text = pg_path.read_text(encoding="utf-8")
    dates = re.findall(r"(\d{4}-\d{2}-\d{2})", text)
    if not dates:
        return 0

    unique_dates = sorted(set(dates), reverse=True)
    today = str(date.today())
    streak = 0
    from datetime import datetime, timedelta

    check_date = datetime.strptime(today, "%Y-%m-%d")
    for d in unique_dates:
        dt = datetime.strptime(d, "%Y-%m-%d")
        diff = (check_date - dt).days
        if diff <= 1:
            streak += 1
            check_date = dt
        elif streak > 0:
            break

    return streak


def _print_status(s: dict):
    """打印可读状态"""
    print(f"位置：{s.get('location', '?')}")
    print(f"老师：{s.get('teacher', '?')}")
    if s.get("classmate"):
        print("同学：夏（陪读）")
    print(f"课程：{s.get('course', '无')}")
    print(f"课次：{s.get('session_count', 0)}")
    print(f"连续：{s.get('streak', 0)} 天")

    nodes = s.get("total_nodes", 0)
    if nodes > 0:
        print(f"知识地图：{nodes} 节点 ", end="")
        summary = s.get("status_summary", {})
        parts = [f"{k}{v}" for k, v in summary.items()]
        print("| ".join(parts))

    updated = s.get("last_updated", "")
    if updated:
        print(f"地图更新：{updated}")


def main():
    json_mode = "--json" in sys.argv

    if json_mode:
        result = get_status(json_mode=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        get_status(json_mode=False)


if __name__ == "__main__":
    main()
