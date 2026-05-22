"""
update_knowledge_map.py

下课后自动运行，扫描 lesson_state.md 和 reading_plan.md，
更新 knowledge_map_state.json 中每个节点的状态。

用法：
    python scripts/update_knowledge_map.py courses/<课程名>

输入：
    courses/<课程名>/knowledge_map_state.json
    courses/<课程名>/lesson_state.md
    courses/<课程名>/reading_plan.md

输出：
    更新后的 knowledge_map_state.json + 变更摘要
"""

import json
import re
import sys
from pathlib import Path

from _shared import concept_match


def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"警告：{path} 不存在，使用空数据")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_lesson_state(md_path: Path) -> dict:
    """从 lesson_state.md 提取「已建立的结论」和「卡住的问题」"""
    if not md_path.exists():
        return {"conclusions": [], "stuck": []}

    text = md_path.read_text(encoding="utf-8")
    conclusions = []
    stuck = []

    in_conclusions = False
    in_stuck = False

    for line in text.split("\n"):
        stripped = line.strip()

        if re.match(r"^##?\s*已建立的结论", stripped):
            in_conclusions = True
            in_stuck = False
            continue
        if re.match(r"^##?\s*卡住的问题|正在卡住", stripped):
            in_stuck = True
            in_conclusions = False
            continue
        if re.match(r"^##?\s", stripped) and not re.match(r"^###?\s", stripped):
            in_conclusions = False
            in_stuck = False
            continue

        # 提取列表项
        item_match = re.match(r"^[-*]\s+(.+)", stripped)
        if item_match:
            content = item_match.group(1).strip()
            if in_conclusions:
                # 检测弱化标记
                weak = bool(re.search(r"[?？]|需巩固|待巩固|多用|不太稳|有点模糊", content))
                conclusions.append({"text": content, "weak": weak})
            elif in_stuck:
                stuck.append(content)

    return {"conclusions": conclusions, "stuck": stuck}


