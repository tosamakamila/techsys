"""
scaffold_knowledge_map.py —— 从已有课程文件自动生成知识地图草稿

输入：
    - courses/<课程名>/reading_plan.md（片段列表）
    - courses/<课程名>/transformed/*.md（教案，提取概念名）

输出：
    courses/<课程名>/knowledge_map.md（如已存在则输出 knowledge_map_draft.md）

用法：
    python function/map/scaffold.py courses/<课程名>
    python function/map/scaffold.py courses/<课程名> --dry-run  # 只预览不写文件
    python function/map/scaffold.py courses/<课程名> --chapter 2  # 只生成指定章节
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def parse_reading_plan(md_path: Path) -> list:
    """从 reading_plan.md 提取片段列表，返回 [{fragment_id, chapter, topic}]"""
    if not md_path.exists():
        print(f"警告：{md_path} 不存在")
        return []

    text = md_path.read_text(encoding="utf-8")
    fragments = []

    in_table = False
    for line in text.split("\n"):
        if "片段ID" in line and "主题" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("|") and not line.strip().startswith("|---"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if len(cells) >= 4:
                fid = cells[0]
                chapter_raw = cells[2] if len(cells) > 2 else ""
                topic = cells[3] if len(cells) > 3 else ""
                chapter_match = re.search(r"第(\d+)章", chapter_raw)
                chapter_num = int(chapter_match.group(1)) if chapter_match else 0
                fragments.append({
                    "fragment_id": fid,
                    "chapter": chapter_raw,
                    "chapter_num": chapter_num,
                    "topic": topic,
                })
        if in_table and line.strip() == "":
            in_table = False

    return fragments


def extract_concepts_from_transformed(md_path: Path) -> list:
    """从教案的'结束点'和'必须掌握'中提取概念名"""
    if not md_path.exists():
        return []

    text = md_path.read_text(encoding="utf-8")
    concepts = []

    # 方法1: 从 "本堂课只处理：xxx、yyy、zzz" 提取顿号分隔的概念
    for line in text.split("\n"):
        m = re.match(r"^[-*]\s*本堂课只处理[：:]\s*(.+)", line.strip())
        if m:
            raw = m.group(1)
            # 按顿号/逗号/分号拆分
            items = re.split(r"[、，,；;]", raw)
            for item in items:
                item = item.strip().rstrip("。")
                # 进一步拆分 "xxx及其yyy" → 只取 xxx
                item = re.sub(r"及其.*$", "", item)
                item = re.sub(r"与.*$", "", item)
                if len(item) >= 2 and len(item) <= 20:
                    concepts.append(item)
            if concepts:
                return concepts

    # 方法2: 从 "必须掌握：xxx、yyy" 提取
    for line in text.split("\n"):
        m = re.match(r"^[-*]\s*必须掌握[：:]\s*(.+)", line.strip())
        if m:
            raw = m.group(1)
            items = re.split(r"[、,，;；]", raw)
            for item in items:
                item = item.strip().rstrip("。")
                item = re.sub(r"及其.*$", "", item)
                item = re.sub(r"与.*$", "", item)
                item = re.sub(r"的具体.*$", "", item)
                item = re.sub(r"的现代定义$", "", item)
                item = re.sub(r"的概念$", "", item)
                if len(item) >= 2 and len(item) <= 20:
                    concepts.append(item)
            if concepts:
                return concepts

    # 方法3: 降级——从 "### QN. 标题" 提取并简化
    for line in text.split("\n"):
        m = re.match(r"^###\s+Q\d+\.\s*(.+)", line.strip())
        if m:
            title = m.group(1).strip()
            title = re.sub(r"[？?！!。，,]+$", "", title)
            title = re.sub(r'["""]', "", title)
            # 取前12个字符作为短概念名
            if len(title) > 14:
                title = title[:12] + "…"
            if len(title) >= 2:
                concepts.append(title)

    return concepts


def extract_concepts_from_materials(md_path: Path) -> list:
    """从教材中提取概念（解析 ### N. 标题）"""
    if not md_path.exists():
        return []

    text = md_path.read_text(encoding="utf-8")
    concepts = []

    for line in text.split("\n"):
        m = re.match(r"^###\s+\d+\.\s*(.+)", line.strip())
        if m:
            concepts.append(m.group(1).strip())

    return concepts


