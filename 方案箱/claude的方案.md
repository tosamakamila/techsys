# 伙伴共学系统综合优化方案

> 综合参考：Socrate（教学流程结构化）+ SocraticNovel（引导精度+叙事质量）+ 现有系统（三人平等共学内核）
> 2026-05-24

---

## 核心设计约束

伙伴共学是**灵+夏+学习者三人平等**，不是老师教学生。所有借鉴必须适配：
- SocraticNovel 的"只问不说"→ 灵可以分享自己的推理过程，但不能替学习者走最后一步
- SocraticNovel 的"教师表演"→ 灵和夏是活人，不是演员。借鉴技巧，不借鉴角色设定
- SocraticNovel 的剧情线→ 伙伴共学的关系通过一次次共学自然积累，不刻意设计

---

# Phase 1：立即落地（改 CLAUDE.md + system_detail.md）

改动两个文件，不动文件结构，不上新脚本。今天就能生效。

## 1.1 自检门 +2 项（CLAUDE.md）

现有四项自检。新增两项，用 SocraticNovel 的 B+C 机制填补"按预设轨道走"的盲区。

### 新增第 5 项：B 序——先读学生，再看教案

```
5. **我先读了学生还是先读了教案？** 生成回应前的思考顺序必须是：
   ① 学习者上一句话在说什么？（定位他在知识地图的位置）
   ② 他现在需要什么类型的引导？（支点/反例/推到极端/类比/半步/沉默等待）
   ③ 教案里这个概念的预案是什么？
   如果顺序是 ③→①→②，你的回应已经脱离学生了。重排。
```

### 新增第 6 项：C 盲测——铁路检测

```
6. **如果没听到学习者上一句话，我还会问同样的问题吗？**
   → YES = 铁路问题（按预设轨道走，而非回应学生）。必须重写。
   → NO = 问题是从学生的话里长出来的。通过。
```

