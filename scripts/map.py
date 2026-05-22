"""
map.py —— 交互式地图导航

苏格拉底式教学系统的终端导航层。数字键秒切场景，
AI 只在进入教学/角色互动场景时才接管。

用法：
    python scripts/map.py
    python scripts/map.py --start gate
    python scripts/map.py --course uv --start classroom
    python scripts/map.py --no-state
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# ── UTF-8 终端修复 ──────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Rich 依赖检查 ────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich.box import ROUNDED
except ImportError:
    print("需要安装 rich 库：pip install rich")
    sys.exit(1)

console = Console()

# ── 项目根目录 ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
from _shared import scan_characters, scan_courses

# ── 工具函数 ─────────────────────────────────────────────────

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def get_key(valid_keys: set) -> str:
    """阻塞等待用户按下合法按键（仅 Windows）。"""
    import msvcrt as m
    while True:
        key = m.getch().decode("utf-8", errors="ignore").lower()
        if key in valid_keys:
            return key


def wait_key():
    """等待任意按键。"""
    import msvcrt as m
    m.getch()


def bell():
    """响铃提示（非法按键反馈）。"""
    import msvcrt as m
    try:
        # 写入 BEL 字符
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


# ── 扫描函数 ─────────────────────────────────────────────────

# ── 全局状态 ─────────────────────────────────────────────────

class AppState:
    """运行时状态，在内存中维护。"""
    def __init__(self):
        self.location = "gate"
        self.teacher = None       # teacher id
        self.course = None        # course id
        self.classmate = False
        self.location_stack = []  # 面包屑导航


# ── 位置定义 ─────────────────────────────────────────────────

LOCATIONS = {
    "gate": {
        "name": "校门口",
        "flavor": "公告栏上贴着今天的排课",
        "desc": "今天哪位老师来上课？",
        "actions": [
            {"key": "1", "label": "灵", "type": "select_teacher"},
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
            {"key": "3", "label": "自己刷闪卡", "type": "script",
             "script_cmd": ["python", "card/review.py", "{course_id}"],
             "needs_course": True, "needs_cards": True},
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

# 不需要返回按钮的位置（已经是顶层）
NO_BACK_LOCATIONS = {"gate"}


# ── 状态持久化 ───────────────────────────────────────────────

def load_state(args, full: bool = False) -> AppState:
    """加载 map_state.json。默认仅恢复位置，full=True 时恢复全部（供 --go 使用）。"""
    state = AppState()
    if args.no_state:
        return state

    state_path = SCRIPTS_DIR / "map_state.json"
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
    state_path = SCRIPTS_DIR / "map_state.json"
    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_state(state: AppState, characters: dict, courses: dict):
    """验证持久化状态中的引用是否仍然有效。"""
    if state.teacher and state.teacher not in characters:
        state.teacher = None
    # 不清理不在 courses/ 中的课程名——可能是用户通过"其他课程"输入的自定义名称
    # 这些课程将由 AI 从 course_inbox/ 匹配并自动建课
    # 如果不在 gate 且没有老师，回退到 gate
    if state.location != "gate":
        if state.teacher is None and len(characters) > 0:
            # 有老师可选但没选 → 回 gate 选老师
            if state.location != "library":  # 图书馆不需要老师
                state.location = "gate"


# ── Scene 交接 ───────────────────────────────────────────────

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
            course_name = state.course  # 自定义课程名（来自"其他课程"输入）

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


# ── 快捷路径 ─────────────────────────────────────────────────

def go_quick(args, state: AppState, characters: dict, courses: dict):
    """--go 快速续课：跳过导航，直接用上次状态写 scene 文件。"""
    # 检查是否有历史记录
    state_path = SCRIPTS_DIR / "map_state.json"
    if not state_path.exists():
        console.print("\n  [bold bright_red]还没有上课记录。[/bold bright_red]")
        console.print("  [#888888]请先运行 map.py 选择场景。[/#888888]\n")
        sys.exit(1)

    # 验证状态引用
    state = load_state(args, full=True)
    validate_state(state, characters, courses)

    # 快捷路径允许覆盖 course
    if args.course:
        state.course = args.course

    if not state.teacher:
        console.print("\n  [bold bright_red]还没有选择老师。[/bold bright_red]")
        console.print("  [#888888]请先运行 map.py 进入校门口选择老师。[/#888888]\n")
        sys.exit(1)

    # 检查位置是否可进入教学场景
    loc = LOCATIONS.get(state.location, {})
    scene_actions = [a for a in loc.get("actions", []) if a["type"] == "scene"]

    if not scene_actions:
        loc_name = loc.get("name", state.location)
        console.print(f"\n  [bold bright_red]当前位置（{loc_name}）无法直接进入教学场景。[/bold bright_red]")
        console.print("  [#888888]请先运行 map.py 手动选择。[/#888888]\n")
        sys.exit(1)

    # 选择 scene 动作
    scene_action = scene_actions[0]  # 默认取第一个
    if args.mode:
        for a in scene_actions:
            if a.get("scene_id") == args.mode:
                scene_action = a
                break
        else:
            valid_modes = ", ".join(a.get("scene_id", "") for a in scene_actions)
            console.print(f"\n  [bold bright_red]当前场景不支持 --mode {args.mode}。[/bold bright_red]")
            console.print(f"  [#888888]可用: {valid_modes}[/#888888]\n")
            sys.exit(1)

    # 检查可用性
    available, reason = action_available(scene_action, state, courses)
    if not available:
        console.print(f"\n  [bold bright_red]{reason}[/bold bright_red]\n")
        sys.exit(1)

    # 写 scene 文件
    write_scene_file(scene_action["scene_id"], state, characters, courses)
    save_state(state)

    teacher_name = characters.get(state.teacher, {}).get("name", "?")
    course_name = courses.get(state.course, {}).get("name", "（未选）")
    console.print(f"\n  [bold bright_cyan]快速续课...[/bold bright_cyan]")
    console.print(f"  [#888888]老师: {teacher_name}[/#888888]")
    console.print(f"  [#888888]场景: {scene_action['scene_id']}[/#888888]")
    console.print(f"  [#888888]课程: {course_name}[/#888888]\n")
    sys.exit(0)


def start_server(port: int = 8765) -> tuple:
    """启动知识地图面板子进程。返回 (proc, url)。"""
    import socket
    server_script = SCRIPTS_DIR / "knowledge_panel.py"

    # 找可用端口
    max_tries = 5
    actual_port = port
    for offset in range(max_tries):
        test_port = port + offset
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", test_port))
            sock.close()
            actual_port = test_port
            break
        except OSError:
            sock.close()
            if offset == max_tries - 1:
                raise RuntimeError(f"端口 {port}-{port + max_tries - 1} 均被占用")

    proc = subprocess.Popen(
        [sys.executable, str(server_script), "--port", str(actual_port), "--no-browser"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{actual_port}"
    return proc, url


# ── Subprocess 调用 ──────────────────────────────────────────

def run_script(cmd_template: list, state: AppState) -> bool:
    """运行子进程脚本，返回 True 表示成功。"""
    cmd = []
    for part in cmd_template:
        cmd.append(part.format(course_id=state.course or "", teacher=state.teacher or ""))

    console.print(f"\n  [#888888]启动: {' '.join(cmd)}[/#888888]")
    console.print("  [#888888]脚本结束后将返回地图...[/#888888]\n")

    try:
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        return result.returncode == 0
    except FileNotFoundError:
        console.print(f"\n  [bold bright_red]错误: 找不到 Python 解释器[/bold bright_red]")
        return False
    except Exception as e:
        console.print(f"\n  [bold bright_red]脚本运行出错: {e}[/bold bright_red]")
        return False


# ── UI 渲染 ──────────────────────────────────────────────────

def action_available(action: dict, state: AppState, courses: dict) -> tuple:
    """检查动作是否可用。返回 (available: bool, reason: str)。"""
    if action.get("needs_course") and state.course is None:
        return False, "需要先选课程"
    if action.get("needs_cards") and state.course:
        course = courses.get(state.course, {})
        if not course.get("has_cards", False):
            return False, "该课程没有闪卡"
    return True, ""


def render_location(state: AppState, characters: dict, courses: dict):
    """渲染当前位置的 UI。"""
    loc = LOCATIONS.get(state.location)
    if not loc:
        console.print(f"[bold bright_red]未知位置: {state.location}[/bold bright_red]")
        state.location = "gate"
        return render_location(state, characters, courses)

    clear_screen()

    # ── 顶栏：位置名 ──
    header_text = Text(loc["name"], style="bold bright_cyan")
    header = Panel(Align.center(header_text), box=ROUNDED, border_style="bright_blue",
                   padding=(0, 4))
    console.print(header)

    # ── 氛围文字 ──
    if loc.get("flavor"):
        console.print(f"  [italic #aaaaaa]{loc['flavor']}[/italic #aaaaaa]")

    # ── 描述文字 ──
    if loc.get("desc"):
        console.print(f"\n  [#ffffff]{loc['desc']}[/#ffffff]")

    # ── 动作按钮 ──
    console.print("")
    shown_keys = set()

    for action in loc["actions"]:
        # 未选课时隐藏需要课程的动作
        if action.get("needs_course") and state.course is None:
            continue

        available, reason = action_available(action, state, courses)
        key = action["key"]
        shown_keys.add(key)

        # 已选课时"选课程"→"换课程"
        label = action["label"]
        if action["type"] == "select_course" and state.course is not None:
            label = "换课程"

        if available:
            # 根据类型加不同颜色
            label_color = "#ffffff"
            key_bg = "bright_green"
            key_fg = "#1a1a2e"
            if action["type"] == "scene":
                key_bg = "bright_cyan"
            elif action["type"] == "script":
                key_bg = "bright_yellow"
                key_fg = "#1a1a2e"
            elif action["type"] == "study_submenu":
                key_bg = "bright_magenta"

            console.print(
                f"  [[{key_fg} on {key_bg}] [bold] {key} [/bold] [/]] "
                f"[{label_color}]{label}[/{label_color}]"
            )
        else:
            console.print(f"  [#555555] [{key}] {label}（{reason}）[/#555555]")

    # ── 系统动作（返回/退出） ──
    console.print("")
    shown_keys.add("b")
    shown_keys.add("q")
    back_visible = state.location not in NO_BACK_LOCATIONS
    if back_visible:
        console.print(f"  [#888888] [b] 返回[/#888888]", end="")
    console.print(f"  [#888888] [q] 放学[/#888888]")

    # ── 底部状态栏 ──
    console.print("")
    status_parts = []
    if state.teacher and state.teacher in characters:
        status_parts.append(characters[state.teacher]["name"])
    if state.course and state.course in courses:
        status_parts.append(courses[state.course]["name"])
    if state.classmate:
        status_parts.append("+夏")
    status = "  |  ".join(status_parts) if status_parts else "  -"
    console.print(f"  [#555555]当前: {status}[/#555555]")


def show_teacher_submenu(characters: dict) -> str:
    """显示老师选择子菜单，返回选中的 teacher id 或 None。"""
    teachers = [(k, v) for k, v in characters.items() if v["role"] == "teacher"]
    if not teachers:
        console.print("\n  [bold bright_red]没有可用的老师。[/bold bright_red]")
        wait_key()
        return None
    if len(teachers) == 1:
        console.print(f"\n  [#888888]自动选择: [bold]{teachers[0][1]['name']}[/bold][/#888888]")
        wait_key()
        return teachers[0][0]

    # 多老师选择
    clear_screen()
    title = Panel(
        Align.center(Text("选择老师", style="bold bright_cyan")),
        box=ROUNDED, border_style="bright_blue", padding=(0, 4),
    )
    console.print(title)
    console.print("")

    for i, (tid, tdata) in enumerate(teachers, 1):
        console.print(f"  [[bright_green] [bold]{i}[/bold] [/bright_green]] "
                      f"[bold]{tdata['name']}[/bold]")

    console.print(f"\n  [#888888] [b] 返回[/#888888]")

    valid_keys = {str(i) for i in range(1, len(teachers) + 1)} | {"b"}
    key = get_key(valid_keys)
    if key == "b":
        return None

    idx = int(key) - 1
    return teachers[idx][0]


def show_course_submenu(courses: dict) -> str:
    """显示课程选择子菜单，返回选中的 course id 或 None。"""
    valid_courses = [(k, v) for k, v in courses.items()]

    clear_screen()
    title = Panel(
        Align.center(Text("选择课程", style="bold bright_cyan")),
        box=ROUNDED, border_style="bright_blue", padding=(0, 4),
    )
    console.print(title)
    console.print("")

    if valid_courses:
        for i, (cid, cdata) in enumerate(valid_courses, 1):
            tags = []
            if cdata.get("has_km"):
                tags.append("[bright_cyan]KM[/bright_cyan]")
            if cdata.get("has_cards"):
                tags.append("[bright_yellow]C[/bright_yellow]")
            tag_str = f" {' '.join(tags)}" if tags else ""
            console.print(
                f"  [[bright_green] [bold]{i}[/bold] [/bright_green]] "
                f"[bold]{cdata['name']}[/bold]{tag_str}"
            )
            if cdata.get("aliases"):
                alias_str = ", ".join(cdata["aliases"])
                console.print(f"       [#888888]别名: {alias_str}[/#888888]")
    else:
        console.print("  [#888888]courses/ 下还没有课程。[/#888888]")
        console.print("  [#888888]可以直接输入课程名，AI 助手会从 course_inbox/ 建课。[/#888888]")

    console.print("")
    console.print(
        f"  [[bright_green] [bold]0[/bold] [/bright_green]] "
        f"[#ffffff]其他课程（手动输入课程名）[/#ffffff]"
    )
    console.print(f"  [#888888] [b] 返回[/#888888]")

    valid_keys = {str(i) for i in range(0, len(valid_courses) + 1)} | {"b"}
    key = get_key(valid_keys)
    if key == "b":
        return None
    if key == "0":
        console.print("\n  [#ffffff]请输入课程名:[/#ffffff] ", end="")
        custom = input().strip()
        return custom if custom else None

    idx = int(key) - 1
    return valid_courses[idx][0]


def show_study_submenu() -> bool:
    """显示「和夏学习」子菜单。返回 True 表示选择了已实装的功能。"""
    clear_screen()
    title = Panel(
        Align.center(Text("和夏一起学习", style="bold bright_cyan")),
        box=ROUNDED, border_style="bright_blue", padding=(0, 4),
    )
    console.print(title)
    console.print("")
    console.print("  [#888888]选一个学习方式：[/#888888]")
    console.print("")

    # 占位功能列表
    items = [
        ("1", "费曼模式", "你给夏讲解概念，她负责提问和挑漏洞"),
        ("2", "互相出题", "轮流考对方，看谁先卡住"),
    ]

    for key, label, desc in items:
        console.print(
            f"  [[#555555] [bold]{key}[/bold] [/]] "
            f"[#555555]{label}[/#555555]  [#444444]— {desc}[/#444444]"
        )

    console.print("")
    console.print("  [#888888] [b] 返回[/#888888]")

    valid_keys = {"1", "2", "b"}
    key = get_key(valid_keys)

    if key == "b":
        return False

    # 所有功能暂未开放
    console.print("\n  [#888888]这个功能还在准备中，很快就能用了。[/#888888]")
    console.print("  [#888888]按任意键返回...[/#888888]")
    wait_key()
    return False


# ── 动作分发 ─────────────────────────────────────────────────

def dispatch_action(key: str, state: AppState, characters: dict, courses: dict) -> str:
    """
    分发按键到对应动作。返回值：
    - "continue" — 已处理，继续循环
    - "exit" — 退出脚本
    - "scene:<scene_id>" — 触发教学场景后退出
    """
    loc = LOCATIONS.get(state.location)
    if not loc:
        return "continue"

    # 处理系统动作
    if key == "q":
        save_state(state)
        scene_path = SCRIPTS_DIR / "current_scene.json"
        if scene_path.exists():
            scene_path.unlink()
        console.print("\n  [bright_yellow]放学了，明天见！[/bright_yellow]")
        return "exit"

    if key == "b":
        if state.location_stack:
            state.location = state.location_stack.pop()
        elif state.location != "gate":
            state.location = "gate"
        return "continue"

    # 匹配位置动作
    for action in loc["actions"]:
        if action["key"] != key:
            continue

        atype = action["type"]

        # ── navigate ──
        if atype == "navigate":
            state.location_stack.append(state.location)
            state.location = action["target"]
            return "continue"

        # ── select_teacher ──
        if atype == "select_teacher":
            tid = show_teacher_submenu(characters)
            if tid:
                state.teacher = tid
                state.location_stack.append(state.location)
                state.location = "classroom_door"
            return "continue"

        # ── select_course ──
        if atype == "select_course":
            cid = show_course_submenu(courses)
            if cid is not None:
                state.course = cid
            return "continue"

        # ── study_submenu ──
        if atype == "study_submenu":
            show_study_submenu()
            return "continue"

        # ── scene ──
        if atype == "scene":
            available, reason = action_available(action, state, courses)
            if not available:
                console.print(f"\n  [bold bright_red]{reason}[/bold bright_red]")
                wait_key()
                return "continue"

            # 自动设置 classmate（如"和夏一起上课"）
            if action.get("set_classmate"):
                state.classmate = True

            write_scene_file(action["scene_id"], state, characters, courses)
            save_state(state)
            scene_id = action["scene_id"]
            teacher_name = characters.get(state.teacher, {}).get("name", "?")
            course_name = courses.get(state.course, {}).get("name", "（未选）")
            console.print(f"\n  [bold bright_cyan]正在进入教学场景...[/bold bright_cyan]")
            console.print(f"  [#888888]老师: {teacher_name}[/#888888]")
            console.print(f"  [#888888]场景: {scene_id}[/#888888]")
            console.print(f"  [#888888]课程: {course_name}[/#888888]")
            return f"scene:{scene_id}"

        # ── script ──
        if atype == "script":
            available, reason = action_available(action, state, courses)
            if not available:
                console.print(f"\n  [bold bright_red]{reason}[/bold bright_red]")
                wait_key()
                return "continue"

            success = run_script(action["script_cmd"], state)
            if not success:
                console.print("\n  [bold bright_red]脚本执行失败。[/bold bright_red]")
            console.print("\n  [#888888]按任意键返回地图...[/#888888]")
            wait_key()
            return "continue"

    # 未匹配到动作
    bell()
    return "continue"


# ── CLI 参数 ─────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="苏格拉底式教学系统 - 交互式地图导航",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/map.py                      从上次位置开始
  python scripts/map.py --start gate         从校门口开始
  python scripts/map.py --course uv          预选课程
  python scripts/map.py --no-state           全新开始，忽略记忆
        """,
    )
    parser.add_argument(
        "--start", metavar="LOCATION",
        choices=["gate", "classroom_door", "classroom", "study_room", "library"],
        help="起始位置（默认: 上次位置）",
    )
    parser.add_argument(
        "--teacher", metavar="TEACHER_ID",
        help="预选老师（characters/ 下的文件夹名）",
    )
    parser.add_argument(
        "--course", metavar="COURSE_ID",
        help="预选课程（courses/ 下的文件夹名）",
    )
    parser.add_argument(
        "--classmate", action="store_true",
        help="启用同学陪读模式（夏）",
    )
    parser.add_argument(
        "--no-state", action="store_true",
        help="不加载 map_state.json，从校门口开始",
    )
    parser.add_argument(
        "--go", action="store_true",
        help="快速续课：跳过导航，直接用上次状态进入教学场景",
    )
    parser.add_argument(
        "--mode", metavar="SCENE",
        choices=["teaching", "tutoring", "review_with_teacher", "chat", "study_together"],
        help="配合 --go 使用，指定教学场景类型",
    )
    parser.add_argument(
        "--server", action="store_true",
        help="同时启动知识地图面板（HTTP 服务器在后台线程）",
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="知识地图面板端口（默认 8765，配合 --server 使用）",
    )
    return parser.parse_args()


