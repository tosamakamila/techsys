# Socrate 借鉴方案：三项可落地的系统改进

参考项目：[Socrate](https://github.com/Haaaiawd/Socrate) — 提示词优先的苏格拉底教学 CLI

---

## 一、质量检查系统

### 要解决的问题

当前系统下课后依赖灵和夏的"课后群聊"做诊断，但诊断是散文式的、依赖临场记忆的。没有一个**结构化的、可自动执行的**质量检查流程来发现：
- 知识点覆盖断裂（学了 N008 但 N007 没建立）
- 引导质量退化（连续使用是非题、硬跳无桥梁、说话占比过高）
- 学习画像与实际课堂行为不一致

### 设计方案

新增一个课后自检流程，在"课后群聊"**之后**、写入 `teaching_insights.md` **之前**执行。由 AI 利用已有结构化数据做只读分析，不新增文件。

#### 新增文件：`scripts/quality_check.py`

不是独立脚本，是给 AI 的**检查清单+分析框架**。下课流程中，AI 读取此文件作为检查依据，直接在对话中输出检查报告，然后摘要写入 `teaching_insights.md`。

```python
# scripts/quality_check.py
"""
课后质量自检框架。只定义检查维度，AI 在对话中执行，不写文件。
使用方式：下课流程的第 1.5 步（课后群聊之后、teaching_insights 写入之前）
"""

CHECKLIST = {
    "coverage": {
        "label": "覆盖连续性",
        "checks": [
            "knowledge_map 中本课涉及节点 → 是否全部在 covered 列表中？",
            "前置依赖链上是否有断裂？——如果本课覆盖了 N008 但 N007 未覆盖，标记",
            "reading_plan 中标记需复习的片段 → 是否在本次课堂中被触及？",
        ],
        "severity": {
            "missing_covered": "HIGH",
            "dependency_gap": "CRITICAL",
            "missed_review_flag": "MEDIUM",
        }
    },
    "dependency": {
        "label": "依赖图完整性",
        "checks": [
            "knowledge_map 中本课涉及节点 → 每个节点有明确的前置依赖或标注为根节点",
            "前置依赖链无环——从任意节点出发沿依赖链走到底，不回到自身",
            "跨片段依赖——如果本课片段依赖上一片段的概念，entry_line 是否桥接了？",
        ],
        "severity": {
            "missing_prereq": "CRITICAL",
            "cycle_detected": "CRITICAL",
            "missing_bridge": "HIGH",
        }
    },
    "guidance": {
        "label": "引导质量",
        "checks": [
            "自检门五项通过率——回顾课堂对话，五项自检各违规几次？",
            "是非题计数——课堂中灵/夏说了多少次「是不是」「对不对」「一样吗」？",
            "承接桥梁覆盖率——每次概念切换是否都有三要素桥接？（已解决→矛盾/关联→开启提问）",
            "灵说话占比估计——灵的输出量 vs 学习者输出量，是否超过 70%？",
        ],
        "severity": {
            "yesno_over_3": "HIGH",
            "missing_bridge_over_2": "HIGH",
            "ling_ratio_over_70": "CRITICAL",
        }
    },
    "profile_alignment": {
        "label": "画像对齐",
        "checks": [
            "learner_profile 有效策略 → 本次课堂是否应用了？",
            "learner_profile 需要避免 → 本次课堂是否触碰了？",
            "本次课堂新发现 → 是否与已知薄弱点/待观察一致？如果矛盾，记录",
        ],
        "severity": {
            "strategy_not_applied": "MEDIUM",
            "avoidance_violated": "HIGH",
            "profile_contradiction": "MEDIUM",
        }
    }
}

REPORT_TEMPLATE = """
## 质量检查报告 (第{N}课 {日期})

### 覆盖连续性
{覆盖率统计}
{缺失/断裂项}

### 依赖完整性
{依赖图状态}
{异常项}

### 引导质量
- 是非题: {计数}次 {状态}
- 桥梁缺失: {计数}次 {状态}
- 灵占比: 估计{百分比}% {状态}

### 画像对齐
{对齐状况}

### 需立即修复 (CRITICAL)
{列表或"无"}

### 建议优化 (HIGH)
{列表或"无"}
"""
```

#### 集成点：修改 `teacher/system_detail.md` 的"课后更新"节

在现有流程中插入 1.5 步：

```
## 课后更新

### 1. 总结
### 1.5 质量检查 ← 新增
读取 scripts/quality_check.py 中的 CHECKLIST，
在对话中执行四维检查，输出结构化报告。
摘要写入 teaching_insights.md 的「质量检查摘要」行。
### 2. 课后群聊
...
```

#### 集成点：修改 `courses/_template/teaching_insights.md`

在现有表格格式中增加一行「质量检查摘要」：

```
## 第N课 (日期)

| 维度 | 诊断详情 | 优化策略 |
|:---|:---|:---|
| 质量检查摘要 | 覆盖=通过/依赖=1项CRITICAL/引导=灵占比65%偏高/画像=对齐 | 下次控制灵输出量 |
| 推理断层点 | ... | ... |
| 交互特征 | ... | ... |
| 策略有效性 | ... | ... |
```

### 为什么不做成独立脚本

质量检查需要**理解课堂对话内容**（数是非题、评估桥梁覆盖率、估计灵占比），这只能由 AI 在上下文中完成。做成独立脚本会退化为只有 coverage 和 dependency 的机械检查——意义不大。保持"框架文件 + AI 执行"的模式，和现有 `after_class_update.md` 的定位一致。

---

## 二、前置依赖显式化

### 要解决的问题

`knowledge_map.md` 已有 `前置依赖` 列，但它是给人看的自然语言（如 `N005`、`N002`），没有：
- 依赖类型区分（强依赖/弱依赖/可选前置）
- 跨片段依赖的显式标记
- 机器可解析的格式让脚本做环检测

### 设计方案

#### 2.1 knowledge_map.md 格式升级

在现有表格中增加两列：`依赖类型` 和 `跨片段`。

**现有格式：**
```
| N008 | 原核细胞基本特点 | N005 | L001b |
```

**升级后：**
```
| N008 | 原核细胞基本特点 | N005 | strong | - | L001b |
| N009 | 细菌细胞结构与功能 | N008 | strong | - | L001b |
| N011 | 真核细胞三大结构体系 | N005 | strong | - | L001b |
| N012 | 病毒基本特征 | N001 | weak | L001a→L001b | L001b |
```

列定义：
| 列 | 含义 |
|----|------|
| 节点ID | 不变 |
| 概念名 | 不变 |
| 前置依赖 | 不变——依赖的节点ID列表 |
| **依赖类型** | **新增** — `strong`（必须先建立）/ `weak`（可并行或后补）/ `optional`（了解即可）|
| **跨片段** | **新增** — 如果依赖来自其他片段，标注 `来源片段→当前片段` |
| 关联片段 | 不变 |

#### 2.2 lesson_state.yaml 增加依赖声明

在 `lesson_state.yaml` 中增加一个可选字段，让每次课后声明"本次建立的节点"和"遗留的弱依赖"：

```yaml
# lesson_state.yaml 新增字段
established_nodes:
  - N008  # 原核细胞基本特点 — 建立稳固
  - N009  # 细菌细胞结构 — 建立稳固
  - N012  # 病毒基本特征 — 初步建立，weak 依赖 N001

pending_weak_deps:
  - node: N013
    depends_on: N012
    reason: "病毒起源讨论中，N012 刚建立，需要间隔一段时间再推进"
```

这个字段的作用：下次上课前 AI 读到 `lesson_entry.yaml` 时，知道哪些弱依赖还没消化完，避免强行推进。

#### 2.3 环检测工具：`scripts/check_deps.py`

一个简单的 Python 脚本，读取 knowledge_map 做依赖图校验：

```python
# scripts/check_deps.py
"""
依赖图校验工具。
用法：python scripts/check_deps.py courses/<课程名>
输出：依赖环列表 + 缺失前置列表 + 依赖深度统计
"""
import sys, yaml, re
from pathlib import Path
from collections import defaultdict

def parse_knowledge_map(course_dir: Path) -> dict:
    """解析 knowledge_map.md，返回 {节点ID: {prereqs, type, cross_fragment}}"""
    km = course_dir / "knowledge_map.md"
    if not km.exists():
        return {}
    
    text = km.read_text(encoding="utf-8")
    nodes = {}
    
    for line in text.splitlines():
        # 匹配表格行: | N008 | 原核细胞基本特点 | N005 | strong | - | L001b |
        m = re.match(r'\|\s*(N\d+)\s*\|.*?\|\s*([^|]+)\s*\|\s*(\w+)\s*\|', line)
        if m:
            nid = m.group(1)
            prereqs_raw = m.group(2).strip()
            dep_type = m.group(3).strip()
            
            prereqs = []
            if prereqs_raw and prereqs_raw != '-':
                prereqs = [p.strip() for p in prereqs_raw.split(',')]
            
            nodes[nid] = {
                'prereqs': prereqs,
                'type': dep_type,
            }
    
    return nodes

def detect_cycles(nodes: dict) -> list:
    """DFS 检测依赖环"""
    visited = set()
    in_stack = set()
    cycles = []
    
    def dfs(node, path):
        if node in in_stack:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        if node in visited or node not in nodes:
            return
        
        visited.add(node)
        in_stack.add(node)
        
        for prereq in nodes[node].get('prereqs', []):
            dfs(prereq, path + [node])
        
        in_stack.discard(node)
    
    for node in nodes:
        if node not in visited:
            dfs(node, [])
    
    return cycles

def check_missing_prereqs(nodes: dict) -> list:
    """检查引用了不存在的节点"""
    all_ids = set(nodes.keys())
    missing = []
    for nid, info in nodes.items():
        for prereq in info['prereqs']:
            if prereq not in all_ids:
                missing.append((nid, prereq))
    return missing

def main():
    course_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    nodes = parse_knowledge_map(course_dir)
    
    if not nodes:
        print("未找到 knowledge_map.md 或无有效节点")
        return
    
    cycles = detect_cycles(nodes)
    missing = check_missing_prereqs(nodes)
    
    print(f"节点总数: {len(nodes)}")
    
    if cycles:
        print(f"\n⚠ 检测到 {len(cycles)} 个依赖环:")
        for c in cycles:
            print(f"  {' → '.join(c)}")
    else:
        print("\n✓ 无依赖环")
    
    if missing:
        print(f"\n⚠ 检测到 {len(missing)} 个缺失前置引用:")
        for nid, prereq in missing:
            print(f"  {nid} 依赖不存在的节点 {prereq}")
    else:
        print("\n✓ 所有前置引用有效")
    
    # 深度统计
    depths = defaultdict(list)
    for nid, info in nodes.items():
        d = len(info['prereqs'])
        depths[d].append(nid)
    
    print(f"\n依赖深度分布:")
    for d in sorted(depths.keys()):
        print(f"  深度{d}: {len(depths[d])}个节点")

if __name__ == "__main__":
    main()
```

此脚本可被 `system_status.py` 调用，也可在 `socrate init` 初始化项目时运行一次做健康检查。

---

## 三、预期回答分支

### 要解决的问题

当前系统中灵的引导策略全部在 CLAUDE.md 的 prompt 中描述（"卡住时给半步提示""换角度重新框定"），但没有任何**结构化的预案**。灵在课堂中需要临场判断"这个回答属于正确/部分/错误中的哪一类"并选择对应引导路径——这完全依赖 LLM 的临场推理，质量不稳定。

Socrate 的 `chapter-template.md` 为每个关键问题预设了三种回答路径，这是一个值得借鉴的结构。

### 设计方案

#### 3.1 在教案中新增「关键引导点」区段

在 `transformed/` 教案文件（或教材直讲时在 `materials/` 原文相关位置）中，为每个核心概念添加可选的「关键引导点」标注。

格式直接嵌入教案文件中，不用单独的文件：

```markdown
## 引导点: 细胞学说三条的第三条——"细胞来自细胞"

<!-- gp: N003 -->
<!-- gp: prereq N002 -->
<!-- gp: type 对比引导 -->

**铺路：** 前面两条说了两件事——(1)所有生物由细胞构成，(2)细胞是生命活动的基本单位。
这两条都描述了"细胞是什么"。第三条"细胞来自细胞"在意的不是"是什么"，是"从哪来的"。

**主问题：** 如果魏尔啸在1855年观察到伤口边缘有新细胞出现，他凭什么断定这些新细胞是旧细胞分裂来的，而不是从伤口液体里凭空冒出来的？

**预期回答分支：**

→ ✅ 正确方向（提到"看到分裂图像"或"逻辑推断如果凭空出现不需要一个初始细胞"）：
   "对——显微镜下确实看到了分裂中的细胞中间出现隔膜。但魏尔啸在说这句话的时候还有一个逻辑前提——他必须先否定什么？"

→ ⚠️ 部分正确（提到细胞分裂但没说凭什么排除其他可能）：
   "分裂能解释一部分。但魏尔啸说的是'所有'细胞都来自细胞——他凭什么排除'有些细胞可以从无到有'这种可能？当时自然发生说还很流行。"

→ ❌ 方向偏离（回答成细胞怎么分裂的细节）：
   "噗——那个是'怎么产生的'，我更好奇的是——看伤口长新细胞的时候，魏尔啸脑子里在反对谁？当时大家普遍信什么？"

**过渡：** 否定自然发生说 → 确认所有细胞来自已有细胞的分裂 → 自然引出：那第一个细胞怎么来的？
```

#### 3.2 标注规范

每个引导点以 `<!-- gp: 节点ID -->` 开头，包含以下结构字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `gp: 节点ID` | 是 | 对应 knowledge_map 中的节点 |
| `gp: prereq` | 否 | 引导前需确认的前置知识 |
| `gp: type` | 是 | 引导类型：`对比引导`/`过程拆解`/`推到极端`/`反例检验`/`场景假设` |
| **铺路** | 是 | 一两句总结已建立的前提 |
| **主问题** | 是 | 核心引导问题，不能是是非题 |
| **预期回答分支** | 否 | 正确/部分/偏离三条路径，每条不超过2句话 |
| **过渡** | 是 | 无论哪条路径，最终要桥接到下一个概念 |

#### 3.3 使用规则

最关键的一条：**引导点是预案，不是剧本。**

- 课堂中灵**不逐字读**引导点内容——那是给灵的内部参考
- 如果学习者的回答不在三个分支中，灵按 CLAUDE.md 的引导法则临场应对
- 一节课不超过 3 个引导点——只标注最关键的概念转折处
- 引导点不替代灵的角色性格——灵开口时仍然是口语化、带颗粒感的，不是教案腔

#### 3.4 curriculum designer 的职责

引导点由**备课阶段**（而非上课阶段）填充。当推进到新片段时，AI 检查教案：

1. 教案中有 `<!-- gp: -->` 标注 → 已设计引导点，直接使用
2. 教案中无标注但有 `knowledge_map` 中标记为 `strong` 依赖的关键节点 → 询问是否要补充引导点
3. 教材直讲无教案 → 不强制，灵的临场引导即可

---

## 实施优先级

| 优先级 | 改进项 | 理由 |
|--------|--------|------|
| **P0 立即** | 质量检查框架 (`quality_check.py`) | 改动最小，直接插入下课流程，立即提升课后诊断质量 |
| **P1 本周** | 预期回答分支（教案格式） | 解决灵引导质量不稳定的核心痛点，但需要备课阶段配合填充 |
| **P2 渐进** | knowledge_map 格式升级 + `check_deps.py` | 依赖图校验有价值，但需要逐课程迁移旧格式，适合新课程先试用 |

---

## 与现有架构的关系

- **不改动** CLAUDE.md 的共学内核（苏格拉底引导法则、自检门、禁令）
- **不改动** 角色卡结构（ling.yaml / xia.yaml）
- **不改动** map_daemon / preload 机制
- **仅在** 下课流程（`system_detail.md` 课后更新节）、教案格式、knowledge_map 表格结构中做增量添加
