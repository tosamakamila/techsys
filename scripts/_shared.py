"""
_shared.py —— 脚本共享模块

提供 map.py、knowledge_panel.py、recommend_node.py、update_knowledge_map.py 共用的函数。
"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def scan_characters():
    """扫描 characters/ 目录，返回 {id: {name, role, folder}} 的 dict。

    每个角色目录需有一个 {folder.name}.md 或 {folder.name}.yaml 文件。
    优先读取 .yaml（name/id 字段），回退到 .md（首行标题）。
    """
    chars_dir = PROJECT_ROOT / "characters"
    if not chars_dir.exists():
        return {}

    characters = {}
    for folder in sorted(chars_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        # 优先 yaml，回退 md
        yaml_file = folder / f"{folder.name}.yaml"
        md_file = folder / f"{folder.name}.md"
        content = ""
        name = folder.name

        if yaml_file.exists():
            text = yaml_file.read_text(encoding="utf-8")
            content = text
            # 从 yaml 提取 name 字段
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                    break
        elif md_file.exists():
            text = md_file.read_text(encoding="utf-8")
            content = text
            first_line = text.split("\n")[0].strip()
            if first_line.startswith("#"):
                raw = first_line.lstrip("#").strip()
                # "灵：角色索引" → "灵"
                name = raw.split("：")[0].split(":")[0].strip()
        else:
            continue

        # 优先从 yaml 字段判断角色，回退到内容关键词
        role = ""
        if yaml_file.exists():
            for line in text.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("role:") or line_stripped.startswith("角色:"):
                    rv = line_stripped.split(":", 1)[1].strip()
                    if rv in ("classmate", "同学", "陪读"):
                        role = "classmate"
                    elif rv in ("teacher", "老师"):
                        role = "teacher"
                    break
        if not role:
            is_classmate = ("陪读" in content and "同学" in content) or "classmate" in folder.name.lower()
            role = "classmate" if is_classmate else "teacher"

        has_tutoring = (folder / "supplement_tutoring.yaml").exists() or (folder / "supplement_tutoring.md").exists()

        characters[folder.name] = {
            "id": folder.name,
            "name": name,
            "role": role,
            "folder": str(folder.relative_to(PROJECT_ROOT)),
            "has_tutoring": has_tutoring,
        }

    return characters


def scan_courses():
    """扫描 courses/ 目录，返回 {id: {name, aliases, has_cards, has_km}} 的 dict。"""
    courses_dir = PROJECT_ROOT / "courses"
    cards_dir = PROJECT_ROOT / "card"
    if not courses_dir.exists():
        return {}

    courses = {}
    for folder in sorted(courses_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        name = folder.name
        aliases = []

        course_md = folder / "course.md"
        if course_md.exists():
            text = course_md.read_text(encoding="utf-8")
            nm = re.search(r"##\s+课程名称\s*\n\s*(.+)", text)
            if nm:
                name = nm.group(1).strip()
            alias_sec = re.search(r"##\s+课程别名\s*\n((?:\s*[-*]\s*.+\n?)*)", text)
            if alias_sec:
                for line in alias_sec.group(1).split("\n"):
                    a = line.strip().lstrip("-*").strip()
                    if a:
                        aliases.append(a)

        has_cards = (cards_dir / folder.name / "cards.md").exists()
        has_km = (folder / "knowledge_map_state.json").exists()

        courses[folder.name] = {
            "id": folder.name,
            "name": name,
            "aliases": aliases,
            "has_cards": has_cards,
            "has_km": has_km,
        }

    return courses


def compute_transitive_impact(node_id: str, nodes: dict, visited: set = None) -> int:
    """计算传递影响面：所有直接+间接后继节点数"""
    if visited is None:
        visited = set()
    if node_id in visited:
        return 0
    visited.add(node_id)

    node = nodes.get(node_id)
    if not node:
        return 0

    count = 0
    for nb in node.get("needed_by", []):
        if nb not in visited:
            count += 1 + compute_transitive_impact(nb, nodes, visited)
    return count


def concept_match(concept_name: str, text_list: list) -> bool:
    """检查概念名是否出现在文本列表中（关键词拆分模糊匹配，≥40%命中）"""
    keywords = concept_name.replace("与", " ").replace("和", " ").replace("的", " ").split()
    if not keywords:
        return False
    for text in text_list:
        matches = sum(1 for kw in keywords if kw in text)
        if matches / len(keywords) >= 0.4:
            return True
    return False
