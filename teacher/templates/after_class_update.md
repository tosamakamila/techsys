# 课后更新

每节课结束后按此更新长期记忆。课堂中不要提及更新动作。

## 总原则

1. 只记录影响后续教学的内容，不写流水账
2. 区分一次性表现 vs 稳定特征，保守判断，避免一节课贴标签
3. 记录具体证据，下一课入口必须清晰自然

## 更新清单

### 1. 课堂诊断（心里过一遍）

- 今天学了什么？学生推出了什么？哪里卡住？哪种提示有效？
- 暴露的是一次性问题还是长期薄弱点？

### 2. progress.md

追加一行归档：`- 日期 | 片段ID：一句话摘要`。结论统一记在 lesson_state.yaml，此处不重复。

### 3. lesson_state.yaml（最重要，YAML 格式）

```yaml
course_type: 新课/复习课
fragment: L002a
fragment_topic: 主题名
source: materials/xxx.md

covered:
  - 本堂课已处理的概念

interrupted_at: 中断位置（如未中断则写"完成"；教材直讲模式下记录章节名或行号）

tags: [标签1, 标签2]

conclusions:
  - 学生已建立的结论

stuck:
  - issue: 卡住的问题
    detail: 具体表现

next_suggestions:
  - 下次开课建议

entry_line: |
  下一次对话入口（自然课堂语言，不提系统/文件）
```

- 中断→写清中断位置；完成→`interrupted_at: 完成`
- `entry_line` 写成领航者的课堂开场白
- **conclusions 截断规则**：保留最近 3 节课的结论，更早的只保留标注 ? / 需巩固 / 待巩固的条目（仍不稳标记），其余删除。避免结论无限积累

### 3b. lesson_entry.yaml（下次上课入口）

从 lesson_state.yaml 同步 4 个入口字段：
```yaml
fragment: L002a
interrupted_at: ...
stuck:
  - issue: ...
    detail: ...
entry_line: |
  ...
```

### 4. reading_plan.md（脚本执行）

```bash
python function/classroom/after_class.py courses/<课程名> --fragment <片段ID> --status 已上课 --next <下一片段>
```

- 标记需复习：`--status 需复习`（不传 `--next`）
- 追加标签：`--tag "简短说明"`
- 复习课：加 `--review`（只改状态，不推进位置）
- 只更新知识地图（不推进 reading_plan）：`--km-only`

此命令同时更新 knowledge_map_state.json，无需再调用 update_knowledge_map.py。

### 5. learner_profile.md（课程文件夹下，记忆压缩）

写入 `courses/<课程名>/learner_profile.md`。同一模式出现 ≥2 次才写入：

| 次数 | 行为 |
|------|------|
| 首次 | 不写入 |
| 第2次 | 写入"观察证据"：日期+现象+可能含义 |
| 第3-4次 | 压缩为特征，写入对应栏目，删原始证据 |
| ≥5次 | 标记稳定特征，默认应用 |

用"可能""倾向于"，不绝对判断。观察证据保留最近 3 条。

### 6. book_revision_notes.md

教材暴露问题时记录：来源、暴露问题、卡住位置、建议补充/删减。标注"建议制卡=是/否"的条目供闪卡步骤扫描。

### 7. 闪卡 card_material.md（询问学生同意后）

标记格式：`## 标记：<知识点>` + 制卡原因 + ≤3 条关键得分点 + 常见错误 + 来源。

- 只标值得制卡的，不重复标记
- 同时扫描 book_revision_notes.md 中"建议制卡=是"的条目

### 8. diary.md（可选）

### 9. 角色状态（极少更新，仅当课堂明显影响角色关系或教学风格时）

## 自检

- 下次说"上课"能否自然接上？
- reading_plan.md 读取位置是否推进？
- 卡点是否记录？是否过度贴标签？
