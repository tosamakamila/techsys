# 课程教材投递箱协议

`courses/course_inbox/` = 预存教材的临时入口。用户说"上某某课"时，先查 `courses/`，无则查 `courses/course_inbox/`。

## 匹配规则

1. 在 `courses/` 下寻找已存在的课程文件夹
2. 无→检查 `courses/course_inbox/` 下是否有文件名包含课程名的教材
3. 多个匹配→视为同一课程候选；不确定→简短询问

## 自动建课流程

若 `courses/` 下无对应课程但 `courses/course_inbox/` 中有匹配教材：

1. 创建课程文件夹，从 `courses/_template/` 复制基础结构
2. **移动**（非复制）教材到 `courses/<课程名>/materials/`
3. 更新 `course.md`：名称、别名、教材来源、课程状态
4. 初始化 `progress.md` 和 `lesson_state.yaml`
5. 若教材 >1-2 万字→初始化 `reading_plan.md`（识别目录→建分片计划→设首个片段）
6. 询问：先按 `textbook_transform.md` 生成教案，还是直接开始诊断式上课？

## 课后更新

课程创建后所有状态写入课程文件夹，不再写入 `courses/course_inbox/`。
