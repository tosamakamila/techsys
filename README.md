# 苏格拉底式学习系统

## 目录地图

```
sugeladi/
├── CLAUDE.md              ← 联邦路由表：触发→加载什么，~109行
├── README.md              ← 你在这里
├── log.md                 ← 变更日志
├── .gitignore             ← 排除运行时文件+开发文件
│
├── teacher/               ← 全局教学内核
│   ├── system.md          教学系统概述（文件分工表）
│   ├── system_detail.md   苏式教学细则（问题设计、课堂节奏、课后规则）
│   ├── teacher_profile.md 通用教学框架（所有老师共享）
│   ├── learner_profile.md 学习者长期画像（记忆压缩机制）
│   ├── classroom.md       多人课堂规则（通过 map.py 触发）
│   ├── course_folder_protocol.md   课程匹配与文件协议
│   ├── course_inbox_protocol.md    新课程自动建课协议
│   └── templates/
│       ├── after_class_update.md   课后更新模板
│       └── textbook_transform.md   长教材分片与教案模板（~110行）
│
├── characters/            ← 角色文件（卡片式）
│   ├── hoshino_mio/
│   │   ├── hoshino_mio.md          澪的角色卡（上课加载，~72行）
│   │   ├── character_backstory.md  澪的背景故事（首次/按需加载）
│   │   └── supplement_tutoring.md  课后辅导补充（仅辅导模式）
│   └── asakura_natsune/
│       └── asakura_natsune.md      夏音的人物文件
│
├── scripts/               ← 脚本层
│   ├── _shared.py         共享函数（scan_courses, compute_transitive_impact 等）
│   ├── map.py             终端交互式地图导航
│   ├── map_server.py      知识地图可视化面板（HTTP 服务器）
│   ├── build_knowledge_map.py      从 .md 生成 knowledge_map_state.json
│   ├── recommend_node.py           薄弱节点推荐
│   ├── update_knowledge_map.py     课后更新知识地图状态
│   ├── templates/
│   │   └── index.html     map_server 前端页面
│   ├── current_scene.json 场景交接信号（map.py 写 → AI 读 → AI 删）
│   └── map_state.json     地图记忆（上次位置/老师/课程）
│
├── courses/               ← 具体课程
│   ├── _template/         课程模板（新建课程时复制）
│   │   ├── course.md / progress.md / lesson_state.md / reading_plan.md
│   │   └── book_revision_notes.md
│   ├── _general/          通用诊断课程（未指定课程时的兜底）
│   └── <课程名>/          具体课程文件夹
│       ├── course.md              课程大纲
│       ├── progress.md            学习进度
│       ├── lesson_state.md        课节状态
│       ├── reading_plan.md        教材分片计划
│       ├── book_revision_notes.md 教材修订+教师补充
│       ├── knowledge_map_state.json  知识地图状态（JSON）
│       ├── materials/             原始教材
│       └── transformed/           生成的教案
│
├── course_inbox/          ← 教材投递箱
├── card/                  ← 闪卡
├── 方案箱/                ← 方案与回答
│   ├── claude的方案.md    AI 的方案输出
│   └── 回答.md            用户对方案的回复
└── 问题箱.md              ← 用户待办事项
```

---

## 运作流程

1. 用户说「上学」或「上课」→ 运行 `scripts/map.py`
2. map.py 导航到场景 → 写入 `scripts/current_scene.json` → 退出
3. AI 启动时检测到 scene 文件 → 按 CLAUDE.md 联邦路由表加载 → 删除 scene 文件
4. AI 上课（苏格拉底式教学）
5. 「下课」→ 总结 + 制卡询问 + 课后更新（CLAUDE.md 处理）

---

## 上课时必读

| 顺序 | 文件 | 内容 |
|------|------|------|
| 1 | `teacher/system.md` | 文件分工表 |
| 2 | `teacher/system_detail.md` | 苏式教学细则 |
| 3 | `teacher/teacher_profile.md` | 通用教学框架 |
| 4 | `characters/<角色名>/<角色名>.md` | 角色卡 |
| 5 | `teacher/course_folder_protocol.md` | 课程匹配协议 |
| 6 | `teacher/learner_profile.md` | 学习者画像 |

### 按需加载

| 条件 | 加读文件 |
|------|---------|
| 同学陪读 | `teacher/classroom.md` + 夏音角色文件 |
| 课后辅导模式 | `supplement_tutoring.md` |
| 课后更新 | `after_class_update.md` |
| 教材改写 | `textbook_transform.md` |
| 首次见面/用户要求 | `character_backstory.md` |
| 无对应课程 | `course_inbox_protocol.md` |

---

## 角色系统

采用**卡片式**结构：角色卡（核心信念、反差触发、经典话术、禁止事项）+ 背景故事（仅首次加载）。

澪的情感表达：不直接"说"，只通过节奏和语气"漏"。交流会上对学生提问的印象 → 三个月后在名单上认出他 → 接了这个学生。见 `character_backstory.md`。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `map.py` | 终端交互式地图，Rich UI。数字键导航，选场景后写 scene 文件退出 |
| `map_server.py` | HTTP 服务器（127.0.0.1），浏览器可视化：知识地图 Canvas + 闪卡复习 + 课程进度 |
| `build_knowledge_map.py` | 从 knowledge_map.md 生成 knowledge_map_state.json 骨架 |
| `recommend_node.py` | 找出薄弱节点，按影响面排序推荐 |
| `update_knowledge_map.py` | 课后扫描 lesson_state + reading_plan，更新节点状态 |
| `_shared.py` | 共享函数，消除跨脚本代码重复 |

---

## 输出规范（上课用）

- 小结限 3-5 条新结论
- 追问一个问题时不嵌解释
- 课后更新一次性完成，不逐条确认
- 上课不提"系统""文件""模块""角色设定""提示词"
