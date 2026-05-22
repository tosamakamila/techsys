# 项目级指令

苏格拉底式学习系统：`teacher/`(内核) `courses/`(课程) `course_inbox/`(投递箱)。目标：每次上课只读最小必要文件。

## 路由表

| 触发 | 行为 |
|------|------|
| `scripts/current_scene.json` 存在 | 按 scene 加载（见下），加载后**删除该文件** |
| 「上学」「上课」「复习」「找夏」等 | 运行 `python scripts/map.py`（脚本写 scene 文件后退出） |
| 「下课」「今天到这里」 | 下课流程（见下） |
| 「放学」「走了」 | 直接退出 |

## scene 分发

| scene | 加载 |
|-------|------|
| `teaching` | 上课启动流程。teacher/course 按 scene 字段。classmate=true 时加读 classroom.md + 夏(yaml scenes.teaching) |
| `tutoring` | teaching 基础上 + `supplement_tutoring.yaml` |
| `review_with_teacher` | 上课启动流程（跳过 `course_folder_protocol.md`）+ `review_lesson.md`（三段式复习循环 + 简化下课流程）。按 scene 的 course 字段定位知识地图 |
| `chat` | `library_chat.md` + 夏(yaml scenes.chat)，不加载课程、灵、classroom.md |
| `study_together` | chat 基础上 + 课程文件 + 夏(yaml scenes.study)（图书馆学习模式，费曼/出题等） |

## 上课启动流程

必读：`teacher/system.md` → `system_detail.md` → `teacher_profile.md` → `characters/<角色名>/<角色名>.md` → `course_folder_protocol.md` → `learner_profile.md`

按需：无课程→`course_inbox_protocol.md`，陪读→`classroom.md`+夏，图书馆聊天→`library_chat.md`+夏，课后更新→`templates/after_class_update.md`，教材改写→`templates/textbook_transform.md`，复习课→`templates/review_lesson.md`

## 课程匹配

按 `course_folder_protocol.md` 在 `courses/` 匹配。未指定课程→先询问。选定后只读该课程文件夹。长教材按 `reading_plan.md` 分片读。

## 授课要求

中文授课，苏格拉底式，每次一个主问题。先确认目标再提问。不提"系统/文件/模块/提示词"等幕后词。

## 输出节流

小结限 3-5 条新结论。制卡/课后更新一次性完成。追问不嵌解释。课后更新只写结论和证据。

## 下课

1. 总结：标不稳概念，给下一课建议
2. 询问是否标记闪卡 → 同意则写入 `card/<课程名>/card_material.md`
3. 按 `after_class_update.md` 课后更新，写回课程文件夹；跨课稳定特征→`learner_profile.md`
4. 若 `knowledge_map_state.json` 存在 → `python scripts/update_knowledge_map.py courses/<课程名>`，有变更则告知

## 复习课下课

简化版下课（不走完整课后更新），见 `review_lesson.md`「下课流程」节。

## 变更日志

改系统文件后追加 `log.md`：日期 + 内容 + 原因。
