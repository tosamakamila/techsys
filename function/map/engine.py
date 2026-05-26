"""
map.py —— 命令行入口

导航菜单已迁移至 map_daemon.py（终端常驻）。
本脚本仅处理快捷路径和知识面板。

用法：
    python function/map/engine.py --go --stdout                    续课（捕获 stdout JSON）
    python function/map/engine.py --go --stdout --teacher ling     切老师 + 续课
    python function/map/engine.py --go --stdout --course uv        切课程 + 续课
    python function/map/engine.py --go --stdout --location study   切位置 + 续课
    python function/map/engine.py --go --mode review --stdout      复习
    python function/map/engine.py --go --server                    续课 + 启动面板
    python function/map/engine.py --server                         仅启动面板
"""

import sys
import json
import argparse
import subprocess
import socket
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent.parent

from _shared import (
    LOCATIONS, AppState,
    load_state, save_state, validate_state,
    action_available, scan_characters, scan_courses,
)


# ── 知识面板 ─────────────────────────────────────────────

def start_server(port: int = 8765):
    """启动知识地图面板子进程。返回 (proc, url)。"""
    server_script = ROOT / "web" / "knowledge_panel.py"

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


# ── 快捷路径 ─────────────────────────────────────────────

def go_quick(args, characters: dict, courses: dict):
    """--go 快速续课：读取状态 + 参数覆盖 → 输出 scene JSON 或写文件。"""
    state_path = ROOT / "function" / "state" / "map_state.json"

    # 首次使用 + 提供了参数 → 自动创建状态
    if not state_path.exists():
        if args.teacher:
            state = AppState()
            state.teacher = args.teacher
            state.location = "study_room" if args.mode == "review" else "classroom"
            if args.course:
                state.course = args.course
            save_state(state)
        else:
            print("错误：还没有上课记录。请先指定老师，例如「上课 ling」。", file=sys.stderr)
            sys.exit(1)
    else:
        state = load_state(no_state=False, full=True)

    validate_state(state, characters)

    # CLI 参数覆盖
    if args.teacher:
        state.teacher = args.teacher
    if args.course:
        state.course = args.course
    if hasattr(args, 'location') and args.location:
        state.location = args.location

    if not state.teacher:
        print("错误：还没有选择老师。", file=sys.stderr)
        sys.exit(1)

    # 自动导航到支持 target_mode 的位置
    def _find_scene_actions(loc_key):
        loc = LOCATIONS.get(loc_key, {})
        return [a for a in loc.get("actions", []) if a["type"] == "scene"]

    scene_actions = _find_scene_actions(state.location)
    target_mode = args.mode or "study"

    if not any(a.get("scene_id") == target_mode for a in scene_actions):
        for loc_key in LOCATIONS:
            candidates = _find_scene_actions(loc_key)
            if any(a.get("scene_id") == target_mode for a in candidates):
                state.location = loc_key
                scene_actions = candidates
                break

    # 选择 scene 动作
    scene_action = scene_actions[0]
    if args.mode:
        for a in scene_actions:
            if a.get("scene_id") == args.mode:
                scene_action = a
                break
        else:
            valid_modes = ", ".join(a.get("scene_id", "") for a in scene_actions)
            print(f"错误：当前场景不支持 --mode {args.mode}。可用: {valid_modes}", file=sys.stderr)
            sys.exit(1)

    available, reason = action_available(scene_action, state, courses)
    if not available:
        print(f"错误：{reason}", file=sys.stderr)
        sys.exit(1)

    teacher_name = characters.get(state.teacher, {}).get("name", "?")
    course_name = courses.get(state.course, {}).get("name", "（未选）")

    scene_data = {
        "scene": scene_action["scene_id"],
        "teacher": state.teacher,
        "teacher_name": teacher_name,
        "course": state.course,
        "course_name": course_name,
        "classmate": state.classmate,
    }

    if args.stdout:
        save_state(state)
        print(json.dumps(scene_data, ensure_ascii=False))
        sys.exit(0)

    save_state(state)

    print(f"\n  快速续课...")
    print(f"  老师: {teacher_name}")
    print(f"  场景: {scene_action['scene_id']}")
    print(f"  课程: {course_name}\n")
    sys.exit(0)


# ── CLI 参数 ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="苏格拉底式教学系统 - 命令行入口")
    parser.add_argument("--teacher", metavar="TEACHER_ID", help="预选老师")
    parser.add_argument("--course", metavar="COURSE_ID", help="预选课程")
    parser.add_argument("--location", metavar="LOCATION", help="预选位置")
    parser.add_argument("--classmate", action="store_true", help="已废弃：共学模式下夏始终在")
    parser.add_argument("--no-state", action="store_true", help="不加载 map_state.json")
    parser.add_argument("--go", action="store_true", help="快速续课")
    parser.add_argument("--mode", choices=["study", "review", "chat"], help="共学场景类型")
    parser.add_argument("--stdout", action="store_true", help="输出 scene JSON 到 stdout")
    parser.add_argument("--server", action="store_true", help="启动知识地图面板")
    parser.add_argument("--port", type=int, default=8765, help="知识面板端口")
    return parser.parse_args()


# ── 主入口 ───────────────────────────────────────────────

def main():
    args = parse_args()
    characters = scan_characters()
    courses = scan_courses()

    if args.server:
        try:
            _server_proc, url = start_server(args.port)
            print(f"知识地图面板: {url}")
        except (OSError, RuntimeError) as e:
            print(f"无法启动面板: {e}", file=sys.stderr)

    if args.go:
        go_quick(args, characters, courses)

    if not args.server:
        print("用法：")
        print("  python function/map/engine.py --go --stdout          续课")
        print("  python function/map/engine.py --go --stdout --teacher ling --course 动物生理学")
        print("  python function/map/engine.py --server                启动知识面板")
        print("  python function/map/daemon.py                  终端导航菜单")


if __name__ == "__main__":
    main()
