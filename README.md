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
├── characters/            ← 角色文件（YAML 卡片式）
│   ├── ling/
│   │   ├── ling.yaml                灵的角色卡（八重神子风）
│   │   ├── character_backstory.yaml 灵的背景故事（首次/按需）
│   │   └── supplement_tutoring.yaml 课后辅导补充（辅导模式）
│   └── xia/
│       ├── xia.yaml                 夏的角色卡（神里绫华风）
│       └── xia.md                   索引
│
├── scripts/               ← 脚本层
│   ├── _shared.py         共享函数（scan_courses, compute_transitive_impact 等）
│   ├── map.py             终端交互式地图导航
│   ├── knowledge_panel.py      知识地图可视化面板（HTTP 服务器）
│   ├── build_knowledge_map.py      从 .md 生成 knowledge_map_state.json
│   ├── recommend_node.py           薄弱节点推荐
│   ├── update_knowledge_map.py     课后更新知识地图状态
│   ├── templates/
│   │   └── index.html     knowledge_panel 前端页面
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
| 同学陪读 | `teacher/classroom.md` + 夏角色卡 |
| 课后辅导模式 | `supplement_tutoring.yaml` |
| 课后更新 | `after_class_update.md` |
| 教材改写 | `textbook_transform.md` |
| 首次见面/用户要求 | `character_backstory.yaml` |
| 无对应课程 | `course_inbox_protocol.md` |

---

## 角色系统

采用 **YAML 卡片式**结构：角色卡 + 背景故事 + 场景片段索引（scenes 字段），AI 按场景选取对应 section。

灵：八重神子式知心大姐姐，笑眯眯追问，情感藏在玩笑里——越喜欢越要逗。
夏：神里绫华式青梅竹马，含蓄细腻，好感藏在日常小动作里。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `map.py` | 终端交互式地图，Rich UI。数字键导航，选场景后写 scene 文件退出 |
| `knowledge_panel.py` | HTTP 服务器（127.0.0.1），浏览器可视化：知识地图 Canvas + 闪卡复习 + 课程进度 |
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
