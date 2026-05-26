"""
recommend_node.py

从 knowledge_map_state.json 找出薄弱节点，按影响面排序推荐。

用法：
    python function/map/recommend.py courses/<课程名>
    python function/map/recommend.py courses/<课程名> --top 5

输入：
    courses/<课程名>/knowledge_map_state.json

输出：
    Top N 优先修补推荐列表
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from _shared import compute_transitive_impact


def recommend(course_dir: Path, top_n: int = 3) -> list:
    """返回推荐列表"""
    state_path = course_dir / "knowledge_map_state.json"
    if not state_path.exists():
        print(f"错误：找不到 {state_path}")
        return []

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, KeyError):
        print("错误：知识地图状态文件损坏")
        sys.exit(1)
    nodes = state["nodes"]

    # 收集薄弱节点
    weak_nodes = []
    for nid, node in nodes.items():
        if node["status"] in ("卡住", "不稳"):
            impact = compute_transitive_impact(nid, nodes)
            weak_nodes.append({
                "node_id": nid,
                "name": node["name"],
                "chapter": node["chapter"],
                "status": node["status"],
                "impact": impact,
                "stuck_detail": node.get("stuck_detail", ""),
                "fragment": node.get("fragment", ""),
                "source": node.get("source", node.get("lesson_plan", "")),
            })

    # 按影响面降序
    weak_nodes.sort(key=lambda x: (-x["impact"], x["status"] == "不稳"))
    return weak_nodes[:top_n]


def output_json(results, nodes, course_info):
    """以 JSON 格式输出推荐结果，供 AI 解析。"""
    status_count = {}
    for n in nodes.values():
        status_count[n["status"]] = status_count.get(n["status"], 0) + 1

    output = {
        "course": course_info.get("course", ""),
        "last_updated": course_info.get("last_updated", ""),
        "status_summary": status_count,
        "total_nodes": len(nodes),
        "recommendations": [
            {
                "rank": i + 1,
                "node_id": r["node_id"],
                "name": r["name"],
                "chapter": r["chapter"],
                "status": r["status"],
                "impact": r["impact"],
                "depends_on": nodes[r["node_id"]].get("depends_on", []),
                "needed_by": nodes[r["node_id"]].get("needed_by", []),
                "fragment": r.get("fragment", ""),
                "source": r.get("source", r.get("lesson_plan", "")),
                "stuck_detail": r.get("stuck_detail", ""),
            }
            for i, r in enumerate(results)
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/recommend_node.py courses/<课程名> [--top N]")
        sys.exit(1)

    course_dir = Path(sys.argv[1])
    top_n = 3

    # 解析 --top / --json 参数
    args = sys.argv[2:]
    json_mode = False
    for i, arg in enumerate(args):
        if arg == "--top" and i + 1 < len(args):
            try:
                top_n = int(args[i + 1])
            except ValueError:
                print(f"警告：--top 参数 '{args[i + 1]}' 不是有效数字，使用默认值 3")
                top_n = 3
        elif arg == "--json":
            json_mode = True

    results = recommend(course_dir, top_n)

    if not results:
        if json_mode:
            try:
                state = json.loads((course_dir / "knowledge_map_state.json").read_text(encoding="utf-8"))
            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                print(json.dumps({"error": "无法读取知识地图文件"}, ensure_ascii=False))
                return
            print(json.dumps({
                "course": state.get("course", ""),
                "last_updated": state.get("last_updated", ""),
                "status_summary": {},
                "total_nodes": len(state.get("nodes", {})),
                "recommendations": [],
            }, ensure_ascii=False, indent=2))
        else:
            print("没有找到薄弱节点。所有概念状态正常。")
        return

    # 加载课程状态
    try:
        state = json.loads((course_dir / "knowledge_map_state.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        print("错误：无法读取知识地图文件")
        return

    if json_mode:
        output_json(results, state["nodes"], state)
        return

    print(f"课程：{state.get('course', '未知')}")
    print(f"最后更新：{state.get('last_updated', '无')}")
    print()

    status_symbol = {"卡住": "[!]", "不稳": "[~]"}
    for i, r in enumerate(results, 1):
        sym = status_symbol.get(r["status"], "?")
        chapter = r["chapter"]
        impact_desc = ""
        if r["impact"] >= 5:
            impact_desc = f" — 影响 {r['impact']} 个后继节点，堵在{chapter}"
        elif r["impact"] >= 2:
            impact_desc = f" — 影响 {r['impact']} 个后继节点"
        elif r["impact"] == 0:
            impact_desc = " — 无后继节点依赖，可延后处理"
        else:
            impact_desc = f" — 影响 {r['impact']} 个后继节点"

        print(f"  {i}. {sym} {r['node_id']} {r['name']} [{r['status']}]{impact_desc}")
        if r["stuck_detail"]:
            print(f"     详情：{r['stuck_detail']}")
        if r.get("source"):
            print(f"     来源：{r['source']}")


def dashboard(course_dir: Path):
    """教师仪表盘：章节级进度条 + 薄弱概念一览"""
    state_path = course_dir / "knowledge_map_state.json"
    if not state_path.exists():
        print(f"错误：找不到 {state_path}")
        return

    state = json.loads(state_path.read_text(encoding="utf-8"))
    nodes = state["nodes"]

    # 按章节分组统计
    chapters = {}
    for nid, node in nodes.items():
        ch = node.get("chapter", "未分类")
        if ch not in chapters:
            chapters[ch] = {"total": 0, "稳固": 0, "不稳": 0, "卡住": 0, "未学": 0}
        chapters[ch]["total"] += 1
        st = node["status"]
        if st in chapters[ch]:
            chapters[ch][st] += 1

    BAR_W = 28

    print(f"\n{'='*50}")
    print(f"  知识地图仪表盘：{state.get('course', '未知')}")
    print(f"  更新日期：{state.get('last_updated', '无')}")
    print(f"{'='*50}")

    total_nodes = len(nodes)
    stable_total = sum(c["稳固"] for c in chapters.values())
    stuck_total = sum(c["卡住"] for c in chapters.values())

    print(f"\n  总计 {total_nodes} 个节点 | 稳固 {stable_total}/{total_total_ratio(total_nodes, stable_total)} | 卡住 {stuck_total}")

    print(f"\n  ── 章节进度 ──")
    for ch_name in sorted(chapters.keys()):
        c = chapters[ch_name]
        pct = c["稳固"] / c["total"] * 100 if c["total"] > 0 else 0
        filled = int(BAR_W * c["稳固"] / c["total"]) if c["total"] > 0 else 0
        bar = "█" * filled + "░" * (BAR_W - filled)
        stuck_marker = f" ⚠️ {c['卡住']}" if c["卡住"] > 0 else ""
        unstable_marker = f" ~{c['不稳']}" if c["不稳"] > 0 else ""
        print(f"  {ch_name:16s} [{bar}] {c['稳固']}/{c['total']} ({pct:.0f}%){stuck_marker}{unstable_marker}")

    # 薄弱概念按影响面排列
    print(f"\n  ── 薄弱概念（影响面排序）──")
    weak = []
    for nid, node in nodes.items():
        if node["status"] in ("卡住", "不稳"):
            impact = compute_transitive_impact(nid, nodes)
            weak.append((nid, node, impact))
    weak.sort(key=lambda x: -x[2])

    if not weak:
        print("  无薄弱概念！")
    else:
        for nid, node, impact in weak[:8]:
            sym = "⚠️" if node["status"] == "卡住" else "~"
            ch = node.get("chapter", "")
            print(f"  {sym} {nid} {node['name']} [{node['status']}] - 影响 {impact} 个后继 | {ch}")
        if len(weak) > 8:
            print(f"  ... 还有 {len(weak) - 8} 个薄弱节点")

    print()


def total_total_ratio(total, stable):
    """返回掌握比例字符串"""
    if total == 0:
        return "0%"
    return f"{stable/total*100:.0f}%"


if __name__ == "__main__":
    # 检查是否为仪表盘模式
    if "--dashboard" in sys.argv:
        if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
            print("用法：python scripts/recommend_node.py courses/<课程名> --dashboard")
            sys.exit(1)
        course_dir = Path(sys.argv[1])
        if not course_dir.exists():
            print(f"错误：找不到课程目录 {course_dir}")
            sys.exit(1)
        dashboard(course_dir)
    else:
        main()