def scaffold(course_dir: Path, target_chapter: int = 0, dry_run: bool = False):
    """主流程"""
    course_name = course_dir.name

    # 1. 解析 reading_plan
    reading_path = course_dir / "reading_plan.md"
    fragments = parse_reading_plan(reading_path)
    if not fragments:
        print("错误：未在 reading_plan.md 中提取到片段信息")
        return

    print(f"读取到 {len(fragments)} 个片段")

    # 2. 扫描 materials 目录（教材原文直接提取概念）
    materials_dir = course_dir / "materials"
    if not materials_dir.exists():
        print(f"警告：{materials_dir} 目录不存在，尝试从 transformed 提取")
        concepts_by_fragment = extract_from_transformed_legacy(course_dir, fragments)
    else:
        concepts_by_fragment = extract_from_materials(course_dir, fragments)

    # 3. 按章节分组
    chapter_fragments = defaultdict(list)
    for f in fragments:
        if target_chapter and f["chapter_num"] != target_chapter:
            continue
        fid = f["fragment_id"]
        # 展开片段 ID：L001 → [L001a, L001b]
        sub_fragments = []
        for key in concepts_by_fragment:
            if key.startswith(fid):
                sub_fragments.append(key)
        if not sub_fragments:
            sub_fragments = [fid]
        chapter_fragments[f["chapter_num"]].append({
            "chapter": f["chapter"],
            "fragments": sorted(sub_fragments),
            "topic": f["topic"],
        })

    if not chapter_fragments:
        print("错误：没有匹配的章节数据")
        return

    # 4. 生成节点列表
    nodes = []
    node_id_counter = 1

    for ch_num in sorted(chapter_fragments.keys()):
        ch_info = chapter_fragments[ch_num]
        for ch_entry in ch_info:
            prev_in_chapter = None
            for fid in ch_entry["fragments"]:
                concepts = concepts_by_fragment.get(fid, [])
                if not concepts:
                    continue
                for concept_name in concepts:
                    nid = f"N{node_id_counter:03d}"
                    deps = []
                    if prev_in_chapter:
                        deps.append(prev_in_chapter)
                    nodes.append({
                        "node_id": nid,
                        "name": concept_name,
                        "chapter": ch_entry["chapter"],
                        "depends_on": deps,
                        "fragment": fid,
                    })
                    prev_in_chapter = nid
                    node_id_counter += 1

    if not nodes:
        print("错误：未提取到任何概念节点")
        return

    print(f"\n生成 {len(nodes)} 个节点")

    # 5. 生成 Markdown
    md_lines = [f"# 知识地图：{course_name}", ""]
    md_lines.append("> [!] 此文件由 scaffold_knowledge_map.py 自动生成")
    md_lines.append("> 请检查并调整前置依赖后，运行 build_knowledge_map.py 生成状态文件")
    md_lines.append("")

    current_chapter = ""
    for node in nodes:
        if node["chapter"] != current_chapter:
            current_chapter = node["chapter"]
            md_lines.append(f"## {current_chapter}")
            md_lines.append("")
            md_lines.append("| 节点ID | 概念名 | 前置依赖 | 关联片段 |")
            md_lines.append("|--------|--------|----------|----------|")

        deps_str = ",".join(node["depends_on"]) if node["depends_on"] else "-"
        md_lines.append(
            f"| {node['node_id']} | {node['name']} | {deps_str} | {node['fragment']} |"
        )

    md_lines.append("")

    output = "\n".join(md_lines)

    if dry_run:
        print("\n─── 预览 ───")
        print(output)
        return

    # 6. 写文件
    output_path = course_dir / "knowledge_map.md"
    if output_path.exists():
        output_path = course_dir / "knowledge_map_draft.md"
        print(f"\nknowledge_map.md 已存在，写入草稿：{output_path.name}")
    else:
        print(f"\n写入：{output_path.name}")

    output_path.write_text(output, encoding="utf-8")
    print(f"完成！下一步：检查 {output_path.name} → 调整依赖 → 运行 build_knowledge_map.py")


def extract_from_materials(course_dir: Path, fragments: list) -> dict:
    """降级方案：从 materials/*.md 标题提取概念"""
    materials_dir = course_dir / "materials"
    if not materials_dir.exists():
        return {}

    concepts_by_fragment = defaultdict(list)
    # 简单方案：每个材料文件对应一个片段
    for mf in sorted(materials_dir.glob("*.md")):
        concepts = extract_concepts_from_materials(mf)
        if concepts:
            # 尝试匹配片段
            fid = None
            for f in fragments:
                if f["chapter"] in mf.stem:
                    fid = f["fragment_id"]
                    break
            if not fid:
                fid = mf.stem[:5]
            concepts_by_fragment[fid] = concepts
            print(f"  {fid} (from {mf.name}): {len(concepts)} 个概念")

    return concepts_by_fragment


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/scaffold_knowledge_map.py courses/<课程名>")
        print("      python function/map/scaffold.py courses/<课程名> --dry-run")
        print("      python function/map/scaffold.py courses/<课程名> --chapter 2")
        sys.exit(1)

    course_dir = Path(sys.argv[1])
    if not course_dir.exists():
        print(f"错误：找不到课程目录 {course_dir}")
        sys.exit(1)

    dry_run = "--dry-run" in sys.argv
    target_chapter = 0

    for i, arg in enumerate(sys.argv):
        if arg == "--chapter" and i + 1 < len(sys.argv):
            target_chapter = int(sys.argv[i + 1])

    scaffold(course_dir, target_chapter, dry_run)


if __name__ == "__main__":
    main()
