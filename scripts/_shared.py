"""
_shared.py —— 脚本共享模块

提供 map.py、knowledge_panel.py、recommend_node.py、after_class.py 共用的函数。
"""
import re
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# ── 位置定义 ─────────────────────────────────────────────────

LOCATIONS = {
    "gate": {
        "name": "校门口",
        "flavor": "公告栏上贴着今天的排课",
        "desc": "今天哪位老师来上课？",
        "actions": [
            {"key": "1", "label": "灵", "type": "select_teacher", "teacher": "ling"},
        ],
    },
    "classroom_door": {
        "name": "教室门口",
        "flavor": "走廊尽头的教室亮着灯",
        "desc": "",
        "actions": [
            {"key": "1", "label": "去教室（上课）", "type": "navigate", "target": "classroom"},
            {"key": "2", "label": "去自习室（复习）", "type": "navigate", "target": "study_room"},
            {"key": "3", "label": "去找夏", "type": "navigate", "target": "library"},
        ],
    },
    "classroom": {
        "name": "教室",
        "flavor": "灵在讲台前翻着备课本",
        "desc": "",
        "actions": [
            {"key": "1", "label": "选课程", "type": "select_course"},
            {"key": "2", "label": "正常上课", "type": "scene", "scene_id": "teaching",
             "needs_course": True},
            {"key": "3", "label": "课后辅导", "type": "scene", "scene_id": "tutoring",
             "needs_course": True},
            {"key": "4", "label": "和夏一起上课", "type": "scene", "scene_id": "teaching",
             "needs_course": True, "set_classmate": True},
        ],
    },
    "study_room": {
        "name": "自习室",
        "flavor": "自习室亮着暖黄的灯，靠窗的座位空着",
        "desc": "",
        "actions": [
            {"key": "1", "label": "选课程", "type": "select_course"},
            {"key": "2", "label": "老师带着复习", "type": "scene", "scene_id": "review_with_teacher",
             "needs_course": True},
        ],
    },
    "library": {
        "name": "图书馆",
        "flavor": "靠窗的位置，夏正在翻笔记本",
        "desc": "",
        "actions": [
            {"key": "1", "label": "闲聊", "type": "scene", "scene_id": "chat"},
            {"key": "2", "label": "学习", "type": "study_submenu"},
        ],
    },
}

NO_BACK_LOCATIONS = {"gate"}

# ── 运行时状态 ─────────────────────────────────────────────────

class AppState:
    """运行时状态，在内存中维护。"""
    def __init__(self):
        self.location = "gate"
        self.teacher = None       # teacher id
        self.course = None        # course id
        self.classmate = False
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
            state.teacher = data.get("last_teacher")
            state.course = data.get("last_course")
            state.classmate = data.get("last_classmate", False)
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
        "version": 1,
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


def write_scene_file(scene_id: str, state: AppState, characters: dict, courses: dict):
    """写入 current_scene.json，供 AI 读取启动教学场景。"""
    teacher_name = ""
    if state.teacher and state.teacher in characters:
        teacher_name = characters[state.teacher]["name"]

    course_name = ""
    if state.course:
        if state.course in courses:
            course_name = courses[state.course]["name"]
        else:
            course_name = state.course

    data = {
        "scene": scene_id,
        "teacher": state.teacher,
        "teacher_name": teacher_name,
        "course": state.course,
        "course_name": course_name,
        "classmate": state.classmate,
        "timestamp": datetime.now().isoformat(),
    }

    scene_path = SCRIPTS_DIR / "current_scene.json"
    scene_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