def parse_reading_plan(md_path: Path) -> dict:
    """从 reading_plan.md 提取每个片段的狀態"""
    if not md_path.exists():
        return {}

    text = md_path.read_text(encoding="utf-8")
    fragment_status = {}

    # 从已完成的標籤中提取
    for line in text.split("\n"):
        # 匹配 "L001：xxx" 或 "- L001：xxx"
        match = re.match(r"^[-*]\s*(L\d+)[：:](.+)", line.strip())
        if match:
            fid = match.group(1)
            label = match.group(2).strip()
            if "需复习" in label:
                fragment_status[fid] = "需复习"
            elif "已上课" in label:
                fragment_status[fid] = "已上课"
            elif "跳过" in label:
                fragment_status[fid] = "跳过"

    # 从分片计划表格中提取
    in_table = False
    for line in text.split("\n"):
        if "片段ID" in line and "状态" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("|") and not line.strip().startswith("|---"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if len(cells) >= 4:
                fid = cells[0]  # 片段ID
                status = ""
                # 找状态列（通常在后面）
                for c in cells[1:]:
                    if c in ("未处理", "已生成教案", "已上课", "需复习", "跳过"):
                        status = c
                        break
                if fid and status and fid not in fragment_status:
                    fragment_status[fid] = status
        if in_table and line.strip() == "":
            in_table = False

    return fragment_status


def concept_in_text(concept_name: str, conclusions: list) -> tuple:
    """检查概念名是否出现在结论中，返回 (出现, 弱化)"""
    for c in conclusions:
        if concept_match(concept_name, [c["text"]]):
            return (True, c["weak"])
    return (False, False)


def concept_in_stuck(concept_name: str, stuck: list) -> bool:
    """检查概念名是否出现在卡住列表中"""
    return concept_match(concept_name, stuck)


def update_state(state: dict, lesson_data: dict, fragment_status: dict) -> list:
    """更新节点状态，返回变更列表"""
    nodes = state["nodes"]
    conclusions = lesson_data["conclusions"]
    stuck = lesson_data["stuck"]
    changes = []

    for nid, node in nodes.items():
        old_status = node["status"]
        new_status = old_status
        reason = ""

        fragment_id = node.get("fragment", "")
        concept = node.get("name", "")

        # 1. 关联片段未学 → 未学
        if fragment_id and fragment_status.get(fragment_id) in ("未处理", "已生成教案"):
            if fragment_status.get(fragment_id) == "未处理":
                new_status = "未学"
                if old_status != new_status:
                    reason = f"片段 {fragment_id} 尚未学习"
            elif fragment_status.get(fragment_id) == "已生成教案":
                # 教案已生成但还没上课 → 保持未学
                if old_status != "未学":
                    new_status = "未学"
                    reason = "教案已生成但尚未上课"

        # 2. 在卡住列表中 → 卡住
        if concept_in_stuck(concept, stuck):
            new_status = "卡住"
            node["stuck_detail"] = "学生在课堂上卡在这个概念上"
            if old_status != new_status:
                reason = "概念出现在卡住问题中"

        # 3-4. 在结论中
        elif conclusions:
            found, weak = concept_in_text(concept, conclusions)
            if found:
                if weak:
                    new_status = "不稳"
                    if old_status != new_status:
                        reason = "结论中出现但标注了薄弱标记"
                else:
                    new_status = "稳固"
                    if old_status != new_status:
                        reason = "概念已在结论中建立"

        # 5. 片段已上课但概念不在结论中
        if new_status == old_status and fragment_id:
            fs = fragment_status.get(fragment_id, "")
            if fs in ("已上课", "需复习") and not concept_in_text(concept, conclusions)[0]:
                new_status = "不稳"
                if old_status != new_status:
                    reason = f"片段 {fragment_id} 已上课但概念未在结论中出现"

        # 应用变更
        if new_status != old_status:
            from datetime import datetime
            node["status"] = new_status
            node["updated"] = datetime.now().strftime("%Y-%m-%d")
            changes.append({
                "node_id": nid,
                "name": concept,
                "old": old_status,
                "new": new_status,
                "reason": reason,
            })

    return changes


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/update_knowledge_map.py courses/<课程名>")
        sys.exit(1)

    course_dir = Path(sys.argv[1])
    if not course_dir.exists():
        print(f"错误：找不到课程目录 {course_dir}")
        sys.exit(1)

    state_path = course_dir / "knowledge_map_state.json"
    lesson_path = course_dir / "lesson_state.md"
    reading_path = course_dir / "reading_plan.md"

    # 加载数据
    state = load_json(state_path)
    if not state:
        print("错误：knowledge_map_state.json 不存在，请先运行 build_knowledge_map.py")
        sys.exit(1)

    print(f"扫描课程：{state.get('course', '未知')}")

    lesson_data = parse_lesson_state(lesson_path)
    fragment_status = parse_reading_plan(reading_path)

    print(f"  结论数：{len(lesson_data['conclusions'])}")
    print(f"  卡住问题数：{len(lesson_data['stuck'])}")
    print(f"  片段状态数：{len(fragment_status)}")

    # 更新状态
    changes = update_state(state, lesson_data, fragment_status)

    # 写回
    from datetime import datetime
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 打印变更摘要
    if changes:
        print(f"\n[{state['last_updated']}] 知识地图状态更新：")
        for ch in changes:
            arrow = "→"
            print(f"  {ch['node_id']} {ch['name']}: {ch['old']} {arrow} {ch['new']}（{ch['reason']}）")
    else:
        print(f"\n[{state['last_updated']}] 无状态变更")

    # 统计
    status_count = {}
    for n in state["nodes"].values():
        status_count[n["status"]] = status_count.get(n["status"], 0) + 1
    print(f"\n当前状态分布：")
    for s in ("稳固", "不稳", "卡住", "未学"):
        if s in status_count:
            print(f"  {s}：{status_count[s]}")


if __name__ == "__main__":
    main()
