# 苏格拉底式学习系统

这是全局教学内核。具体课程材料、进度、状态、教案都放在 `courses/` 下各自课程文件夹中。

路由以 CLAUDE.md 为权威来源（联邦路由表模式）。场景切换由 `scripts/map.py` 处理。

## 文件分工

| 目录/文件 | 用途 | 加载时机 |
|-----------|------|---------|
| `teacher/system.md` | 本文件（分工表） | 每次上课 |
| `teacher/system_detail.md` | 教学方式与课堂规则 | 每次上课 |
| `teacher/teacher_profile.md` | 通用教学框架 | 每次上课 |
| `teacher/course_folder_protocol.md` | 课程匹配与更新协议 | 每次上课（复习课跳过）|
| `teacher/learner_profile.md` | 跨课程学习者画像（记忆压缩） | 每次上课 |
| `teacher/course_inbox_protocol.md` | 教材投递箱协议 | courses/ 下无对应课程时 |
| `teacher/classroom.md` | 同学陪读模式 | 用户选择同学陪读时 |
| `teacher/templates/` | 课后更新、教材改写等模板 | 课后更新或教材改写时 |
| `teacher/templates/review_lesson.md` | 迷你课复习协议（三段式循环+简化下课） | `review_with_teacher` 场景 |
| `characters/<角色>/` | 角色卡 + 背景故事 | 每次上课（卡）/ 首次见面（故事） |
| `scripts/map.py` | 终端交互式地图 | 用户说"上学"或上课触发词时 |
| `scripts/map_server.py` | 知识地图可视化面板 | 手动启动 |
| `scripts/_shared.py` | 脚本共享函数 | 各脚本内部引用 |
| `courses/<课程名>/` | 课程教材、进度、状态 | 选定课程后 |
