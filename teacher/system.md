# 伙伴共学系统

这是全局共学内核。具体课程材料、进度、状态、教案都放在 `courses/` 下各自课程文件夹中。

路由以 CLAUDE.md 为权威来源（联邦路由表模式）。场景切换由 `function/scripts/map.py` 处理。

## 文件分工

| 目录/文件 | 用途 | 加载时机 |
|-----------|------|---------|
| `teacher/system.md` | 本文件（分工表，开发者参考） | 不加载 |
| `teacher/system_detail.md` | 课堂流程与技法细节 | 每次上课 |
| `teacher/teacher_profile.md` | 已迁移至 CLAUDE.md + system_detail.md | 不再加载 |
| `teacher/course_folder_protocol.md` | 课程文件夹结构说明（参考） | 不加载 |
| `teacher/learner_profile.md` | 已迁移至 `courses/<课程名>/learner_profile.md` | 不再使用 |
| `teacher/course_inbox_protocol.md` | 教材投递箱协议 | courses/ 下无对应课程时 |
| `teacher/classroom.md` | 描写节奏+发言互动（map.py 加载） | study/review 场景 |
| `teacher/templates/` | 课后更新、教材改写等模板 | 课后更新或教材改写时 |
| `teacher/templates/review_lesson.md` | 复习协议（三段式循环+简化下课） | `review` 场景 |
| `teacher/characters/xia/library_chat.md` | 图书馆聊天场景指南（夏） | `chat` 场景 |
| `teacher/characters/<角色>/profile.yaml` | 角色卡（领航者/直觉型伙伴均 YAML化） | 按 scene 选取 |
| `teacher/characters/<角色>/scenes/{study,review,chat}.yaml` | 场景行为定义 | 按 scene 选取 |
| `function/scripts/map.py` | 终端交互式地图 | 用户说"上学"或上课触发词时 |
| `web/knowledge_panel.py` | 知识地图可视化面板 | 手动启动 |
| `function/scripts/_shared.py` | 脚本共享函数 | 各脚本内部引用 |
| `courses/<课程名>/` | 课程教材、进度、状态 | 选定课程后 |
