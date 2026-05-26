# 课程文件夹

每门课一个子文件夹，独立维护教材、进度、教案和状态。

## 标准结构

```
courses/<课程名>/
├── course.md                  ← 课程大纲（首次建课时读）
├── progress.md                ← 学习进度
├── lesson_state.yaml          ← 课节状态（完整归档）
├── lesson_entry.yaml          ← 课节入口（上课只读这个：fragment + 卡点 + entry_line）
├── learner_profile.md         ← 学习者画像（按课程独立）
├── reading_plan.md            ← 教材分片计划
├── book_revision_notes.md     ← 教材修订 + 教师补充
├── knowledge_map.md           ← 知识地图骨架（手动定义）
├── knowledge_map_state.json   ← 知识地图状态（脚本自动更新）
├── materials/                 ← 原始教材
├── transformed/               ← 已弃用（教材即教案，直接按 materials/ 原文推进）
└── notes/                     ← 课堂笔记
```

## 现有课程

| 文件夹 | 说明 |
|--------|------|
| `_template/` | 新建课程模板（复制使用） |
| `_general/` | 通用兜底课程 |
| `动物生理学/` | 动物生理学（最完整，含知识地图 + 教案） |
| `uv/` | UV 课程 |

## 上课机制

课程文件通过 `map.py --preload` 打包到 `function/scripts/state/_preload.json`，AI 一次读取直接开场。详见根目录 `CLAUDE.md` 和 `README.md`。
