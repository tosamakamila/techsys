"""
build_knowledge_map.py

从 knowledge_map.md 生成 knowledge_map_state.json 骨架。
运行时机：教材改写后一次性运行，或老师编辑 knowledge_map.md 后运行。

用法：
    python scripts/build_knowledge_map.py courses/<课程名>/knowledge_map.md
"""

import json
import re
import sys
from pathlib import Path


def parse_knowledge_map(md_path: Path) -> dict:
    """解析 knowledge_map.md，提取课程信息和所有节点"""
    text = md_path.read_text(encoding="utf-8")

    course_name = ""
    chapters = []  # [(chapter_title, [nodes])]
    current_chapter = ""
    current_nodes = []

    lines = text.split("\n")

    # 提取课程名（第一行）
    title_match = re.match(r"^#\s+知识地图：(.+)", lines[0])
    if title_match:
        course_name = title_match.group(1).strip()

    in_table = False
    for line in lines:
        # 检测章节标题
        chapter_match = re.match(r"^##\s+(第\d+章.+)", line)
        if chapter_match:
            if current_nodes:
                chapters.append((current_chapter, current_nodes))
            current_chapter = chapter_match.group(1).strip()
            current_nodes = []
            in_table = False
            continue

        # 检测表格头
        if line.strip().startswith("| 节点ID"):
            in_table = True
            continue

        # 检测表格分隔线
        if in_table and re.match(r"^\|[-|\s]+\|$", line.strip()):
            continue

        # 解析表格行
        if in_table and line.strip().startswith("|") and not line.strip().startswith("|---"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if len(cells) >= 3 and cells[0] and not cells[0].startswith("-"):
                node_id = cells[0]
                concept = cells[1] if len(cells) > 1 else ""
                prereq_raw = cells[2] if len(cells) > 2 else ""
                fragment = cells[3] if len(cells) > 3 else ""

                # 解析前置依赖
                if prereq_raw and prereq_raw != "-":
                    depends_on = [p.strip() for p in prereq_raw.split(",")]
                else:
                    depends_on = []

                current_nodes.append({
                    "node_id": node_id,
                    "name": concept,
                    "depends_on": depends_on,
                    "fragment": fragment,
                })

        # 表格结束
        if in_table and line.strip() == "":
            in_table = False

    # 保存最后一章
    if current_nodes:
        chapters.append((current_chapter, current_nodes))

    return {
        "course": course_name,
        "chapters": chapters,
    }


def build_state(parsed: dict) -> dict:
    """从解析结果构建 knowledge_map_state.json"""
    nodes = {}
    chapter_order = []

    for chapter_title, chapter_nodes in parsed["chapters"]:
        chapter_order.append(chapter_title)
        for node in chapter_nodes:
            nid = node["node_id"]
            nodes[nid] = {
                "name": node["name"],
                "chapter": chapter_title,
                "status": "未学",
                "depends_on": node["depends_on"],
                "needed_by": [],  # 后面统一计算
                "fragment": node["fragment"],
                "lesson_plan": f"transformed/{node['fragment']}_{parsed['course']}.md" if node["fragment"] else "",
                "stuck_detail": "",
                "updated": "",
            }

    # 双向推导：从 depends_on 计算 needed_by
    for nid, node in nodes.items():
        for dep in node["depends_on"]:
            if dep in nodes:
                if nid not in nodes[dep]["needed_by"]:
                    nodes[dep]["needed_by"].append(nid)
            else:
                print(f"  警告：节点 {nid} 的前置依赖 {dep} 不存在")

    return {
        "course": parsed["course"],
        "last_updated": "",
        "nodes": nodes,
        "chapter_order": chapter_order,
    }


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/build_knowledge_map.py courses/<课程名>/knowledge_map.md")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"错误：找不到文件 {md_path}")
        sys.exit(1)

    course_dir = md_path.parent
    state_path = course_dir / "knowledge_map_state.json"

    print(f"解析 {md_path} ...")
    parsed = parse_knowledge_map(md_path)
    print(f"  课程：{parsed['course']}")
    for ch_title, ch_nodes in parsed["chapters"]:
        print(f"  {ch_title}：{len(ch_nodes)} 个节点")

    state = build_state(parsed)

    # 如果 state.json 已存在，保留已有状态
    if state_path.exists():
        print(f"\n发现已有 state.json，保留节点状态...")
        existing = json.loads(state_path.read_text(encoding="utf-8"))
        existing_nodes = existing.get("nodes", {})
        kept = 0
        for nid in state["nodes"]:
            if nid in existing_nodes:
                old_status = existing_nodes[nid].get("status", "未学")
                if old_status != "未学":
                    state["nodes"][nid]["status"] = old_status
                    state["nodes"][nid]["stuck_detail"] = existing_nodes[nid].get("stuck_detail", "")
                    state["nodes"][nid]["updated"] = existing_nodes[nid].get("updated", None)
                    kept += 1
        # 更新 last_updated
        state["last_updated"] = existing.get("last_updated", "")
        print(f"  保留了 {kept} 个节点的已有状态")

        # 检测新增/删除的节点
        old_ids = set(existing_nodes.keys())
        new_ids = set(state["nodes"].keys())
        added = new_ids - old_ids
        removed = old_ids - new_ids
        if added:
            print(f"  新增节点：{', '.join(sorted(added))}")
        if removed:
            print(f"  已删除节点：{', '.join(sorted(removed))}")

    # 写回
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n已生成 {state_path}")
    print(f"  总节点数：{len(state['nodes'])}")
    print(f"  章节数：{len(state['chapter_order'])}")

    # 验证：检查是否有孤立依赖
    all_ids = set(state["nodes"].keys())
    for nid, node in state["nodes"].items():
        for dep in node["depends_on"]:
            if dep not in all_ids:
                print(f"  警告：{nid} 依赖了不存在的节点 {dep}")


if __name__ == "__main__":
    main()