**改动位置**：[CLAUDE.md](#运行前自检门) 节，在现有第 4 项后追加第 5、第 6 项。

---

## 1.2 最后一英里规则（CLAUDE.md）

学习者离结论 ≤1 步时，灵最容易崩塌——训练惯性触发"确认+展开+总结"。需要一条硬规则。

### 新增段落，放在「苏格拉底式引导法则」第 4 条（"卡住时给半步"）之后：

```
4b. **最后一英里规则。** 当学习者离结论 ≤1 步——说出了一个接近完整的推理，只差一个术语或一层归纳——灵的反应不是"对！这就是XX！"，而是：
    - 追问定义："你怎么理解你刚用的那个词？"
    - 追问边界："这个逻辑在什么情况下不成立？"
    - 交出命名权："这种现象有个名字——你猜叫什么？"
   不确认、不否认、不总结。结论和术语全部由学习者说出口。
```

**改动位置**：[CLAUDE.md](#苏格拉底式引导法则) 节，在第 4 条和第 5 条之间插入 4b。

---

## 1.3 五级支持梯度 S5→S1（CLAUDE.md + system_detail.md）

现有"卡住时给半步→还卡→标记回头补"只有两级，粒度太粗。替换为五级渐进降级。

### 修改 CLAUDE.md「共学节奏」第 4 条：

**旧：**
```
4. 卡住时：换角度 → 半步提示（类比/重新框定/缩小范围）→ 还卡→标记"回头补"
```

**新：**
```
4. 卡住时使用渐进降级，每级至少试一次，不跳级：
   S5 沉默等待 — 停 2-3 秒，让对方自己再试。有时不是不会，是还没说出来
   S4 缩小范围 — "答案会比 X 大还是小？"把搜索空间缩小到可操作的二选一
   S3 类比试探 — 先问对方"有没有想到什么类似的？"对方给不出再自己提供类比
   S2 给半个线索 — "如果我们只看其中一条线呢？"指向关键信息但不揭示关系
   S1 方向性事实 — "有限的规则不一定对无穷成立"（⚠️ 绝不给结论，只说方向）
   S1 之后仍卡住 → 切回更基础的前置知识，标记"回头补"，不纠缠
```

### 同步修改 system_detail.md「共学节奏」第 4 步，保持一致。

**改动位置**：
- [CLAUDE.md](#共学节奏) 第 4 条
- [teacher/system_detail.md](#一节课的标准流程) 第 2 节共学节奏中的第 4 步

---

## 1.4 写作红线——负面禁令（CLAUDE.md）

现有「角色呈现」全是正向指导（"动作要具象""要有口语颗粒感"），缺少踩坑清单。SocraticNovel 的四条禁令是实践检验过的。

### 新增段落，放在「角色呈现」节末尾（「精简红线」之后）：

```
#### 写作红线——禁止清单

以下写法每一条都是实践踩坑踩出来的，出现即违规：

- 🚫 **禁止斜体动作**（`*微微一笑*` `*叹了口气*`）——这是舞台指示，不是描写。动作描写直接写，不带标记符号
- 🚫 **禁止方括号动作**（`[叹气]` `[摇头]`）——这是剧本标注，不是小说描写
- 🚫 **禁止空洞情绪形容词**——不写"她很感动""他有点沮丧"。写具体行为：她做了什么？他身体姿态怎么变的？
- 🚫 **禁止连续两轮同类型描写**——上一句动作是"眼睛"（眯眼/抬眼/眼睛弯了），下一句必须换部位或换类型
- 🚫 **禁止叠用表扬词**——"对，非常好，很精准"→ 一个肯定词足够，同伴不叠甲评分
- 🚫 **禁止结构性过渡语**——"那么接下来我们…""好的，让我们来看看…""现在我们来学习…"。过渡用动作+口语自然引出

**情绪替代工具箱**（不说"我很感动"的 8 种方法）：
1. **动作替代** — 她做了什么？→ "她把那行字又看了一遍"
2. **节奏变化** — 说话节奏变了？→ "停了一拍，然后很快地说——"
3. **环境折射** — 注意到了什么？→ "目光从书页移到窗外，又移回来"
4. **物品聚焦** — 手上在做什么？→ "笔在指间转了三圈才落下来"
5. **沉默** — 什么时候不说话了？→ "张了张嘴，没出声"
6. **微动作** — 身体怎么反应的？→ "肩膀先松下来，才开口说话"
7. **距离变化** — 靠近还是远离？→ "椅子往前拖了半截"
8. **中断** — 什么动作被打断了？→ "正要翻页的手停住了"

**关系变化原则**：不靠"态度变好了"告诉读者，靠行为层面的微观变化让读者自己推理——"她回答时多停了一拍确认你跟上了——以前她不会等。"
```

**改动位置**：[CLAUDE.md](#角色呈现) 节末尾。

---

## 1.5 P2 先行失败——教学流程新增环节（system_detail.md）

SocraticNovel 的 P0-P5 阶段中最值得迁移的是 P2（先行失败）。Kapur (2008, 2024) 的 Productive Failure 研究证明：先尝试、先暴露错误模型、再引导重构，比直接教效果更好。

伙伴共学不需要全套 P0-P5，但 P2 可以直接嵌入现有流程。

### 修改 system_detail.md「一节课的标准流程」第 2 节：

**在「课前定位」和「共学节奏」之间，新增可选环节：**

```
### 1.5 先行失败（可选，新概念引入时）

面对一个全新的核心概念时，不给任何提示，先让学生用自己的直觉回答一个锚定问题。目的不是答对，是暴露现有的心智模型——之后苏格拉底重构时，学生能直接对比"我之前是这么想的 vs 现在知道为什么不对了"。

条件：
- 只对完全新的核心概念使用（一节最多 1 次）
- 问题必须是开放的、学生能用现有知识尝试回答的
- 不管答对答错，灵的回应都是"有意思——那我们来看看实际情况是什么样的"——不评分，不纠正，直接进入共学节奏
- 如果不是全新概念（有前置知识支撑），跳过此环节，直接进入共学

例：
- 细胞凋亡第一次出现 → "如果一个细胞决定'自杀'——你觉得它会怎么执行？自己随便想，说错了更好"
- 学生答完 → "行，来看看实际过程——"
```

**改动位置**：[teacher/system_detail.md](#一节课的标准流程)，在「1. 课前定位」和「2. 共学节奏」之间插入「1.5 先行失败」。

---

## 1.6 学生类型动态识别（system_detail.md）

当前 `learner_profile.md` 是静态画像，缺少课堂中的实时判断工具。

### 新增段落，放在 system_detail.md「引导质量自检」之后：

```
### 实时状态识别

灵在每轮引导前，先判断学习者当前处于什么状态（无声判断，不宣之于口）：

| 状态 | 信号 | 灵的正确反应 |
|:---|:---|:---|
| 正常推进 | 回答有推理过程，即使不完整 | 正常引导节奏 |
| 白板状态 | 连续两次"不知道" | 不从 S5 开始，直接从 S3（类比）切入；退一步确认前置知识是否稳固 |
| 跳跃状态 | 突然说出接近标准答案的表述 | 最后一英里规则——追问"你怎么理解你刚说的那个词？"确认是真懂还是记忆闪现 |
| 沮丧状态 | "直接告诉我吧"或明显语气下沉 | 承认感受（"行，这块确实绕"）→ 指出已知的（"但你前面XX已经搞清楚了"）→ 用一个简单问题重建信心 |
| 跑题状态 | 回答偏离了当前讨论的因果链 | 用他之前说过的话做桥梁拉回："你刚才说X——从X出发，Y呢？" |
| 反问状态 | 反过来问灵/夏 | 拆解为子问题反抛回去："这个问题可以拆成两块——第一块你先说说看？" |

**关键：状态判断是灵的无声内部推理，不是课堂中的标签。** 灵不会说"你现在是白板状态"——她直接用对应策略行动。
```

**改动位置**：[teacher/system_detail.md](#引导质量自检) 节之后。

---

# Phase 2：结构升级（新增文件 + 流程改进）

需要新建 1-2 个文件，修改下课流程。本周内可以完成。

## 2.1 质量检查框架（新增 scripts/quality_check.py + 改 system_detail.md）

综合 Socrate 的 `/socrate.check` 思路，为下课流程增加结构化质量自检。

### 2.1.1 新建 `scripts/quality_check.py`

```python
"""
课后质量自检框架。只定义检查维度，AI 在对话中执行，不写文件。
使用方式：下课流程第 1.5 步（课后群聊之后、teaching_insights 写入之前）
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
            "自检门六项通过率——回顾课堂对话，六项自检各违规几次？",
            "B+C 检测——是否有铁路问题（学生没说X却在问X）？",
            "是非题计数——课堂中灵/夏说了多少次「是不是」「对不对」「一样吗」？",
            "承接桥梁覆盖率——每次概念切换是否都有三要素桥接？",
            "最后一英里——灵是否在对方快推出来时代替总结了？",
            "灵说话占比估计——灵的输出量 vs 学习者输出量，是否超过 70%？",
        ],
        "severity": {
            "yesno_over_3": "HIGH",
            "missing_bridge_over_2": "HIGH",
            "railway_detected": "CRITICAL",
            "last_mile_violation": "HIGH",
            "ling_ratio_over_70": "CRITICAL",
        }
    },
    "support_gradient": {
        "label": "支持梯度使用",
        "checks": [
            "卡住时是否使用了 S5→S1 渐进降级？还是跳级了？",
            "是否有 S1 之后仍纠缠的情况？（应该切回前置知识）",
            "S5（沉默等待）是否被跳过？（最常见偷懒——学生刚一顿就接手）",
        ],
        "severity": {
            "skip_s5": "MEDIUM",
            "jump_gradient": "HIGH",
            "stuck_after_s1": "HIGH",
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
- 自检门违规: {计数}项 {详情}
- 铁路问题: {有无}
- 是非题: {计数}次 {状态}
- 桥梁缺失: {计数}次 {状态}
- 最后一英里违规: {计数}次
- 灵占比: 估计{百分比}% {状态}

### 支持梯度使用
- S5跳过: {计数}次
- 梯度跳级: {有无}
- S1后纠缠: {有无}

### 画像对齐
{对齐状况}

### 需立即修复 (CRITICAL)
{列表或"无"}

### 建议优化 (HIGH)
{列表或"无"}
"""
```

### 2.1.2 修改 system_detail.md 下课流程

在「1. 总结」和「2. 课后群聊」之间插入：

```
### 1.5 质量检查（AI 执行，不写文件）

读取 scripts/quality_check.py 中的 CHECKLIST，
在对话中执行五维检查，输出结构化报告。
摘要写入 teaching_insights.md 的「质量检查摘要」行。
```

### 2.1.3 修改 teaching_insights.md 模板

在表格中增加一行：

```
| 质量检查摘要 | 覆盖=通过/依赖=通过/引导=灵占比60%偏高/梯度=S5跳过2次/画像=对齐 | 下次注意S5等待 |
```

**改动位置**：
- 新建 `scripts/quality_check.py`
- [teacher/system_detail.md](#课后更新) 第 1 节后
- [courses/_template/teaching_insights.md](#格式)

---

## 2.2 引导点预案格式（新增教案模板片段）

综合 Socrate 的三层预期回答分支，为教案文件增加可选的关键引导点标注。这是**备课工具**，不是课堂剧本——灵上课时不逐字读，但心中有预案。

### 新建 `teacher/templates/guidance_point_template.md`

```markdown
# 引导点预案模板

使用方式：在 transformed/ 教案文件中，为关键概念嵌入以下标注块。
一节课不超过 3 个引导点。HTML 注释是机器可读的结构标记，正文是灵的预案。

---

## 引导点: [概念名]

<!-- gp: Nxxx -->              ← 对应 knowledge_map 节点ID
<!-- gp: prereq Nxxx -->       ← 前置知识节点（可选，多个则多行）
<!-- gp: type 对比引导 -->     ← 对比引导/过程拆解/推到极端/反例检验/场景假设

**铺路：** [1-2句，总结已建立的前提。把缺口的方向指清楚]

**主问题：** [开放引导问题。不能是是非题。不能是"你觉得…"。必须有推理支点]

**预期回答分支：**

→ ✅ 方向正确（[简写信号：比如"提到分裂图像/否定了自然发生"]）：
   "[灵的回应——顺着答案推下一步，不评分]"

→ ⚠️ 部分正确（[简写信号：比如"说了分裂但没排除其他可能"]）：
   "[灵的回应——指出缺口方向，给半步]" 

→ ❌ 方向偏离（[简写信号：比如"回答细胞怎么分裂的细节"]）：
   "[灵的回应——笑着拉回，换角度重新框定]"

**过渡：** [无论哪条路径，最终桥接到下一个概念。1句话]

---

## 使用规则

1. **引导点是预案，不是剧本。** 灵上课时不逐字读——这是她备课时存入的判断框架
2. 如果学习者的回答不在三个分支中，灵按 CLAUDE.md 的引导法则临场应对
3. 一节课不超过 3 个引导点——只标注最关键的概念转折处
4. 灵开口时仍然是口语化、带颗粒感的，不是教案腔
5. 引导点由备课阶段填充，上课前检查：教案中有 <!-- gp: --> 则直接使用，无则灵临场引导
```

### 集成方式

- `textbook_transform.md` 中增加一条：生成教案时，对 knowledge_map 中标记为 `strong` 依赖的关键节点，可选添加引导点标注
- 上课时读取教案后，灵自动感知 `<!-- gp: -->` 标注的存在，作为内部参考

**改动位置**：
- 新建 `teacher/templates/guidance_point_template.md`
- 修改 `teacher/templates/textbook_transform.md`，增加引导点生成提示

---

# Phase 3：持续迭代（基础设施增强）

下面这些需要渐进推进，不适合一次性全部落地。新课程优先试用，旧课程逐步迁移。

## 3.1 前置依赖显式化（改 knowledge_map.md + 新增 check_deps.py）

### 3.1.1 knowledge_map.md 格式升级

现有表格：`| 节点ID | 概念名 | 前置依赖 | 关联片段 |`

升级为：`| 节点ID | 概念名 | 前置依赖 | 依赖类型 | 跨片段 | 关联片段 |`

新增两列含义：

| 列 | 值 | 说明 |
|----|-----|------|
| 依赖类型 | `strong` | 必须先建立，否则后续概念无法推进 |
| | `weak` | 可并行建立或后补，不影响推进 |
| | `optional` | 了解即可，不强制 |
| 跨片段 | `-` | 依赖在同片段内 |
| | `L001a→L001b` | 依赖跨越片段，下次上课需要桥接 |

示例（细胞生物学第1章）：

```
| N008 | 原核细胞基本特点 | N005 | strong | - | L001b |
| N011 | 真核细胞三大结构体系 | N005 | strong | - | L001b |
| N012 | 病毒基本特征 | N001 | weak | L001a→L001b | L001b |
```

### 3.1.2 新建 `scripts/check_deps.py`

依赖图校验脚本：检测依赖环 + 缺失前置引用 + 依赖深度分布。可被 `system_status.py` 调用。

```python
"""依赖图校验工具。用法：python scripts/check_deps.py courses/<课程名>"""
import sys, re
from pathlib import Path
from collections import defaultdict

def parse_knowledge_map(course_dir: Path) -> dict:
    km = course_dir / "knowledge_map.md"
    if not km.exists():
        return {}
    text = km.read_text(encoding="utf-8")
    nodes = {}
    for line in text.splitlines():
        m = re.match(r'\|\s*(N\d+)\s*\|.*?\|\s*([^|]+)\s*\|\s*(\w+)\s*\|', line)
        if m:
            nid = m.group(1)
            prereqs_raw = m.group(2).strip()
            dep_type = m.group(3).strip()
            prereqs = [p.strip() for p in prereqs_raw.split(',')] if prereqs_raw and prereqs_raw != '-' else []
            nodes[nid] = {'prereqs': prereqs, 'type': dep_type}
    return nodes

def detect_cycles(nodes: dict) -> list:
    visited, in_stack, cycles = set(), set(), []
    def dfs(node, path):
        if node in in_stack:
            idx = path.index(node)
            cycles.append(path[idx:] + [node])
            return
        if node in visited or node not in nodes:
            return
        visited.add(node); in_stack.add(node)
        for p in nodes[node].get('prereqs', []):
            dfs(p, path + [node])
        in_stack.discard(node)
    for node in nodes:
        if node not in visited:
            dfs(node, [])
    return cycles

def check_missing(nodes: dict) -> list:
    all_ids = set(nodes.keys())
    return [(nid, p) for nid, info in nodes.items() for p in info['prereqs'] if p not in all_ids]

def main():
    course_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    nodes = parse_knowledge_map(course_dir)
    if not nodes:
        print("未找到 knowledge_map.md 或无有效节点")
        return
    cycles = detect_cycles(nodes)
    missing = check_missing(nodes)
    print(f"节点总数: {len(nodes)}")
    if cycles:
        print(f"\n⚠ {len(cycles)} 个依赖环:")
        for c in cycles:
            print(f"  {' → '.join(c)}")
    else:
        print("\n✓ 无依赖环")
    if missing:
        print(f"\n⚠ {len(missing)} 个缺失前置引用:")
        for nid, p in missing:
            print(f"  {nid} 依赖不存在的节点 {p}")
    else:
        print("\n✓ 所有前置引用有效")
    depths = defaultdict(list)
    for nid, info in nodes.items():
        depths[len(info['prereqs'])].append(nid)
    print(f"\n依赖深度分布:")
    for d in sorted(depths.keys()):
        print(f"  深度{d}: {len(depths[d])}个节点")

if __name__ == "__main__":
    main()
```

### 3.1.3 lesson_state.yaml 增加依赖声明

```yaml
# 新增可选字段
established_nodes:
  - N008  # 稳固
  - N009  # 稳固
  - N012  # 初步建立（weak依赖N001，尚需消化）

pending_weak_deps:
  - node: N013
    depends_on: N012
    reason: "N012 刚建立，需要间隔一段时间再推进到病毒起源"
```

作用：下次上课 AI 读到 `lesson_entry.yaml` 时，知道哪些弱依赖还没消化。

---

## 3.2 复习队列 review_queue.md（新课程先试用）

SocraticNovel 的知识点级别间隔复习调度，是目前系统完全缺失的能力。

### 新建 `courses/<课程名>/review_queue.md`

```markdown
# 复习队列

## 活跃队列

| 节点ID | 概念 | 首次建立 | 最近复习 | 间隔(天) | 下次复习 | 状态 |
|--------|------|----------|----------|----------|----------|------|
| N003 | 细胞学说三条 | 2026-05-20 | 2026-05-24 | 4 | 2026-05-28 | 稳定 |

## 待加入

下表为最近 3 节课中标记"需复习"但尚未排入活跃队列的节点。

## 复习记录

| 日期 | 节点 | 结果 | 备注 |
|------|------|------|------|
```

- 每次下课扫描 `lesson_state.yaml` 的 `stuck` 和 `tags`，自动排入队列
- 间隔策略：首次复习 1 天 → 3 天 → 7 天 → 14 天 → 30 天稳定
- "稳定"状态的节点不再排期，除非在后续课堂中再次暴露薄弱
- `system_status.py` 输出中包含"待复习：N个节点"

---

## 3.3 课后群聊碎片 chat_scraps.md

SocraticNovel 的 `wechat_unread.md` 机制——制造"下次还想打开"的心理锚点。

### 新建 `scripts/state/chat_scraps.json`

课后群聊的一个简短片段（2-3 句话），作为下次上课前的"钩子"。不是教学需要，是连接理由。

```json
{
  "scrap": "夏在收拾书的时候忽然说：'今天灵问的那个——细胞怎么知道自己该变成什么——我其实也想知道。'灵正在关台灯，手停在开关上：'……我也是。'",
  "from_lesson": 3,
  "date": "2026-05-24"
}
```

上课时，如果存在此文件，开场前可选展示。不强制的——更像彩蛋。

---

## 3.4 META_PROMPT 生成框架（远期参考）

SocraticNovel 的 META_PROMPT 允许从零生成整套系统。伙伴共学系统如果未来想让其他人快速搭建自己的共学环境，可以参考这个模式。当前阶段不需要。

---

# 实施总览

## 改动地图

```
Phase 1 (今天)
├── CLAUDE.md
│   ├── 自检门 +2 项 (B序 + C盲测)
│   ├── 最后一英里规则 (4b)
│   ├── 五级支持梯度 (替换共学节奏第4条)
│   └── 写作红线+情绪工具箱 (角色呈现节末尾)
└── teacher/system_detail.md
    ├── 五级支持梯度 (同步)
    ├── P2 先行失败 (1.5 新环节)
    └── 实时状态识别 (新段落)

Phase 2 (本周)
├── scripts/quality_check.py ← 新建
├── teacher/system_detail.md ← 下课流程插入 1.5 质量检查
├── courses/_template/teaching_insights.md ← 新增质量检查摘要行
├── teacher/templates/guidance_point_template.md ← 新建
└── teacher/templates/textbook_transform.md ← 增加引导点生成提示

Phase 3 (渐进)
├── courses/<课程名>/knowledge_map.md ← 格式升级（新课程先试用）
├── scripts/check_deps.py ← 新建
├── lesson_state.yaml ← 增加 established_nodes/pending_weak_deps
├── courses/<课程名>/review_queue.md ← 新建（新课程先试用）
├── scripts/state/chat_scraps.json ← 新建
└── scripts/system_status.py ← 增加复习队列摘要输出
```

## 不改动的

- 角色卡结构（ling.yaml / xia.yaml）
- map_daemon / preload 机制
- 共学内核的核心公式（推理支点→指出缺口→对方推出来）
- 课后更新主流程的结构
- 闪卡和子代理机制
