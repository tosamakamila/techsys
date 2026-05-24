# 迷你课复习协议

知识地图驱动的轻量复习模式，在自习室触发。

## 加载规则

在正课启动流程基础上调整：

保留：`system_detail.md` → 角色卡 → `learner_profile.md`
跳过：`course_folder_protocol.md`（不需要课程匹配与长教材分片）
跳过：`templates/textbook_transform.md`（不生成新教案）
新增：本文件
按需：`classroom.md` + 夏（若 classmate=true）

## 前置检查

1. 读取 scene 中的 course 字段，确认课程文件夹存在
2. 检查 `knowledge_map_state.json` 是否存在 → 存在则知识地图推荐模式，不存在则退化模式（见末尾）

## 知识地图推荐模式

### 0. 启动推荐

```
python scripts/recommend_node.py courses/<课程名> --json --top 5
```

解析 JSON，取第 1 个推荐节点。若 `recommendations` 为空 → 告知学生"目前没有检测到薄弱节点，你想复习哪个部分？"

### 1. 定位卡点（1-2 轮）

从推荐节点的 `stuck_detail` 了解卡住表现。用简短诊断问题确认卡点是否仍然真实：
- 已想通 → 标记稳固，跳到第 4 段
- 仍卡 → 进入第 2 段

### 2. 针对性重讲（3-5 轮）

- 从 `depends_on` 中挑稳固节点做锚点
- **换全新类比/例子**（不用正课讲过的）——避免"上次讲过了你还不会"的氛围
- 苏式追问推进，节奏比正课快——复习不是新学
- 最多 3-4 轮后做一句小结固定
- 若 5 轮后依然卡住 → 换策略（类比→反例，构造→对比），记录到 `stuck_detail`

### 3. 换例验证（1-2 轮）

给结构相似但情境不同的新例子，学生独立分析，不给提示。
- 正确推理 → "已修复"
- 需少量提示 → "仍不稳"
- 无法推理 → "仍卡住"，记录本次策略

### 4. 修复后处理

#### 4a. 更新知识地图

1. 将修复/未修复结论追加到 `lesson_state.yaml` `conclusions`：
   ```
   - [复习修复] X 概念：已能正确区分 Y 和 Z（换 B 例子后打通）
   - [复习仍卡] X 概念：理解定义但无法迁移到新场景
   ```
2. 运行 `python scripts/after_class.py courses/<课程名> --km-only`（仅更新知识地图）

#### 4b. 复习链串联

询问："这个点清楚了。下一个是 [节点名]，继续还是今天先到这里？"
- 继续 → 重新运行 `recommend_node.py --json`（state 已更新），取新 Top 1 回到第 1 段
- 停下 → 下课流程
- 最多串联 3 个节点，第 3 个结束后建议休息

## 课堂规则调整

- 节奏：每段 2-5 轮（正课 5-10 轮），允许比正课更多直接讲解
- 先问再讲——至少试一问确认卡在哪里，再快速点破
- `system_detail.md` 的深度教学策略、问题设计、讲解边界、对话风格在复习课中继续适用
- 不适用：课堂节奏六段式 → 替换为本协议三段式；课前定位 → 知识地图已定位；有限诊断 5 分钟入题 → 复习不需要重新入题

## 下课流程（复习课简化版）

### 1. 总结 + 制卡询问

"今天复习了 X、Y、Z。X 没问题了，Y 还需再练。——复习中有几个易混淆的点，要加到闪卡吗？"（同意→写入 `card/<课程名>/card_material.md`）

### 2. 课后更新（仅更新以下文件）

- **lesson_state.yaml**：更新 conclusions + stuck + next_suggestions
- **reading_plan.md**（脚本执行）：`python scripts/after_class.py courses/<课程名> --fragment <片段ID> --status 已上课 --review`（仍卡住→`--status 需复习`）（已含知识地图更新，无需单独执行）
- **progress.md**（一行复习记录）：`复习日期：YYYY-MM-DD | 节点：X(修复), Y(仍不稳) | 策略：换用Y类比后打通`
- **learner_profile.md**：同正课记忆压缩规则（≥2 次才写入）
- **跳过**：book_revision_notes.md、diary.md

### 3. 制卡（如在总结时同意）

按 `after_class_update.md` 第 7 节标记格式写入。

## 退化模式（无 knowledge_map_state.json）

1. 读取 `lesson_state.yaml` `stuck` + `progress.md` 归档
2. 都空 → 问学生"想复习哪个部分？"
3. 手动三段式：定位卡点 → 针对重讲 → 换例验证
4. 下课前提议："要不要帮你建一个知识地图？那样下次复习会更系统。"

## 禁止事项

- 不把复习课上成正课——不重新推演，不引入新概念
- 不用正课讲过的例子
- 不推进 reading_plan.md 当前读取位置
- 不修改教材文件（materials/、transformed/、book_revision_notes.md）
- 不因轻量丢失苏式追问内核——先问再讲
