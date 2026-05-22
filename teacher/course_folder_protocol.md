# 分课程文件夹协议

`teacher/` 保存通用教学系统、老师与同学设定、跨课程学习者画像。

`courses/` 保存具体课程。每门课必须有独立文件夹。

`course_inbox/` 保存尚未归档的预存教材。

## 最小读取原则

启动时文件加载集见 CLAUDE.md「上课启动流程」。额外规则：

- 不要读取 `templates/`，除非正在做课后更新或教材改写。
- 不要读取 `classroom.md` 和 `characters/`，除非用户要求同学陪读。
- 确定课程后只读取当前课程文件夹，不读取其他课程。

## 课程文件夹结构

每门课建议包含：

- `course.md`：课程名称、别名、目标、教材来源。
- `progress.md`：本课程学习进度与历史归档。
- `lesson_state.md`：本节课教案入口 + 跨课堂持久状态。
- `reading_plan.md`：长教材分片计划、读取位置、片段状态。
- `materials/`：原始教材。
- `transformed/`：按片段生成的单课教案。
- `notes/`：用户笔记。
- `book_revision_notes.md`：本课程教材修订记录。

## 当用户说"上某某课"

1. 先读取 `teacher/` 的最小全局文件（见 CLAUDE.md）。
2. 到 `courses/` 下寻找对应课程文件夹。
3. 匹配方式：
   - 优先匹配文件夹名。
   - 再读取各课程 `course.md` 的课程名称和别名。
   - 有多个候选→简短询问用户。
   - 无候选→检查 `course_inbox/`（见 `course_inbox_protocol.md`）。
   - 投递箱也无候选→询问是否创建新课程。
4. 找到课程后，读取：`course.md`、`progress.md`、`lesson_state.md`、`reading_plan.md`、相关 `transformed/` 教案、必要时只读 `materials/` 当前片段。

## 长教材读取规则

教材超过一两万字时使用分片机制。短教材可直接生成教案按普通流程上课。

1. 优先读取 `reading_plan.md`。
2. 根据"当前读取位置"确定本节课片段。
3. 有 `transformed/` 教案优先读教案。
4. 无教案→只读对应原文范围 → 按 `teacher/templates/textbook_transform.md` 生成单课教案。
5. 只有依赖旧知识时才读旧片段教案或摘要。
6. 片段标记为"需复习"→下节课优先安排复习，不推进新片段。
7. 课后更新 `reading_plan.md`。

## 课后更新

课后更新按 `teacher/templates/after_class_update.md` 执行。课程信息写回当前课程文件夹，跨课程稳定特征写回 `teacher/learner_profile.md`。
