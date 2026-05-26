"""
after_class.py —— 下课后统一更新

合并 advance_reading.py + update_knowledge_map.py，一个命令完成所有课后写入。

用法：
    # 正课推进：更新 reading_plan + 知识地图
    python function/classroom/after_class.py courses/<课程名> --fragment L002a --status 已上课 --next L002b

    # 复习课修复（不推进位置）
    python function/classroom/after_class.py courses/<课程名> --fragment L001 --status 已上课 --review

    # 标记需复习
    python function/classroom/after_class.py courses/<课程名> --fragment L003 --status 需复习 --tag "反馈调节混淆"

    # 只更新知识地图（不更新 reading_plan）
    python function/classroom/after_class.py courses/<课程名> --km-only
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent.parent

# ── advance_reading 逻辑 ──────────────────────────────────────

def _advance_reading(course_dir: Path, fragment: str, status: str,
                     next_fragment: str = "", tag: str = "", review: bool = False) -> int:
    """更新 reading_plan.md。返回变更数。"""
    rp_path = course_dir / "reading_plan.md"
    if not rp_path.exists():
        print(f"  跳过 reading_plan：文件不存在")
        return 0

    text = rp_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    new_lines = []
    updated_table = False
    updated_position = False
    updated_lesson_count = False
    changes = 0

    for i, line in enumerate(lines):
        if not updated_table and line.startswith(f"| {fragment} "):
            pattern = rf"^(\| {re.escape(fragment)} \|.*?\|.*?\|.*?\|.*?\|.*?\| )\S+?( \|)"
            new_line = re.sub(pattern, rf"\g<1>{status}\g<2>", line)
            if new_line != line:
                new_lines.append(new_line)
                updated_table = True
                changes += 1
                print(f"  reading_plan: {fragment} → {status}")
                continue
            new_lines.append(line)
            continue

        if not review and next_fragment and not updated_position:
            if line.strip().startswith("- 下一个片段："):
                new_lines.append(f"- 下一个片段：{next_fragment}")
                updated_position = True
                changes += 1
                print(f"  reading_plan: 下一个片段 → {next_fragment}")
                continue

        if not review and status == "已上课" and not updated_lesson_count:
            m = re.match(r"^- 已完成课时：(\d+)", line.strip())
            if m:
                count = int(m.group(1)) + 1
                new_lines.append(f"- 已完成课时：{count}")
                updated_lesson_count = True
                changes += 1
                print(f"  reading_plan: 已完成课时 → {count}")
                continue

        new_lines.append(line)

        if tag and line.strip().startswith("## 已完成标签"):
            new_lines.append(f"- {fragment}：{tag}")
            changes += 1
            print(f"  reading_plan: 标签 → {fragment}：{tag}")

    if not updated_table:
        print(f"  警告：未在表格中找到片段 {fragment}")
        return changes

    # 首次使用：已完成课时行不存在则新增
    if not review and status == "已上课" and not updated_lesson_count:
        inserted = False
        for i in range(len(new_lines) - 1, -1, -1):
            if new_lines[i].strip().startswith("- 前置依赖：") or new_lines[i].strip().startswith("- 下一个片段："):
                new_lines.insert(i + 1, "- 已完成课时：1")
                inserted = True
                break
        if not inserted:
            new_lines.append("- 已完成课时：1")
        changes += 1
        print(f"  reading_plan: 已完成课时 → 1（新增）")

    rp_path.write_text("\n".join(new_lines), encoding="utf-8")
    return changes


# ── update_knowledge_map 逻辑 ─────────────────────────────────

def _parse_lesson_state(course_dir: Path) -> dict:
    """从 lesson_state.yaml 提取结论和卡住问题"""
    yaml_path = course_dir / "lesson_state.yaml"
    md_path = course_dir / "lesson_state.md"
    path = yaml_path if yaml_path.exists() else md_path

    if not path.exists():
        return {"conclusions": [], "stuck": []}

    text = path.read_text(encoding="utf-8")

    # YAML
    if path.suffix == ".yaml":
        import yaml
        try:
            data = yaml.safe_load(text)
            if not data:
                return {"conclusions": [], "stuck": []}
            conclusions_raw = data.get("conclusions", [])
            stuck_raw = data.get("stuck", [])
            conclusions = []
            for c in conclusions_raw:
                if isinstance(c, str):
                    conclusions.append({"text": c, "weak": bool(re.search(r"[?？]|需巩固|待巩固|多用|不太稳|有点模糊", c))})
                elif isinstance(c, dict):
                    conclusions.append({"text": c.get("text", ""), "weak": c.get("weak", False)})
            stuck = [s if isinstance(s, str) else s.get("issue", str(s)) for s in stuck_raw]
            return {"conclusions": conclusions, "stuck": stuck}
        except Exception:
            pass

    # Markdown fallback
    conclusions = []
    stuck = []
    in_conclusions = False
    in_stuck = False

    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^##?\s*已建立的结论", stripped):
            in_conclusions, in_stuck = True, False; continue
        if re.match(r"^##?\s*卡住的问题|正在卡住", stripped):
            in_stuck, in_conclusions = False, True; continue
        if re.match(r"^##?\s", stripped) and not re.match(r"^###?\s", stripped):
            in_conclusions, in_stuck = False, False; continue
        item_match = re.match(r"^[-*]\s+(.+)", stripped)
        if item_match:
            content = item_match.group(1).strip()
            if in_conclusions:
                weak = bool(re.search(r"[?？]|需巩固|待巩固|多用|不太稳|有点模糊", content))
                conclusions.append({"text": content, "weak": weak})
            elif in_stuck:
                stuck.append(content)

    return {"conclusions": conclusions, "stuck": stuck}


def _parse_reading_plan(course_dir: Path) -> dict:
    """从 reading_plan.md 提取片段状态"""
    rp_path = course_dir / "reading_plan.md"
    if not rp_path.exists():
        return {}

    text = rp_path.read_text(encoding="utf-8")
    fragment_status = {}

    for line in text.split("\n"):
        match = re.match(r"^[-*]\s*(L\d+[a-z]*)[：:](.+)", line.strip())
        if match:
            fid = match.group(1)
            label = match.group(2).strip()
            if "需复习" in label: fragment_status[fid] = "需复习"
            elif "已上课" in label: fragment_status[fid] = "已上课"
            elif "跳过" in label: fragment_status[fid] = "跳过"

    in_table = False
    for line in text.split("\n"):
        if "片段ID" in line and "状态" in line:
            in_table = True; continue
        if in_table and line.strip().startswith("|") and not line.strip().startswith("|---"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if len(cells) >= 4:
                fid = cells[0]
                for c in cells[1:]:
                    if c in ("未处理", "已上课", "需复习", "跳过"):
                        if fid and fid not in fragment_status:
                            fragment_status[fid] = c
                        break
        if in_table and line.strip() == "":
            in_table = False

    return fragment_status


def _concept_match(concept_name: str, texts: list) -> bool:
    """简单概念名匹配"""
    if not concept_name:
        return False
    name = concept_name.strip().lower()
    for t in texts:
        if name in t.lower():
            return True
    return False


def _concept_in_conclusions(concept_name: str, conclusions: list) -> tuple:
    """检查概念名是否出现在结论中，返回 (出现, 弱化)"""
    for c in conclusions:
        if _concept_match(concept_name, [c["text"]]):
            return (True, c["weak"])
    return (False, False)


def _update_km(course_dir: Path) -> list:
    """更新 knowledge_map_state.json。返回变更列表。"""
    state_path = course_dir / "knowledge_map_state.json"
    if not state_path.exists():
        print("  跳过知识地图：knowledge_map_state.json 不存在")
        return []

    state = json.loads(state_path.read_text(encoding="utf-8"))
    lesson_data = _parse_lesson_state(course_dir)
    fragment_status = _parse_reading_plan(course_dir)

    nodes = state.get("nodes", {})
    conclusions = lesson_data["conclusions"]
    stuck = lesson_data["stuck"]
    changes = []

    for nid, node in nodes.items():
        old_status = node.get("status", "未学")
        new_status = old_status
        reason = ""

        fragment_id = node.get("fragment", "")
        concept = node.get("name", "")

        # 1. 关联片段未学
        if fragment_id and fragment_status.get(fragment_id) == "未处理":
            new_status = "未学"
            if old_status != new_status:
                reason = f"片段 {fragment_id} 尚未学习"

        # 2. 在卡住列表中
        if _concept_match(concept, stuck):
            new_status = "卡住"
            node["stuck_detail"] = "学生在课堂上卡在这个概念上"
            if old_status != new_status:
                reason = "概念出现在卡住问题中"

        # 3-4. 在结论中
        elif conclusions:
            found, weak = _concept_in_conclusions(concept, conclusions)
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
            if fs in ("已上课", "需复习") and not _concept_in_conclusions(concept, conclusions)[0]:
                new_status = "不稳"
                if old_status != new_status:
                    reason = f"片段 {fragment_id} 已上课但概念未在结论中出现"

        if new_status != old_status:
            now = datetime.now().strftime("%Y-%m-%d")
            node["status"] = new_status
            node["updated"] = now
            changes.append({
                "node_id": nid, "name": concept,
                "old": old_status, "new": new_status, "reason": reason,
            })

    state["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    if changes:
        print(f"\n  [{state['last_updated']}] 知识地图更新：")
        for ch in changes:
            print(f"    {ch['node_id']} {ch['name']}: {ch['old']} → {ch['new']}（{ch['reason']}）")
    else:
        print(f"  知识地图：无状态变更")

    return changes


# ── update_lesson_entry 逻辑 ────────────────────────────────────

def _update_lesson_entry(course_dir: Path, next_fragment: str):
    """推进 lesson_entry 到下一片段，清空 interrupted_at。行级替换，不乱格式。"""
    for ext in (".yaml", ".yml", ".md"):
        le_path = course_dir / f"lesson_entry{ext}"
        if le_path.exists():
            break
    else:
        print("  跳过 lesson_entry：文件不存在")
        return

    text = le_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    new_lines = []
    updated_fragment = False
    updated_interrupted = False

    for line in lines:
        stripped = line.strip()
        if not updated_fragment and stripped.startswith("fragment:"):
            new_lines.append(f"fragment: {next_fragment}")
            updated_fragment = True
        elif not updated_interrupted and stripped.startswith("interrupted_at:"):
            new_lines.append("interrupted_at:")
            updated_interrupted = True
        else:
            new_lines.append(line)

    if updated_fragment:
        le_path.write_text("\n".join(new_lines), encoding="utf-8")
        print(f"  lesson_entry: → {next_fragment}（清空卡点）")
    else:
        print(f"  警告：lesson_entry 中未找到 fragment 字段，未更新")


# ── 主入口 ─────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/after_class.py courses/<课程名> [options]")
        print("  --fragment Lxxx  --status 已上课|需复习  [--next Lxxx] [--tag 标签] [--review]")
        print("  --km-only  只更新知识地图")
        sys.exit(1)

    course_dir = Path(sys.argv[1])
    if not course_dir.exists():
        print(f"错误：找不到课程目录 {course_dir}")
        sys.exit(1)

    fragment = ""
    status = ""
    next_fragment = ""
    tag = ""
    review = False
    km_only = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--fragment" and i + 1 < len(args):
            fragment = args[i + 1]; i += 2
        elif args[i] == "--status" and i + 1 < len(args):
            status = args[i + 1]; i += 2
        elif args[i] == "--next" and i + 1 < len(args):
            next_fragment = args[i + 1]; i += 2
        elif args[i] == "--tag" and i + 1 < len(args):
            tag = args[i + 1]; i += 2
        elif args[i] == "--review":
            review = True; i += 1
        elif args[i] == "--km-only":
            km_only = True; i += 1
        else:
            i += 1

    print(f"课后更新：{course_dir.name}")

    # Step 1: 更新 reading_plan（除非只更新知识地图）
    if not km_only and fragment and status:
        if status not in ("已上课", "需复习"):
            print(f"错误：状态须为「已上课」或「需复习」，收到「{status}」")
            sys.exit(1)
        _advance_reading(course_dir, fragment, status, next_fragment, tag, review)
    elif km_only:
        print("  --km-only：跳过 reading_plan 更新")

    # Step 1.5: 推进 lesson_entry（有 --next 时自动切片段）
    if next_fragment:
        _update_lesson_entry(course_dir, next_fragment)

    # Step 2: 更新知识地图
    _update_km(course_dir)

    print("完成。")


if __name__ == "__main__":
    main()
