"""
依赖图校验工具。
用法：
    python scripts/check_deps.py courses/<课程名>        # 直接输出
    python scripts/check_deps.py courses/<课程名> --json  # JSON 输出
也可从 system_status.py 导入 check_deps() 函数。
"""
import sys, re, json
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent


def parse_knowledge_map(course_dir: Path) -> dict:
    """解析 knowledge_map.md，返回 {节点ID: {title, prereqs, dep_type, cross_fragment, fragment}}

    兼容两种格式：
    - 旧 4 列: | NID | Title | Prereqs | Fragment |
    - 新 6 列: | NID | Title | Prereqs | Type | Cross | Fragment |
    """
    km = course_dir / "knowledge_map.md"
    if not km.exists():
        return {}

    text = km.read_text(encoding="utf-8")
    nodes = {}

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("| N"):
            continue

        cols = [c.strip() for c in line.split("|")]
        cols = [c for c in cols if c]
        if len(cols) < 3:
            continue

        nid = cols[0]
        title = cols[1] if len(cols) > 1 else ""

        if len(cols) >= 6:
            # 新格式: NID | Title | Prereqs | Type | Cross | Fragment
            prereqs_raw = cols[2]
            dep_type = cols[3]
            fragment = cols[-1]
        else:
            # 旧格式: NID | Title | Prereqs | Fragment
            prereqs_raw = cols[2] if len(cols) > 2 else "-"
            dep_type = "strong"  # 旧格式默认 strong
            fragment = cols[-1]

        prereqs = []
        if prereqs_raw and prereqs_raw != "-":
            prereqs = [p.strip() for p in prereqs_raw.split(",") if p.strip().startswith("N")]

        nodes[nid] = {
            "title": title,
            "prereqs": prereqs,
            "type": dep_type,
            "fragment": fragment,
        }

    return nodes


def detect_cycles(nodes: dict) -> list[list[str]]:
    """DFS 检测依赖环，返回环列表"""
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]):
        if node in in_stack:
            idx = path.index(node)
            cycles.append(path[idx:] + [node])
            return
        if node in visited or node not in nodes:
            return
        visited.add(node)
        in_stack.add(node)
        for p in nodes[node].get("prereqs", []):
            dfs(p, path + [node])
        in_stack.discard(node)

    for node in nodes:
        if node not in visited:
            dfs(node, [])

    return cycles


def check_missing_prereqs(nodes: dict) -> list[tuple[str, str]]:
    """检查引用了不存在的节点"""
    all_ids = set(nodes.keys())
    missing = []
    for nid, info in nodes.items():
        for prereq in info["prereqs"]:
            if prereq not in all_ids:
                missing.append((nid, prereq))
    return missing


def check_orphan_strong_deps(nodes: dict) -> list[str]:
    """检查 strong 依赖类型但前置节点为空或全部 weak/optional 的节点"""
    orphans = []
    for nid, info in nodes.items():
        if info["type"] != "strong":
            continue
        if not info["prereqs"]:
            continue
        has_strong_parent = any(
            p in nodes and nodes[p]["type"] == "strong"
            for p in info["prereqs"]
        )
        if not has_strong_parent:
            orphans.append(nid)
    return orphans


def check_deps(course_dir: Path) -> dict:
    """主检查函数，返回结果 dict"""
    nodes = parse_knowledge_map(course_dir)
    if not nodes:
        return {"error": "未找到 knowledge_map.md 或无有效节点", "node_count": 0}

    cycles = detect_cycles(nodes)
    missing = check_missing_prereqs(nodes)
    orphans = check_orphan_strong_deps(nodes)

    # 依赖深度分布
    depths = defaultdict(list)
    for nid, info in nodes.items():
        depths[len(info["prereqs"])].append(nid)

    # strong/weak/optional 统计
    type_counts = defaultdict(int)
    for info in nodes.values():
        type_counts[info["type"]] += 1

    return {
        "node_count": len(nodes),
        "cycle_count": len(cycles),
        "cycles": [[str(n) for n in c] for c in cycles],
        "missing_count": len(missing),
        "missing": [{"node": nid, "missing_prereq": p} for nid, p in missing],
        "orphan_strong_count": len(orphans),
        "orphans": orphans,
        "depth_distribution": {str(k): len(v) for k, v in sorted(depths.items())},
        "type_distribution": dict(type_counts),
        "healthy": len(cycles) == 0 and len(missing) == 0,
    }


def print_report(result: dict):
    """打印可读报告"""
    if "error" in result:
        print(result["error"])
        return

    print(f"节点总数: {result['node_count']}")

    # 类型分布
    td = result.get("type_distribution", {})
    if td:
        print(f"类型分布: strong={td.get('strong',0)} weak={td.get('weak',0)} optional={td.get('optional',0)}")

    # 环检测
    cycles = result.get("cycles", [])
    if cycles:
        print(f"\n[!!] 检测到 {len(cycles)} 个依赖环:")
        for c in cycles:
            print(f"  {' -> '.join(c)}")
    else:
        print("\n[OK] 无依赖环")

    # 缺失前置
    missing = result.get("missing", [])
    if missing:
        print(f"\n[!!] 检测到 {len(missing)} 个缺失前置引用:")
        for m in missing:
            print(f"  {m['node']} 依赖不存在的 {m['missing_prereq']}")
    else:
        print("[OK] 所有前置引用有效")

    # 孤立 strong 节点
    orphans = result.get("orphans", [])
    if orphans:
        print(f"\n[!!] {len(orphans)} 个 strong 节点缺少 strong 父节点:")
        for o in orphans:
            print(f"  {o}")

    # 深度分布
    dd = result.get("depth_distribution", {})
    if dd:
        print(f"\n依赖深度分布:")
        for d, count in sorted(dd.items(), key=lambda x: int(x[0])):
            print(f"  深度{d}: {count}个节点")

    # 总评
    if result.get("healthy"):
        print("\n[OK] 依赖图健康")


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/check_deps.py courses/<课程名> [--json]")
        sys.exit(1)

    course_dir = Path(sys.argv[1])
    if not course_dir.exists():
        print(f"目录不存在: {course_dir}")
        sys.exit(1)

    result = check_deps(course_dir)

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
