# 项目级指令

伙伴共学系统：`teacher/`(内核) `courses/`(课程) `courses/course_inbox/`(投递箱)。目标：每次上课只读最小必要文件。

## 入口规则（最高优先级）

收到指令 → 匹配路由表 → 匹配即执行。不探查。未匹配才往下分析。
- 非教学路由（群聊消息、系统状态、下课、放学等）：直接执行，不加载教学文件
- 教学路由（上课/复习、scene 为 study/review）：按「scene 分发」加载，教学规则由 haiku 从 `teacher/system_detail.md` 读取

## 路由表

| 触发 | 行为 |
|------|------|
| 「菜单」/ 打开 daemon / 切换场景 | 1. 弹 daemon 窗口：`Start-Process powershell -ArgumentList "-NoExit", "-Command", "python function/scripts/map_daemon.py"`（必须在新的 PowerShell 窗口运行，不是 cmd）。2. 用 `run_in_background` 后台轮询 `function/scripts/current_scene.json`（2s/120s 超时），检测到更新→`python function/scripts/map.py --go --stdout` 生成`function/scripts/state/_preload.json`→通知回来→haiku 按 scene 分发读文件→pro 开场。后台轮询不受会话中断影响。3. 超时→不做任何事 |
| `_preload.json` 已就绪时对话开始 | `function/scripts/state/_preload.json` 存在且未过期（与 `function/scripts/current_scene.json` timestamp 匹配）→ 直接按 scene 分发读文件开场 |
| 「上课」 | 弹 daemon + 后台轮询（同上步骤 2），选完场景→`map.py --go`→按 scene 分发→开场 |
| 「下课」「今天到这里」 | 下课流程（见下） |
| 「放学」「走了」 | 直接退出 |
| 「看看消息」「群里有什么」「看群聊」 | haiku 读 `function/scripts/state/group_chat_unread.md`，有未读则展示；回复后追加到 `group_chat.md` 并清空未读 |
| 「系统状态」 | 运行 `python function/scripts/system_status.py` 输出摘要 |
| 「怎么走到这里的」 | haiku 读 `function/scripts/current_scene.json`，pro 显示 scene 信息 + 推导路由决策链 |

上课/复习时：文件逐条读取过程不输出说明文字，读完直接输出角色对话或场景描写。不依赖 FileChanged 钩子。

## 模型分配

**pro 不调 Read/Grep/Glob。** 例外：study/review 步骤 1-2 由 pro 直接读取所有文件。轻量文件（`_preload.json`、`current_scene.json`、lesson_entry.yaml、learner_profile.md、progress.md 等）pro 可直接 Read，其余走 haiku 子代理：`Agent(subagent_type="general-purpose", model="haiku")`，prompt 写清读取文件列表和提取要求，多个文件并行启动。haiku 读取后按提取规则精简再返回 pro——不搬运原文，只返回 pro 需要的部分。

## scene 分发

scene 分发时，pro 直接读取以下文件：

| scene | 加载 |
|-------|------|
| `study` / `review` | ① `teacher/system_detail.md` ② 老师角色卡(scenes.{scene}) ③ 课程文件：learner_profile.md + lesson_entry.yaml + 教材对应章节（从 lesson_entry.yaml 的 fragment 定位章节号，读 `materials/` 下对应教材原文）。若 classmate 非空 → + `teacher/classroom.md` + 角色卡。review 额外 + `teacher/templates/review_lesson.md` |
| `chat` | `teacher/library_chat.md` + 夏(scenes.chat)，不加载课程和其他角色 |

**study/review 固定执行步骤（逐条执行，不跳步、不推断）：**

1. pro **一次调用并行读取全部**：
   - system_detail.md → 完整返回（教学规则 pro 全需）
   - 角色卡 → 只返回 `scenes.{scene}` 节 + 说话风格 + 动作库（对话片段和场景描写不返回）
   - learner_profile.md + lesson_entry.yaml → 完整返回（已够短）
   - 教材原文 → 从 lesson_entry.yaml 的 `fragment` 字段确定章节号，读 `courses/<课程名>/materials/` 下对应教材的该章节。从 `interrupted_at` 标记的位置开始，完整返回本章剩余内容。若 `interrupted_at` 为"待开始"则从章首开始
2. pro 开场，不输出技术说明。按教材原文顺序逐节推进，不跳过任何内容

课程文件夹匹配：由 daemon 完成，不单独询问。`course.md` 仅首次建课时加载。`progress.md` 仅历史归档时加载。`reading_plan.md` 仅推进到新片段时加载。

## 下课

按顺序执行，不做前置规划：

1. 总结：haiku 读课程文件（learner_profile.md、lesson_entry.yaml、progress.md）→ pro 标不稳概念，给下一课建议
2. haiku 子代理写课后产出（并行）：
   - 课后群聊 → `teaching_insights.md`（灵+夏+柠讨论：覆盖内容、学习者状态、被绕开的问题）
   - 群聊消息 → `function/scripts/state/group_chat_unread.md`（2-4 条日常闲聊，不写教学复盘）
   - 结构化优化记录 → 追加 `teaching_insights.md` 表格（保留最近 5 条，≥3 次升迁到 learner_profile.md）
3. 询问是否标记闪卡 → 同意则并行启动闪卡子代理（card_material.md + 课程文件更新 + teaching_insights.md）
4. `python function/scripts/after_class.py courses/<课程名> --fragment <片段ID> --status 已上课 [--next <下一片段>] [--review]`

## 复习课下课

简化版下课（不走完整课后更新），见 `teacher/templates/review_lesson.md`「下课流程」节。

## 变更日志

仅系统能力/架构变更记入 `log.md`：`- 日期：一句话内容（一句话原因）`。**追加在文件末尾**。教学进度、课堂记录等写回课程文件夹，不记入 log。

## 方案计划
当给出比较长的解决方案的时候，将方案写进方案箱\claude的方案，并且覆盖里面的内容。
