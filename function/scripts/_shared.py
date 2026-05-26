"""
_shared.py —— 脚本共享模块

提供 map.py、web/knowledge_panel.py、recommend_node.py、after_class.py 共用的函数。
"""
import re
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# ── 位置定义 ─────────────────────────────────────────────────

LOCATIONS = {
    "gate": {
        "name": "校门口",
        "flavor": "灵在自习室，夏在图书馆，柠在家里",
        "desc": "",
        "actions": [
            {"key": "1", "label": "进去", "type": "navigate", "target": "classroom_door"},
        ],
    },
    "classroom_door": {
        "name": "走廊",
        "flavor": "教室、自习室、图书馆——还有一扇门通往柠家",
        "desc": "",
        "actions": [
            {"key": "1", "label": "去教室（三人）", "type": "navigate", "target": "classroom"},
            {"key": "2", "label": "去自习室（找灵）", "type": "navigate", "target": "study_room"},
            {"key": "3", "label": "去图书馆（找夏）", "type": "navigate", "target": "library"},
            {"key": "4", "label": "去柠家（找柠）", "type": "navigate", "target": "home"},
        ],
    },
    "classroom": {
        "name": "教室",
        "flavor": "灵和夏的笔记本摊在桌上，中间给你留了位置",
        "desc": "共学",
        "actions": [
            {"key": "1", "label": "选课程", "type": "select_course"},
            {"key": "2", "label": "开始共学", "type": "scene", "scene_id": "study",
             "needs_course": True, "teacher": "ling", "set_classmate": True},
            {"key": "3", "label": "开始复习", "type": "scene", "scene_id": "review",
             "needs_course": True, "teacher": "ling", "set_classmate": True},
        ],
    },
    "study_room": {
        "name": "自习室",
        "flavor": "灵一个人坐在靠窗的位置，荧光笔在指间转着圈",
        "desc": "和灵双人共学",
        "actions": [
            {"key": "1", "label": "选课程", "type": "select_course"},
            {"key": "2", "label": "开始共学", "type": "scene", "scene_id": "study",
             "needs_course": True, "teacher": "ling"},
            {"key": "3", "label": "开始复习", "type": "scene", "scene_id": "review",
             "needs_course": True, "teacher": "ling"},
        ],
    },
    "library": {
        "name": "图书馆",
        "flavor": "夏在靠窗的位置，围巾搭在椅背上，抬头看见你进来，眼睛亮了一下",
        "desc": "和夏双人共学",
        "actions": [
            {"key": "1", "label": "选课程", "type": "select_course"},
            {"key": "2", "label": "开始共学", "type": "scene", "scene_id": "study",
             "needs_course": True, "teacher": "xia"},
            {"key": "3", "label": "开始复习", "type": "scene", "scene_id": "review",
             "needs_course": True, "teacher": "xia"},
        ],
    },
    "home": {
        "name": "柠家",
        "flavor": "门虚掩着，里面传来笔尖戳纸的声音和一句压低了但还是很明显的'哈！'",
        "desc": "和柠双人共学",
        "actions": [
            {"key": "1", "label": "选课程", "type": "select_course"},
            {"key": "2", "label": "开始共学", "type": "scene", "scene_id": "study",
             "needs_course": True, "teacher": "ning"},
            {"key": "3", "label": "开始复习", "type": "scene", "scene_id": "review",
             "needs_course": True, "teacher": "ning"},
        ],
    },
}

NO_BACK_LOCATIONS = {"gate"}

# ── 运行时状态 ─────────────────────────────────────────────────

class AppState:
    """运行时状态，在内存中维护。"""
    def __init__(self):
        self.location = "gate"
        self.teacher = None       # 无默认值，必须通过菜单选择
        self.course = None        # course id
        self.classmate = None     # str: "ning" / "xia+ning" / "all" / None
        self.scene = None         # 由 scene 动作写入
        self.location_stack = []  # 面包屑导航


def load_state(no_state: bool = False, full: bool = False):
    """加载 map_state.json。默认仅恢复位置，full=True 时恢复全部。"""
    state = AppState()
    if no_state:
        return state

    state_path = SCRIPTS_DIR / "state" / "map_state.json"
    if not state_path.exists():
        return state

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        state.location = data.get("last_location", "gate")
        if full:
            state.teacher = data.get("last_teacher") or None
            state.course = data.get("last_course")
            cm = data.get("last_classmate", None)
            state.classmate = cm if cm else None
            state.scene = data.get("last_scene")
    except (json.JSONDecodeError, KeyError):
        pass

    return state


def save_state(state: AppState):
    """保存当前状态到 map_state.json。"""
    data = {
        "last_location": state.location,
        "last_teacher": state.teacher,
        "last_course": state.course,
        "last_classmate": state.classmate,
        "last_scene": state.scene,
        "version": 2,
    }
    state_path = SCRIPTS_DIR / "state" / "map_state.json"
    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_state(state: AppState, characters: dict):
    """验证持久化状态中的引用是否仍然有效。"""
    if state.teacher and state.teacher not in characters:
        state.teacher = None
    if state.location != "gate":
        if state.teacher is None and len(characters) > 0:
            if state.location != "library":
                state.location = "gate"


def action_available(action: dict, state: AppState, courses: dict):
    """检查动作是否可用。返回 (available: bool, reason: str)。"""
    if action.get("needs_course") and state.course is None:
        return False, "需要先选课程"
    if action.get("needs_cards") and state.course:
        course = courses.get(state.course, {})
        if not course.get("has_cards", False):
            return False, "该课程没有闪卡"
    return True, ""

# ── 课程扫描 ─────────────────────────────────────────────────


def scan_characters():
    """扫描 characters/ 目录，返回 {id: {name, role, folder}} 的 dict。

    每个角色目录需有一个 {folder.name}.md 或 {folder.name}.yaml 文件。
    优先读取 .yaml（name/id 字段），回退到 .md（首行标题）。
    """
    chars_dir = PROJECT_ROOT / "teacher" / "characters"
    if not chars_dir.exists():
        return {}

    characters = {}
    for folder in sorted(chars_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        # 优先 profile.yaml，回退 {name}.yaml，再回退 {name}.md
        yaml_file = folder / "profile.yaml"
        if not yaml_file.exists():
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

        # 从 yaml 读取 role 字段，直接使用原值；回退到内容推断
        role = ""
        if yaml_file.exists():
            for line in text.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith("role:") or line_stripped.startswith("角色:"):
                    rv = line_stripped.split(":", 1)[1].strip()
                    if rv:
                        role = rv
                    break
        if not role:
            role = "伙伴"

        characters[folder.name] = {
            "id": folder.name,
            "name": name,
            "role": role,
            "folder": str(folder.relative_to(PROJECT_ROOT)),
        }

    return characters


def scan_courses():
    """扫描 courses/ 目录，返回 {id: {name, aliases, has_cards, has_km}} 的 dict。"""
    courses_dir = PROJECT_ROOT / "courses"
    cards_dir = PROJECT_ROOT / "function" / "card"
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