# ── 主循环 ───────────────────────────────────────────────────

def main():
    args = parse_args()

    # 扫描角色和课程
    characters = scan_characters()
    courses = scan_courses()

    # ── --server 后台知识地图面板（在 --go 前启动，确保组合使用时存活）──
    _server_proc = None
    if args.server:
        try:
            _server_proc, server_url = start_server(args.port)
            console.print(f"  [#888888]知识地图面板: {server_url}[/#888888]")
        except (OSError, RuntimeError) as e:
            console.print(f"  [bold bright_red]无法启动面板: {e}[/bold bright_red]")

    # ── 清理残留 scene 文件，防止干扰新会话 ──
    scene_path = SCRIPTS_DIR / "current_scene.json"
    if scene_path.exists():
        scene_path.unlink()

    # ── --go 快捷路径：跳过导航直接进入教学场景 ──
    if args.go:
        state = load_state(args)
        if args.course:
            state.course = args.course
        go_quick(args, state, characters, courses)  # 内部调用 sys.exit

    # ── 正常流程：加载持久化状态 ──
    state = load_state(args)

    # CLI 参数覆盖
    if args.teacher:
        state.teacher = args.teacher
    if args.course:
        state.course = args.course
    if args.start:
        state.location = args.start
        state.location_stack = []  # 手动指定位置时清空导航栈
    if args.classmate:
        state.classmate = True

    # 验证状态引用
    validate_state(state, characters, courses)

    # 如果没有老师可选，报错退出
    teachers = [v for v in characters.values() if v["role"] == "teacher"]
    if not teachers:
        console.print(Panel(
            Align.center(Text("characters/ 目录下没有有效的老师角色。\n"
                              "请先在 characters/<角色名>/ 下创建角色文件。",
                              style="bold bright_red")),
            box=ROUNDED, border_style="bright_red", padding=(1, 3),
        ))
        console.print("\n按任意键退出...")
        wait_key()
        sys.exit(1)

    # 主循环
    try:
        while True:
            render_location(state, characters, courses)

            # 收集当前可用按键
            loc = LOCATIONS.get(state.location, {})
            valid_keys = {"q"}
            if state.location not in NO_BACK_LOCATIONS:
                valid_keys.add("b")
            for action in loc.get("actions", []):
                valid_keys.add(action["key"])

            key = get_key(valid_keys)
            result = dispatch_action(key, state, characters, courses)

            if result == "exit":
                break
            if result.startswith("scene:"):
                break  # 交给 AI

    except KeyboardInterrupt:
        console.print("\n\n  [bright_yellow]已取消。[/bright_yellow]")


if __name__ == "__main__":
    main()
