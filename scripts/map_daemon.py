"""
map_daemon.py —— 终端常驻导航菜单

纯标准库，无第三方依赖。在 VS Code 终端启动一次，全程复用。
用法：
    python scripts/map_daemon.py
    python scripts/map_daemon.py --no-state   # 全新开始
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent

from _shared import (
    LOCATIONS, NO_BACK_LOCATIONS, AppState,
    load_state, save_state, validate_state, write_scene_file,
    action_available, scan_characters, scan_courses,
)

# ── 终端工具 ─────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def divider(char="─", width=36):
    return char * width


def bold(text):
    """终端加粗（ANSI）"""
    return f"\033[1m{text}\033[0m"


# ── 子菜单 ────────────────────────────────────────────────────

def select_teacher(characters: dict):
    """显示伙伴列表，返回选中的 character id 或 None。"""
    partners = [(k, v) for k, v in characters.items()]
    if not partners:
        print("\n  没有可用的角色。")
        input("  按 Enter 返回...")
        return None
    if len(partners) == 1:
        print(f"\n  自动选择: {partners[0][1]['name']}")
        input("  按 Enter 继续...")
        return partners[0][0]

    clear()
    print()
    print(f"  {bold('选择伙伴')}")
    print(f"  {divider()}")
    for i, (tid, tdata) in enumerate(partners, 1):
        role = tdata.get("role", "")
        print(f"    {i}. {tdata['name']}  ({role})")
    print(f"  {divider()}")
    print(f"  [b] 返回")
    print()

    while True:
        choice = input("  > ").strip().lower()
        if choice == "b":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(partners):
                return partners[idx][0]
        except ValueError:
            pass
        print("  无效选择，重试。")


def select_course(courses: dict):
    """显示课程列表，返回选中的 course id 或 None。"""
    valid_courses = [(k, v) for k, v in courses.items()]

    clear()
    print()
    print(f"  {bold('选择课程')}")
    print(f"  {divider()}")
    if valid_courses:
        for i, (cid, cdata) in enumerate(valid_courses, 1):
            tags = ""
            if cdata.get("has_km"):
                tags += " [KM]"
            if cdata.get("has_cards"):
                tags += " [C]"
            print(f"    {i}. {cdata['name']}{tags}")
            if cdata.get("aliases"):
                print(f"       别名: {', '.join(cdata['aliases'])}")
    else:
        print("    courses/ 下还没有课程。")
    print(f"  {divider()}")
    print(f"  [0] 其他课程（手动输入）")
    print(f"  [b] 返回")
    print()

    while True:
        choice = input("  > ").strip().lower()
        if choice == "b":
            return None
        if choice == "0":
            print()
            custom = input("  请输入课程名: ").strip()
            return custom if custom else None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(valid_courses):
                return valid_courses[idx][0]
        except ValueError:
            pass
        print("  无效选择，重试。")


def select_classmate(characters: dict, teacher_id: str):
    """选择共学伙伴，返回 classmate 字符串或 None。

    返回格式: "ning" / "xia+ning" / "all" / None（不需要）
    """
    others = [(k, v) for k, v in characters.items() if k != teacher_id]
    if not others:
        print("\n  没有其他角色可选。")
        input("  按 Enter 继续...")
        return None

    clear()
    print()
    print(f"  {bold('选择共学伙伴')}")
    print(f"  {divider()}")
    for i, (cid, cdata) in enumerate(others, 1):
        role = cdata.get("role", "")
        print(f"    {i}. {cdata['name']}  ({role})")

    # 组合选项
    combo_start = len(others) + 1
    if len(others) >= 2:
        names = "+".join(cdata["name"] for _, cdata in others)
        print(f"    {combo_start}. {names}（全部）")
        combo_start += 1
    print(f"    {combo_start}. 全部")
    print(f"  {divider()}")
    print(f"  [b] 不需要伙伴")
    print()

    while True:
        choice = input("  > ").strip().lower()
        if choice == "b":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(others):
                return others[idx][0]
            all_start = len(others)
            if len(others) >= 2 and idx == all_start:
                return "+".join(cdata["id"] for _, cdata in others)
            if idx == all_start + (1 if len(others) >= 2 else 0):
                return "all"
        except ValueError:
            pass
        print("  无效选择，重试。")

def render(state: AppState, characters: dict, courses: dict):
    """渲染当前位置。"""
    loc = LOCATIONS.get(state.location)
    if not loc:
        state.location = "gate"
        return render(state, characters, courses)

    clear()

    # 位置标题
    print()
    print(f"  {bold(loc['name'])}")
    print(f"  {divider()}")
    if loc.get("flavor"):
        print(f"  {loc['flavor']}")
    if loc.get("desc"):
        print(f"  {loc['desc']}")
    print()

    # 动作按钮
    shown_keys = set()
    for action in loc["actions"]:
        if action.get("needs_course") and state.course is None:
            continue
        available, reason = action_available(action, state, courses)
        key = action["key"]
        shown_keys.add(key)

        if available:
            label = action["label"]
            if action["type"] == "select_course" and state.course is not None:
                label = "换课程"
            print(f"  [{key}] {label}")
        else:
            print(f"  [{key}] {label}（{reason}）")

    # 系统动作
    print()
    if state.location not in NO_BACK_LOCATIONS:
        print(f"  [b] 返回", end="  ")
    print(f"  [q] 放学")

    # 状态栏
    print()
    loc_desc = loc.get("desc", "")
    partner_str = loc_desc
    status_parts = [partner_str] if partner_str else []
    if state.course and state.course in courses:
        status_parts.append(courses[state.course]["name"])
    elif state.course:
        status_parts.append(state.course)
    status = "  |  ".join(status_parts)
    print(f"  {divider()}")
    print(f"  {status}")
    print(f"  {divider()}")
    print()

    return shown_keys


def main():
    no_state = "--no-state" in sys.argv
    characters = scan_characters()
    courses = scan_courses()

    state = load_state(no_state=no_state)
    validate_state(state, characters)

    characters_list = list(characters.values())
    if not characters_list:
        print("characters/ 目录下没有角色。按 Enter 退出...")
        input()
        sys.exit(1)

    while True:
        shown_keys = render(state, characters, courses)
        loc = LOCATIONS.get(state.location, {})

        # 构建有效按键
        valid_keys = {"q"}
        if state.location not in NO_BACK_LOCATIONS:
            valid_keys.add("b")
        for action in loc.get("actions", []):
            valid_keys.add(action["key"])

        choice = input("  > ").strip().lower()
        if choice not in valid_keys:
            continue

        if choice == "q":
            state.location = "gate"
            state.location_stack = []
            save_state(state)
            scene_path = SCRIPT_DIR / "current_scene.json"
            if scene_path.exists():
                scene_path.unlink()
            print("\n  放学了，明天见！")
            sys.exit(0)

        if choice == "b":
            if state.location_stack:
                state.location = state.location_stack.pop()
            elif state.location != "gate":
                state.location = "gate"
            save_state(state)
            continue

        # 匹配动作
        for action in loc.get("actions", []):
            if action["key"] != choice:
                continue

            atype = action["type"]

            if atype == "navigate":
                state.location_stack.append(state.location)
                state.location = action["target"]
                save_state(state)
                break

            elif atype == "select_teacher":
                tid = select_teacher(characters)
                if tid:
                    state.teacher = tid
                    state.location_stack.append(state.location)
                    state.location = "classroom_door"
                    save_state(state)
                break

            elif atype == "select_course":
                cid = select_course(courses)
                if cid is not None:
                    state.course = cid
                    save_state(state)
                break

            elif atype == "scene":
                available, reason = action_available(action, state, courses)
                if not available:
                    print(f"\n  {reason}")
                    input("  按 Enter 继续...")
                    break

                if action.get("teacher"):
                    state.teacher = action["teacher"]

                # 同学选择
                if action.get("set_classmate"):
                    state.classmate = select_classmate(characters, state.teacher)
                else:
                    state.classmate = None

                write_scene_file(action["scene_id"], state, characters, courses)
                save_state(state)

                scene_id = action["scene_id"]
                partner_name = characters.get(state.teacher, {}).get("name", "?")
                course_name = courses.get(state.course, {}).get("name", "（未选）")

                # classmate 展示
                classmate_str = ""
                if state.classmate:
                    if state.classmate == "all":
                        classmate_str = " + 全部伙伴"
                    elif "+" in state.classmate:
                        names = []
                        for cid in state.classmate.split("+"):
                            names.append(characters.get(cid, {}).get("name", cid))
                        classmate_str = " + " + " + ".join(names)
                    else:
                        name = characters.get(state.classmate, {}).get("name", state.classmate)
                        classmate_str = f" + {name}"

                print(f"\n  场景已就绪: {scene_id}")
                print(f"  伙伴: {partner_name}{classmate_str}  |  课程: {course_name}")
                print(f"  切回 Claude 面板说「上课」即可。")
                print(f"  （可继续在此窗口重新选择）")
                print()
                input("  按 Enter 继续...")
                break

            elif atype == "script":
                print(f"\n  脚本功能请在终端直接运行。")
                input("  按 Enter 继续...")
                break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  已退出。")
