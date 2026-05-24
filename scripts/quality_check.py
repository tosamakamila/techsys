"""
课后质量自检框架。只定义检查维度，AI 在对话中执行，不写文件。
使用方式：下课流程中，课后群聊之后、teaching_insights 写入之前，AI 读取此 CHECKLIST 执行五维检查。
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
## 质量检查报告 (第{N}课)

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
