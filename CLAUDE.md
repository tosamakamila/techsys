# 项目级指令

伙伴共学系统：`teacher/`(内核) `courses/`(课程) `courses/course_inbox/`(投递箱)。目标：每次上课只读最小必要文件。

## 入口规则（最高优先级）

收到指令 → 匹配路由表 → 匹配即执行。不探查。未匹配才往下分析。
- 非教学路由（群聊消息、系统状态、下课、放学等）：直接执行，不加载教学文件
- 教学路由（上课/复习、scene 为 study/review）：按「scene 分发」加载

## 路由表

| 触发 | 行为 |
|------|------|
| 「菜单」/ 打开 daemon / 切换场景 | 弹 daemon 窗口：`Start-Process powershell -ArgumentList "-NoExit", "-Command", "python function/map/daemon.py"`（必须在新的 PowerShell 窗口运行，不是 cmd）。选完场景后说「上课」即可。 |
| 「上课」 | pro 直接读 `function/state/map_state.json`。若 teacher 为空 → 提示"还没有想好哪位来一起学习哦，要启用菜单么？"。有值 → 按 scene 分发加载 → 开场 |
| 「下课」「今天到这里」 | 下课流程（见下） |
| 「放学」「走了」 | 直接退出 |
| 「看看消息」「群里有什么」「看群聊」 | haiku 读 `function/state/group_chat_unread.md`，有未读则展示；回复后追加到 `group_chat.md` 并清空未读 |
| 「闪卡复习」「复习闪卡」 | `python function/card/review.py` |
| 「系统状态」 | 运行 `python function/classroom/system_status.py` 输出摘要 |
| 「怎么走到这里的」 | pro 读 `function/state/map_state.json`，显示 scene 信息 + 推导路由决策链 |

上课/复习时：文件逐条读取过程不输出说明文字，读完直接输出角色对话或场景描写。不依赖 FileChanged 钩子。

## 模型分配

**pro 不调 Read/Grep/Glob。** 例外：study/review 由 pro 直接读取教学文件。轻量文件（`map_state.json`、lesson_entry.yaml、learner_profile.md 等）pro 可直接 Read，其余走 haiku 子代理：`Agent(subagent_type="general-purpose", model="haiku")`，prompt 写清读取文件列表和提取要求，多个文件并行启动。haiku 读取后按提取规则精简再返回 pro——不搬运原文，只返回 pro 需要的部分。

## scene 分发

scene 分发时，pro 直接读取以下文件：

| scene | 加载 |
|-------|------|
| `study` / `review` | 开场：① `map_state.json` ② `teacher/system_detail.md` ③ 角色卡 `profile.yaml` + `scenes/{scene}.yaml` ④ `lesson_entry.yaml` ⑤ `reading_plan.md`（只取已完成课时）。教学中：教材按教学点分段读、`learner_profile.md` 按需读。若 classmate 非空 → + `teacher/classroom.md` + 角色卡。review 额外 + `teacher/templates/review_lesson.md` |
| `chat` | `teacher/characters/xia/library_chat.md` + 角色卡 `profile.yaml` + `scenes/chat.yaml` + `teacher/dialogue_reference/xia.yaml`，不加载课程和其他角色 |

**study/review 固定执行步骤（逐条执行，不跳步、不推断）：**

1. pro **并行读取开场必需**：
   - `map_state.json` → 获取 teacher、course、scene、classmate
   - teacher 为空 → 提示"还没有想好哪位来一起学习哦，要启用菜单么？"→ 停止
   - `system_detail.md` → 教学规则
   - 角色卡 → 读 `teacher/characters/{teacher}/profile.yaml` + `teacher/characters/{teacher}/scenes/{scene}.yaml`
   - `lesson_entry.yaml` → 获取 fragment 和 interrupted_at
   - `reading_plan.md` → 只取 `已完成课时` 行
2. pro 开场（课程名 + 已完成课时 + 当前日期，日期取系统 `currentDate`，一句即可）。不输出技术说明。按教材原文顺序逐节推进，不跳过任何内容
3. **教材按教学点分段加载**：只读当前要讲的那一小段（1-2 个知识点），讲完再读下一段。不整章一次读完
4. `learner_profile.md` 教学中按需读，开场不加载
5. `progress.md`、`teaching_insights.md` 仅下课流程使用，上课不读

课程文件夹匹配：由 daemon 完成，不单独询问。`course.md` 仅首次建课时加载。`progress.md` 仅历史归档时加载。`reading_plan.md` 开场取已完成课时、推进到新片段时加载。

## 下课

按顺序执行，不做前置规划：

1. 总结：haiku 读课程文件（learner_profile.md、lesson_entry.yaml、progress.md）→ pro 标不稳概念，给下一课建议
2. haiku 子代理写课后产出（并行），**均需读 `teacher/dialogue_reference/` 下三个角色的对话参考**：
   - 课后群聊 → `teaching_insights.md`（灵+夏+柠讨论：覆盖内容、学习者状态、被绕开的问题）
   - 群聊消息 → 按 `function/state/group_chat_unread.md` 文件头规范写入
   - 结构化优化记录 → 追加 `teaching_insights.md` 表格（保留最近 5 条，≥3 次升迁到 learner_profile.md）
3. 询问是否标记闪卡 → 同意则并行启动闪卡子代理。子代理读 `card_material.md`（素材），产 `cards.md`（Q&A 格式闪卡）。产卡规则见 `function/card/card_rules.md`
4. `python function/classroom/after_class.py courses/<课程名> --fragment <片段ID> --status 已上课 [--next <下一片段>] [--review]`。若有 `--next`，脚本自动推进 `lesson_entry.yaml` 的 fragment 并清空 interrupted_at。agent 不再手动维护 lesson_entry 的片段位置

## 复习课下课

简化版下课（不走完整课后更新），见 `teacher/templates/review_lesson.md`「下课流程」节。

## 变更日志

仅系统能力/架构变更记入 `log.md`：`- 日期：一句话内容（一句话原因）`。**追加在文件末尾**。教学进度、课堂记录等写回课程文件夹，不记入 log。

## 方案计划
当给出比较长的解决方案的时候，将方案写进方案箱\claude的方案，并且覆盖里面的内容。
