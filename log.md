# 系统审计开发日志

### 启动效率优化
- `map.py` 新增 `--go` 参数：跳过导航 UI，读取 `map_state.json` 直接写 scene 文件退出（~55 行）
  - 支持 `--mode` 覆盖教学场景类型（teaching/tutoring/review_with_teacher 等）
  - 支持 `--course` 换课：`--go --course uv`
  - 6 种边界情况处理：无记录/老师不存在/课程不存在/位置无效/mode 无效/条件不满足
- `map.py` 新增 `--server` 参数：子进程启动 `knowledge_panel.py`（~25 行）
  - 端口占用时自动尝试下一个（最多 5 次）
  - 可与 `--go` 组合：`--go --server` 一键进课堂+面板在线
- 去除未使用的 `threading` import
- `load_state()` 默认仅恢复位置，不恢复老师/课程（每次 map.py 干净启动）
- 教室菜单分层：未选课时隐藏上课/辅导选项，已选课后显示 + "换课程"
- `map_server.py` → `knowledge_panel.py` 重命名，更新全部引用（8 个文件）
- map.py 启动时 + 放学时清理残留 `current_scene.json`
- `show_course_submenu()` 新增"其他课程"选项：手动输入课程名，AI 从 course_inbox/ 匹配建课
- `write_scene_file()` 和 `validate_state()` 兼容不在 courses/ 中的自定义课程名
- 删除测试数据 `courses/动物生理学/`

### 迷你课（复习模式）实现
- 新建 `teacher/templates/review_lesson.md`（~150 行）：定义三段式复习循环（定位卡点→针对性重讲→换例验证）
  - 知识地图推荐模式：跑 recommend_node --json，按影响面排序薄弱节点
  - 复习链串联：修完一个节点→刷新 state→重新推荐→询问继续/停下，上限 3 个节点
  - 简化下课流程：总结 + 制卡询问 + 仅更新 lesson_state/reading_plan(标记)/progress(一行)，不推进课程进度
  - 退化模式：无 knowledge_map_state.json 时从 lesson_state 卡点入手
  - 加载规则：正课启动流程跳过 course_folder_protocol.md 和 textbook_transform.md
- `recommend_node.py` 添加 `--json` 输出选项：结构化 JSON 含 status_summary + recommendations（含 depends_on/needed_by），供 AI 解析
- `CLAUDE.md` 更新 3 处：scene 分发 review_with_teacher 行、按需加载增加复习课条目、新增「复习课下课」节
- `teacher/system.md` 更新文件分工表：新增 review_lesson.md 行，course_folder_protocol.md 标注"复习课跳过"

## 2026-05-22：系统架构重构（联邦路由表 + 脚本去重 + 角色卡片化）

### CLAUDE.md 联邦路由表改造
- 从 238 行瘦身到 109 行
- 删除「动作系统（场景路由）」全部面板（~150 行）——场景切换改由 map.py 处理
- 删除「修改代办协议」——待后续重新设计，方案改写到方案箱
- 保留：场景文件触发、上课启动流程、课程匹配、授课要求、输出节流、下课/放学流程
- 新增路由表：触发条件 → 行为映射

### 脚本层重构
- 新建 `scripts/_shared.py`：提取 4 个共享函数（scan_courses, scan_characters, compute_transitive_impact, concept_match）
- `map.py`：删除重复的 scan_courses/scan_characters（-70 行），删除死代码 SYSTEM_ACTIONS
- `knowledge_panel.py`：删除重复的 scan_courses，删除空注释块，parse_qs 改用标准库 urllib.parse，HTML 分离到 `scripts/templates/index.html`（-967 行内嵌）
- `recommend_node.py`：compute_transitive_impact 改为从 _shared 导入（-17 行）
- `update_knowledge_map.py`：compute_transitive_impact 和 concept_match 改为从 _shared 导入，concept_in_stuck 简化为 1 行

### 角色文件卡片化
- `hoshino_mio.md`：96 行 → 72 行，去重退塾背景（已在 backstory），精简为卡片式结构
- `character_backstory.md`：59 行 → 72 行，增强交流会心动线（加"笔记本上画星号线"伏笔、"三个月后"章节强化命运感），删除不可表现的习惯（咖啡、老番、便利店小票），二次元表现改为用词/语气导向
- `supplement_tutoring.md`：不变

### teacher 文件夹清理
- `system_detail.md`：更新触发词描述（不再列出具体触发词，改为引用 map.py + CLAUDE.md 路由），同学陪读触发词改为引用 map.py
- `classroom.md`：删除自然语言触发词列表（"找个同学一起上课"等 5 条），改为引用 map.py 场景选择
- `system.md`：更新文件分工表（加入 scripts/ 相关文件）
- `textbook_transform.md`：280 行 → 110 行，删除从未使用的 12 字段教案模板（~130 行），保留分片策略核心 + 精简教案格式 + 困难章预警
- `after_class_update.md`：learner_profile 更新加入"记忆压缩"机制（1次不提/2次观察/3次压缩为特征/5次稳定特征）

### 分片策略微调
- `_template/reading_plan.md`：加入「困难章节预警」表，困难章行数 > 350 建议 ≥3 课时
- 难度说明更新：困难章行数 > 350 时标注建议

### .gitignore
- 新建：排除问题箱.md、responseto问题箱.md、todo.md、__pycache__/、*.pyc、运行时 json

## 2026-05-21：教学 Tab + 文件桥接（HTML ↔ Claude 通信）

在 knowledge_panel.py 中新增「教学」Tab，实现 HTML 与 Claude Code 之间通过 JSON 文件进行教学对话。

### 新增

- **教学 Tab**：第五个 Tab，包含聊天消息区和输入框
  - 消息气泡：老师（左侧暗色）、学生（右侧绿色）、系统（居中斜体）
  - 自动轮询检测老师回复（1.5s 间隔）
  - Enter 发送，Shift+Enter 换行
  - 触发教学场景后自动切换到教学 Tab
- **后端 API 端点**：
  - `POST /api/teaching/start`：初始化 conversation.json
  - `POST /api/teaching/student-input`：写入 pending_input.json + 追加学生消息到 conversation.json
  - `GET /api/teaching/status?since=`：检测是否有新的老师回复
  - `GET /api/teaching/conversation`：返回完整对话记录
- **对话管理函数**（文件桥接层）：
  - `load_conversation()` / `save_conversation()` / `write_pending_input()` / `check_teacher_response()`

### 通信流程

```
学生输入(HTML) → pending_input.json → Claude 读取
Claude 回复 → conversation.json → HTML 轮询显示
```

终端仅输出简短状态（「已回复」），教学内容只显示在 HTML 中。

### 修改文件

- `scripts/knowledge_panel.py`：新增教学 Tab（CSS + HTML + JS）、4 个 API 端点、对话管理函数
- `CLAUDE.md`：「场景文件触发」节新增「文件桥接模式」小节，定义 pending_input.json 优先检查、文件输出规则、下课/放学处理

---

## 2026-05-21：网站瘦身 + 知识地图可视化优化

### 任务 1：删除教学 Tab 和文件桥接

用户决定上课回归终端，网站不再承载教学对话功能。

**删除内容：**
- 教学 Tab（CSS 样式、HTML 视图、JS 函数）
- 4 个教学 API 端点（`/api/teaching/start`、`/api/teaching/student-input`、`/api/teaching/status`、`/api/teaching/conversation`）
- 对话管理函数（`load_conversation`、`save_conversation`、`write_pending_input`、`check_teacher_response`）
- `triggerScene` 恢复为弹 toast 提示切回终端
- CLAUDE.md 中「文件桥接模式」小节删除

### 任务 2：知识地图 Canvas 可视化

**新增：**
- Canvas 依赖关系图：节点按章节分列排列，贝塞尔曲线箭头连接依赖关系
- 节点着色：绿=稳固、黄=不稳、红=卡住、灰=未学
- 点击节点 / 推荐项 → 弹出详情面板（状态、前置依赖、被依赖、卡住详情、关联教案）
- 依赖链支持中继跳转（点击前置/后继节点名直接切换详情）
- 图例 + 章节标题标注

**保留：**
- 统计栏（稳固/不稳/卡住/未学 数量）
- 优先复习推荐列表（按影响面排序）
- 全部节点列表

### 修改文件

- `scripts/knowledge_panel.py`：瘦身约 200 行 + 新增 Canvas 知识地图
- `CLAUDE.md`：删除文件桥接模式小节
- `log.md`：本条目

---

## 2026-05-21：DOL 风格 HTML 完整客户端（knowledge_panel.py）

基于用户选择（方案 B：双窗口模式），将 map.py 扩展为完整的 DOL 风格 HTML 客户端。

### 新增/重写

- `scripts/knowledge_panel.py`：完整重写，~800 行。Python HTTP 服务器 + 嵌入式 HTML/CSS/JS。

### 四大视图

| Tab | 功能 | 实现 |
|-----|------|------|
| 地图 | 位置导航、老师/课程选择、场景触发 | JS 状态机 + API |
| 闪卡 | 全部/间隔复习模式，SM-2 算法 | Python 会话管理 + JS UI |
| 知识地图 | 节点状态统计、薄弱推荐、依赖展示 | 读 knowledge_map_state.json |
| 进度 | lesson_state / reading_plan / progress | 读课程文件夹内 Markdown |

### 技术要点

- DOL 暗色羊皮纸主题（CSS 变量体系）
- 侧边栏实时状态 + 课程列表
- 数字键/点击双重操作
- 场景触发 → 写 current_scene.json → 提示切到 Claude Code
- 闪卡后端集成 SM-2 算法和状态持久化
- URL 中文参数解析（urllib.parse）

### 启动方式

```bash
python scripts/knowledge_panel.py          # 自动打开浏览器
python scripts/knowledge_panel.py --port 8765 --no-browser
```

修改文件：`scripts/knowledge_panel.py`（重写）

## 2026-05-21：Python 地图导航脚本（map.py）

基于用户反馈（DOL 游戏的地图移动模式参考），将场景导航从 AI 文字面板中抽离为独立的 Python 终端脚本。

### 新增文件

- `scripts/map.py`：交互式地图导航脚本，约 400 行。使用 rich + msvcrt 实现：
  - 5 个位置（校门口 → 教室门口 → 教室/自习室/图书馆）
  - 数字键导航，无需按 Enter，秒切场景
  - 动态扫描 `characters/` 和 `courses/` 目录
  - 选择教学/聊天场景时写入 `current_scene.json` 然后退出，交给 AI 接管
  - 状态持久化（`map_state.json`），记住上次位置/老师/课程
  - 支持运行子进程（card/review.py）
  - CLI 参数：`--start`、`--teacher`、`--course`、`--classmate`、`--no-state`

### 修改文件

- `CLAUDE.md`：新增「场景文件触发」节和「地图脚本」节，定义 AI 检测到 `current_scene.json` 后的加载流程。原有文字路由保留作为 fallback。

### 设计原则

map.py = 导航层（快速键盘交互），AI = 内容层（教学/聊天），两者的交接通过 `current_scene.json` 完成。

## 2026-05-21：面板叙述风格改造 + 知识地图路由整合

### 面板叙述风格改造

将所有路由面板从"角色对话念菜单"改为"斜体旁白 + 编号选项"：
- 主菜单上学：选老师面板 + 选场景面板 → 旁白
- 去教室 / 上课：模式面板 → 旁白
- 去自习室 / 复习：复习方式面板 → 旁白
- 去找夏音：活动面板 → 旁白，选择后角色自然回应

原因：角色（澪、夏音）被当成系统UI来念菜单选项，削弱角色感。现在系统面板用旁白叙述，角色对话仅在进入教学/互动后出现。

### 知识地图路由整合

新增「知识地图路由」节，打通「去自习室 → 老师带着复习 → 知识地图推荐 → 迷你复习课」完整链路：
- 检查 state.json → 运行 recommend_node.py → 展示薄弱节点 → 用户选节点 → 读教案 → 苏式迷你复习
- 无知识地图时回退到苏式自由复习
- 路由规则新增第 7、8 条
- 课后辅导路径中知识地图作为老师后台参考（查影响面决定是否深补）

### 下课流程增强

下课流程插入第 4 步「知识地图更新」：课后更新完成后自动运行 update_knowledge_map.py，有变更则简要告知用户，无变更静默完成。

修改文件：`CLAUDE.md`

## F1（致命）：课后辅导加载集缺失关键文件

### 问题
CLAUDE.md 中「去教室 → 课后辅导」分支原本只加载 `system.md + teacher_profile.md + reading_plan.md + progress.md`，缺少三个文件：

- **system_detail.md** — 包含苏格拉底式教学细则、课堂节奏、问题设计策略、讲解边界条件、课后更新规则。不加载它，老师在课后辅导中失去全部教学行为规范，变成普通 ChatGPT。
- **course_folder_protocol.md** — 包含课程匹配、长教材分片、课后更新写回规则。不加载它，课后辅导不知道如何正确更新课程文件。
- **learner_profile.md** — 包含学习者背景、已知薄弱点、有效/无效教学策略。不加载它，课后辅导对学生一无所知。

### 修复
改为「按上课启动流程加载全部全局文件」，和正常上课完全一致。

### 如果没修
用户选课后辅导后，老师没有教学框架约束、没有学习者画像、没有课程匹配规则。教学会降级为通用 AI 对话——缺乏苏式追问风格、不知道学生薄弱点、课后更新可能写错地方。

### Token 影响
课后辅导多了3个全局文件的加载（约增加 3000-4000 token），但这是必要的——少了这些文件，课后辅导的质量损失远大于 token 节省。

---

## M1：「开始上课」不在路由表

### 问题
`system_detail.md`（第5行）、`system.md`（第50行）、`classroom.md`（第24行）三处都把「开始上课」当作有效触发词，但 CLAUDE.md 的路由表中没有它。如果用户说「开始上课」，CLAUDE.md 没有匹配规则，系统可能不启动或行为不确定。

### 修复
在 CLAUDE.md 去教室触发词列表中补上「开始上课」，行为等同于「上课」——直达正常上课，跳过面板。

### 如果没修
用户说「开始上课」时，CLAUDE.md 没有路由到教学系统。虽然 system_detail.md 里有提及，但 CLAUDE.md 是项目级最高优先级指令，缺了这个触发词意味着路由链断裂。

### Token 影响
无。一个词的触发映射，不影响任何加载量。

---

## M2：「进入老师模式」不在路由表

### 问题
同 M1，`system_detail.md` 第5行列出了「进入老师模式」作为触发词，但 CLAUDE.md 完全没提到它。这是用户早期使用的触发词。

### 修复
在 CLAUDE.md 补上，行为等同于「上课」——直达正常上课。

### 如果没修
用户用这个旧词无法启动系统老路径不通畅，虽然还有别的词可用。

### Token 影响
无。

---

## M3：「考考我」「费曼模式」无定义行为

### 问题
CLAUDE.md「去找夏音 → 一起学习」子面板中，「考考我」和「费曼模式」被列为可选但没有任何地方定义：选择后加载什么文件、行为流程是什么。如果用户选了，系统不知道做什么。

### 修复
将三个选项都标为（待实现），统一状态。

### 如果没修
用户选「考考我」后，没有预设行为——可能产生幻觉或无效响应，影响信任度。

### Token 影响
无。标记为待实现后，用户选择时直接告知未开放，零额外加载。

---

## M4：`session_archive.md` 死引用

### 问题
`after_class_update.md` 中有两处提到「旧 session_archive.md」——暗示这是一个之前存在的文件格式，需要将内容迁移到 `progress.md`。但当前整个项目中不存在 `session_archive.md` 文件，`course_folder_protocol.md` 的推荐结构也从未包含它。

### 修复
删除这两处遗留说明。

### 如果没修
每次课后更新时，会想去找一个不存在的文件做迁移，造成困惑或无效操作。虽然不会崩溃，但浪费推理步骤和 token。

### Token 影响
轻微减少——少了两句不必要的指令文本。更重要的是消除了可能的困惑循环。

---

## M5：「继续上课」「今天学习」无行为映射

### 问题
两个触发词被列在路由表中，但没有明确说明它们的行为是「直达正常上课」还是「弹出面板」。「继续上课」语义上应该直接上课（学生想继续之前的内容），但缺乏显式定义。

### 修复
明确为直达正常上课，与「上课」行为一致。

### 如果没修
可能导致不同情况下行为不一致——有时直接上课、有时弹出面板，用户体验不稳定。

### Token 影响
无。

---

## M7：`teacher/progress.md` 死引用

### 问题
`course_folder_protocol.md` 第83行：`不要把某一门课的进度写入 teacher/progress.md`。该文件不存在，整句话的目标对象是空的，失去了警告意义。

### 修复
改为 `不要把某一门课的进度写入 teacher/ 全局目录。所有课程进度始终写回 courses/<课程名>/progress.md`。从「禁止写到一个不存在的文件」变成「明确写回正确位置」。

### 如果没修
警告存在一个不存在的文件，表述模糊。新加课程时可能犹豫进度该写到哪里。

### Token 影响
无。

---

## M8：`diary.md` 路径不明确

### 问题
`system_detail.md`（第128行）和 `after_class_update.md`（第220行）都提到要更新 `diary.md`，但从未说明这个文件的路径——是放在 `teacher/` 下还是 `courses/<课程名>/` 下？uv 课程目录中也从未创建它。

### 修复
两处都明确为 `courses/<课程名>/diary.md`，如果不存在就创建。

### 如果没修
课后更新时可能创错位置，或犹豫应该放在哪。路径不明确每次都多一步判断。

### Token 影响
无。明确了路径后减少了每次判断的开销。

---

## M9：`system_detail.md` 触发词过时

### 问题
`system_detail.md` 第5行的触发词列表还是老版本（「开始上课」「上课」「继续上课」「今天学习」「进入老师模式」），没有提到新体系的「上学」「去教室」「去自习室」「去找夏音」「放学」。

### 修复
将触发词描述同步为新体系，并注明「具体路由由 CLAUDE.md 的动作系统控制」，避免两处重复维护路由规则。

### 如果没修
两个文件之间的触发词体系不一致。虽然 CLAUDE.md 优先级更高，但 system_detail.md 的旧表述可能被误当作补充规则。

### Token 影响
略微减少——避免两处各自维护完整的触发词表。

---

## 总影响评估

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| 课后辅导可用性 | 缺少3个关键文件，教学降级 | 完整加载，和正常上课同等质量 |
| 触发词覆盖率 | 缺3个词，旧用户路径不通 | 全部覆盖，旧词兼容 |
| 死引用 | 3处指向不存在文件 | 全部清理 |
| 待实现功能 | 2个未标记，选了就尴尬 | 统一标注，选了就告知 |
| 文件间一致性 | system_detail.md 与 CLAUDE.md 脱节 | 同步且单点维护 |
| Token 消耗 | 正常上课约 8000-10000 token | 基本不变，课后辅导增加了必要加载 |
| 用户使用 | 存在3条不通路径 | 所有已知路径畅通 |

修复后，系统在最关键的两个维度上补齐了缺口：课后辅导不再「残血」运行，触发词路由不再有漏洞。

---

## 2026-05-20 Token 瘦身方案执行

### 改1：拆分 teacher_profile.md
- 创建 `characters/hoshino_mio/character_backstory.md`（人物背景故事，首次或用户要求时才加载）
- `teacher/teacher_profile.md` 从 ~2788 token 瘦身到 ~750 token，仅保留教学行为规则
- 创建 `characters/` 文件夹体系：`characters/hoshino_mio/` 和 `characters/asakura_natsune/`
- `teacher/characters/asakura_natsune.md` 移至 `characters/asakura_natsune/asakura_natsune.md`
- 原因：每次上课加载的人物叙事脂肪被剥离，省约 1800 token/课

### 改2：system.md 瘦身
- 删除与 CLAUDE.md 重复的最小启动原则、课程选择、课堂原则、课后更新
- 改为文件分工表 + 引用 CLAUDE.md 为权威来源
- 省约 500 token

### 改3：规则去重（交叉）
- 不提系统词汇：权威来源为 CLAUDE.md，其他文件改为引用
- 最小加载：权威来源为 CLAUDE.md
- 苏式循环：权威来源为 system_detail.md
- 课后更新：权威来源为 after_class_update.md
- course_folder_protocol.md 中重复内容改为一行引用

### 改4：system_detail.md 压缩
- 删除"暂不启用模块"节（移至 todo.md）
- 流程、策略、问题设计各节压缩为编号/列表形式
- 闪卡制作改为引用 after_class_update.md
- 省约 1300 token

### 改5+6：CLAUDE.md 瘦身 + 输出节流
- 面板用一行引用格式
- 路由规则压缩
- 新增「输出节流」节：小结限3-5条、制卡一次性完成、追问不嵌解释、课后更新只写结论

### 新增文件
- `todo.md`：集中记录待实现功能和暂不启用模块
- `characters/hoshino_mio/character_backstory.md`：人物背景

### 预估效果
每节课开局加载从 ~10322 token 降至 ~5700 token，省约 45%。

---

## 2026-05-20 修改代办协议更新：提案→审查→执行三段式

- CLAUDE.md「修改代办协议」拆为「提案阶段」和「执行阶段」。
- 新增规则：讨论中涉及项目修改时，先写成提案写入 `问题箱.md`，等用户审查决策后再执行。不直接动手改。
- 同步更新 memory 中的 feedback_revision_protocol。
- 原因：用户要求所有修改方案先经过审查再执行，确保对项目变更有最终决策权。

## 2026-05-20 修正：问题箱+答复箱改为覆写模式

- 用户澄清：`问题箱.md` 和 `responseto问题箱.md` 均由用户覆写（非追加），每次干净独立。
- 两个文件可跨对话携带——用户在另一对话改好，回来触发「修改代办」即可执行。
- 更新 CLAUDE.md 和 memory，去掉「提案阶段」（我不写问题箱），统一为简短的执行流程。

---

## 2026-05-21：教案与课后总结优化方案实施

按问题箱决策，实施了6项方案：

**方案1 — progress.md 去重**：`progress.md` 模板和 `after_class_update.md` 中删除"学生亲自推出来的结论"字段，结论统一由 `lesson_state.md` 的"已建立的结论"维护。

**方案2 — 闪卡原材料改为标记清单**：`after_class_update.md` 第7节完全重写。card_material.md 从"完整答案型"改为"标记清单型"（只记为什么值得制卡、关键得分点≤3条、常见错误）。写入触发改为下课询问后执行。

**方案3 — 教材补充→闪卡闭环**：`book_revision_notes.md` 模板增加"建议制卡"和"制卡原因"字段。`after_class_update.md` 第6节增加下课时扫描 book_revision_notes 纳入 card_material 的闭环说明。

**方案4 — 分片粒度+教师补充教材**：
- `reading_plan.md` 模板增加"预估课时"和"难度"列，新增难度说明表。
- `textbook_transform.md` 核心原则增加第6条（教师补充教材），新增"教师补充教材"专节。
- `book_revision_notes.md` 模板增加"教师补充内容"字段，老师可直接撰写教材缺失的知识点。

**方案5 — 课后更新去重**：被方案1完全覆盖，不额外改动。

**方案6 — 下课增加制卡询问**：`CLAUDE.md` 下课流程在总结后、课后更新前插入第2步"制卡询问"。学生同意才写 card_material.md。

涉及文件：`CLAUDE.md`、`teacher/templates/after_class_update.md`、`teacher/templates/textbook_transform.md`、`courses/_template/progress.md`、`courses/_template/reading_plan.md`、`courses/_template/book_revision_notes.md`。

---

## 2026-05-21：澪的人物背景重写

重写了 `characters/hoshino_mio/character_backstory.md` 中"开学前：与陈的初次交集"一节。

旧版是便利店偶遇（碰掉冰淇淋→买 Pocky）——用户认为潦草、无趣、无用。

新版改为：三个月前理学部交流会上，澪观察到陈在台下问了一个直击要害的问题（"可解释性到底解决了什么实际问题"），被讲者绕过去后他不再追问，但那个自己消化的表情让她想起高二退塾后的自己。三个月后他的名字出现在学生列表上，她接了。第一节课时陈不知道她当时在场。

改动效果：相遇从随机事件变为基于判断的选择。澪对陈的关注不再是巧合，而是她在他身上看到了自己曾经的样子。情愫的种子埋在她的观察和选择里，而不是外部事件里。

---

## 2026-05-21：人物系统架构重构——通用教学框架 + 角色人格分离

按问题箱决策，将教师角色从通用教学框架中分离：

**新增文件：**
- `characters/hoshino_mio/hoshino_mio.md`：澪的主人格文件。整合人物底色、教学人格（反差触发、说话方式、教学信念）、对陈的情感（行为绑定的触发规则表）、禁止事项。
- `characters/hoshino_mio/supplement_tutoring.md`：课后辅导模式补充文件。仅在课后辅导时加载。定义澪在一对一近距离环境中的潜意识身体意识（靠近→退开、手指碰到→缩回、想碰肩膀→收手敲笔记本）。触发不超过每课 2 次，表达通过动作中断而非内心独白。学生视角不可察觉。

**重写文件：**
- `teacher/teacher_profile.md`：从澪专属档案重写为通用教学框架。保留苏式教学核心（四类问题、教学节奏）、情绪应对、沉浸边界、通用禁止事项。澪专属内容（反差触发、说话方式、教学信念、人物背景）全部迁移至 `hoshino_mio.md`。

**修改文件：**
- `CLAUDE.md`：
  - 主菜单新增老师选择面板（"今天哪位老师来上课？" 1. 星野澪 2. 待加入），为未来多老师框架做准备。
  - 「上课」「去教室」等触发词均先弹老师选择面板，再按原有逻辑路由。
  - 上课启动流程增加角色文件加载（第4步：`characters/<角色名>/<角色名>.md`）。
  - 课后辅导分支增加补充文件加载（`characters/<角色名>/supplement_tutoring.md`）。

**设计意图：** 通用教学能力（怎么问问题、怎么应对情绪）与具体人物（谁在教、她什么性格、她对学生的情感）彻底分离。新增老师只需创建 `characters/` 下的文件夹，无需改动教学框架。

---

## 2026-05-21：创建 README.md

创建项目总览文件，涵盖：目录地图、文件加载规则、动作系统触发词、角色系统结构、课程文件协议、闪卡系统、修改代办协议、输出规范。原因：系统文件增多，用户需要快速查阅的入口。

---

## 2026-05-21：知识地图系统——第一阶段实现

按问题箱讨论决策，实现了知识地图的核心骨架和脚本系统。

**设计决策（用户确认）：**
- 师生双视图（老师完整诊断版，学生简化进度版）
- 按章网络状分布，概念为节点，依赖关系为边
- 骨架手动定义（`knowledge_map.md`），状态脚本自动更新（`knowledge_map_state.json`）
- 迷你课 = 复习模式（去自习室 → 老师带着复习），知识地图告诉老师"补什么"
- 依赖关系双向自动推导：老师只填"前置依赖"，`needed_by` 由脚本自动计算

**新增文件：**
- `scripts/build_knowledge_map.py`：从 knowledge_map.md 解析节点表格，自动推导双向依赖，生成 state.json 骨架。已存在 state.json 时保留已有状态，仅更新新增/删除节点。
- `scripts/update_knowledge_map.py`：下课后扫描 lesson_state.md（已建立结论+卡住问题）和 reading_plan.md（片段状态），自动判定每个节点状态（稳固/不稳/卡住/未学），打印变更摘要。
- `scripts/recommend_node.py`：从 state.json 找出薄弱节点，按传递影响面（直接+间接后继节点数）排序推荐 Top 3。
- `courses/动物生理学/knowledge_map.md`：第1章绪论的骨架定义（13个概念节点，含前置依赖关系）。
- `courses/动物生理学/knowledge_map_state.json`：由 build 脚本自动生成的状态文件。
- `courses/动物生理学/lesson_state.md`：模拟课后数据（10条结论 + 3个卡住问题）。
- `courses/动物生理学/reading_plan.md`：模拟课后数据（L001已上课）。

**实测结果（动物生理学第1章模拟数据）：**
- 状态分布：稳固6 / 不稳6 / 卡住1
- 推荐 Top 3：ch01-08 体液调节[卡住，影响4个后继] → ch01-04 兴奋性演变[不稳] → ch01-02 急性/慢性实验[不稳，末端可延后]

**Token 优化设计：**
- 骨架 markdown 只在建课/编辑时读（低频，~3-5K token）
- 日常查看地图只读 state.json（高频，~500-1500 token）
- JSON 内置 depends_on/needed_by，推荐脚本不需要回头读 markdown。

---

## 2026-05-21：知识地图 UI 大改 + 地图 Tab 删除

### 背景

用户明确：终端 map.py = 导航层；Claude Code = 教学层；网站 = 知识/进度可视化仪表盘。网站不再需要地图 Tab。

### 删除内容

- **地图 Tab**（HTML/CSS/JS）：位置导航、老师/课程选择、场景触发按钮
- **侧边栏**：课程列表、角色状态显示 → 替换为顶部课程选择栏
- **Python 后端函数**：`scan_characters`、`load_map_state`、`save_map_state`、`write_scene_file`
- **API 端点**：`/api/scene`、`/api/state`
- **JS 状态字段**：`character`、`location`、`state` 从全局 state 移除
- `/api/init` 简化：仅返回 `courses`，不再返回 `characters` 和 `state`

### 网站新结构（3 Tab）

| Tab | 功能 |
|-----|------|
| 📊 知识地图 | Canvas 依赖关系图（主导地位，占视口大部）|
| 🃏 闪卡 | SM-2 算法间隔复习 |
| 📋 进度 | 课堂状态、阅读计划、学习者档案 |

### UI 改动

- **配色**：深灰色系（`--bg: #1a1a1e`，面板 `#222228`），大幅降低对比度
- **布局**：横向长方形（`width: 92vw; max-width: 1400px`），知识地图主导视口
- **课程选择栏**：顶部横条替代原侧边栏，显示当前课程 + 标签，点击弹出选择模态框
- **知识地图 Canvas**：
  - 拓扑分层布局（`computeLayers`）：节点位置由依赖深度决定，而非章节归属
  - 贝塞尔曲线箭头连接依赖关系
  - 高 DPI 渲染（`devicePixelRatio` 缩放，解决字体模糊）
  - 右键拖拽平移（`oncontextmenu` 阻止默认菜单 + `kmPanX/Y` 偏移）
  - 节点点击弹出浮动详情面板（`position:absolute` 覆盖在 Canvas 上方）
  - 详情面板内依赖链可中继跳转（点击前置/后继节点名 → 切换详情）
  - 图例（稳固/不稳/卡住/未学）+ 选中节点高亮
  - 推荐项点击自动定位到对应节点
- **文档字符串**更新为反映网站新定位

### 修改文件

- `scripts/knowledge_panel.py`：~1300+ 行（删除 ~300 行地图/教学代码，新增 Canvas 知识地图 ~200 行）
- `CLAUDE.md`：删除文件桥接模式小节
- `log.md`：本条目

---

## 2026-05-22：角色系统重构（YAML化 + 风格重写 + 重命名）

### 图书馆菜单调整 + 三条交互线明确化
- map.py 图书馆：「选课程」→「学习」（子菜单占位：费曼模式、互相出题，暂未开放）
- 三条交互线分离：
  - 教室「和夏一起上课」→ `teaching` + classmate（灵在场）
  - 图书馆「闲聊」→ `chat`（`library_chat.md` + 夏，不加载灵和 classroom.md）
  - 图书馆「学习」→ `study_together`（chat 基础上 + 课程文件）
- 新建 `teacher/templates/library_chat.md`：图书馆聊天场景指南
- 理由：用户要求三种互动方式各走各的路由，不混淆

### 夏角色重写（神里绫华方向）
- 从通用同学 → 神里绫华式青梅竹马：含蓄细腻，好感藏在日常小动作里
- 新增：青梅竹马背景、日常习惯与小细节、聊天话题偏好
- 说话方式分课堂/闲聊两套
- 理由：用户指定神里绫华为参考方向

### 夏 YAML 化
- 4 个 md 片段（core/backstory/learning/chat）→ 1 个 `xia.yaml`（~100行）
- `scenes:` 字段定义三个场景各加载哪些 section
- 理由：用户觉得 md 太长，要结构化 YAML 人物卡

### 灵全量重写（八重神子方向）
- 风格：清冷话少精准 → 笑眯眯知心大姐姐
- 调侃式追问替代冷脸批评："嗯哼～所以你觉得这样就够了？"
- 情感：神子式——越喜欢越要逗，`teasing_is_affection` 字段定义四类玩笑表达
- 反差切换：收起笑容 = 这里很重要
- 文件：`ling.yaml` + `character_backstory.yaml` + `supplement_tutoring.yaml`（均为 YAML）
- 理由：用户不喜欢清冷话术，要活泼知心大姐姐，参考八重神子

### 角色重命名：灵 + 夏
- 星野澪 → 灵，朝仓夏音 → 夏
- 目录：`characters/ling/` + `characters/xia/`
- 全项目引用更新（CLAUDE.md / system.md / system_detail.md / classroom.md / library_chat.md / map.py / README.md / todo.md / 全部 course 文件）
- `_shared.py`：`scan_characters()` 适配 yaml 优先读取，`supplement_tutoring` 支持 .yaml/.md
- 理由：用户要求名字好打（拼音，4键位）

---

## 2026-05-23：/god 开发者模式 + map.py 编码修复

### /god 开发者模式
- 新增 `scripts/god_mode.json` 状态文件（`{"god_mode": true/false}`）
- `/god` → 写入 true，scene 检测后不加载教学文件，只告知下一步
- `/god` 再触发 → 写入 false，恢复正常
- 修改：`CLAUDE.md`（路由表更新 + scene 分发加入 god_mode 检查）、`memory/feedback_god_mode.md`（新建）、`memory/MEMORY.md`

### map.py 编码修复
- PowerShell 弹窗命令避免 Base64 编码中文（`-EncodedCommand` 要求 UTF-16LE）
- `Read-Host '按 Enter 关闭'` → `pause`

### 日志书写规范
- 明确 `log.md` 追加在末尾，不插最前面（Claude 之前误插顶部）
- 修改：`CLAUDE.md` 变更日志节

## 2026-05-23：God Mode 升级——对话触发 + 三级反馈

### God Mode 从布尔开关升级为分级开发者工具

- `scripts/god_mode.json` 结构从 `{god_mode: bool}` 改为 `{level: "off"|"brief"|"detail"|"trace"}`
- 对话题触发（不用斜杠命令）：
  - 「开发者模式」→ brief、「详细模式」→ detail、「追踪模式」→ trace、「退出开发」→ off
  - 「系统状态」→ 显示位置/老师/课程/知识地图统计/连续天数
  - 「怎么走到这里的」→ 显示路由触发链
- scene 分发逻辑：按 level 给出对应粒度反馈，非 off 时保留 scene 文件不删
- 修改：`CLAUDE.md`、`scripts/god_mode.json`、`方案箱/god_mode升级方案.md`
- 理由：开发时快速获取反馈和定位路由问题，不需要手动翻文件


## 2026-05-24：Token 优化第三轮 — scene 免文件 + 脚本合并 + 对话精简

### #2 scene 文件免读写
- `map.py` 新增 `--stdout` 参数：配合 `--go` 使用时直接输出 scene JSON 到 stdout，跳过写文件→读文件→删文件三步
- CLAUDE.md 路由表更新：「上课」→ `map.py --go --stdout`（捕获 stdout JSON），「上学/换老师/换课程」→ `map.py`（TUI + 文件机制）
- 理由：最常用的续课路径不再需要 scene 文件中转

### #3 下课脚本合并
- 新建 `scripts/after_class.py`：合并 advance_reading.py 和 update_knowledge_map.py
  - 用法：`python scripts/after_class.py courses/<课程名> --fragment Lxxx --status 已上课 [--next Lxxx] [--review] [--tag] [--km-only]`
  - 一次执行同时更新 reading_plan.md 和 knowledge_map_state.json
- CLAUDE.md / after_class_update.md / review_lesson.md 全部引用更新为 after_class.py
- review_lesson.md 删除单独的「刷新知识地图」步骤（已含在 after_class.py 中）
- 理由：下课时一个命令替代两个命令，减少 shell 调用

### #4 课堂对话精简规则
- system_detail.md「对话风格」节新增精简规则：
  - 不叠用表扬词，一个"对"即可
  - 不讲结构性过渡语（"那么接下来..."），直接进入下一问
  - 不用口头禅式引入（"你知道吗...""你有没有想过..."）
  - 小结限 3-5 条短结论，不展开解释
  - 不做三明治反馈（表扬+纠正+鼓励），答对直接追深问
- 理由：AI 生成的教学对话有大量结构性废话和过度表扬

### 撤销默认课程
- 用户明确不需要默认课程，CLAUDE.md 课程匹配规则恢复为「未指定→先询问」
- memory MEMORY.md 索引更新

涉及文件：map.py、CLAUDE.md、after_class.py（新建）、after_class_update.md、review_lesson.md、system_detail.md、MEMORY.md

## 2026-05-24：Token 优化第四轮 — 教学内核搬家 + 读/写分家 + 系统清理

### #1 教学内核搬入 CLAUDE.md（免费 token）
- system_detail.md 的苏式推进循环、深度教学策略、问题设计、讲解边界、对话风格、精简规则全部移入 CLAUDE.md「教学内核」节
- system_detail.md 瘦为 28 行（仅课堂参与者 + 开场/定位/节奏 + 引用）
- 新增精简规则：不描述教学动作（直接做，不说"我来问你一个问题"）
- 理由：CLAUDE.md 自动注入系统提示词不花 Read token，system_detail.md 每次上课要读一次

### #2 lesson_state 读/写分家
- 新建 `lesson_entry.yaml`（fragment/interrupted_at/stuck/entry_line，~10 行）
- course_folder_protocol.md 更新：上课时读 lesson_entry.yaml 而非完整 lesson_state.yaml（~52 行）
- lesson_state.yaml 保留为归档+脚本用（课后读/写）
- 理由：上课只需要 4 个入口字段，省 ~40 行/课

### #3 conclusions 自动截断
- after_class_update.md 新增截断规则：保留最近 3 节课结论，更早的只保留标注 ?/需巩固/待巩固 的条目
- 理由：结论无限累积，3 节课以前的已固化为知识地图节点状态，不需要再读

### #5 技能 + 记忆清理
- skills-lock.json：删除 7 个无关 Vercel 技能（web 部署类，对学习系统无用）
- C 盘记忆合并：auto_launch + silent_exec → feedback_execution.md（4 记忆 → 3 记忆）
- god_mode 记忆更新为当前四级体制
- 理由：清理系统提示词中的噪声技能列表，减少记忆文件索引

涉及文件：CLAUDE.md、system_detail.md、lesson_entry.yaml（新建）、course_folder_protocol.md、after_class_update.md、skills-lock.json、MEMORY.md、feedback_execution.md、feedback_god_mode.md

## 2026-05-24：启动流程精简 — 必读链砍半

### course_folder_protocol.md 移出必读链
- 独特内容（长教材读取）合并入 CLAUDE.md「长教材读取」节
- 其余内容（最小读取、课程匹配、课后更新）与 CLAUDE.md 高度重复
- 文件保留为参考说明，标注"日常上课不再读取"
- 理由：省 45 行/课

### course.md 按需加载
- CLAUDE.md 明确：仅在首次建课或推进到全新章节时加载
- 日常续课由 lesson_entry.yaml + transformed/ 教案定位，不需要课程目标/章节列表
- 理由：省 48 行/课

### learner_profile.md 按课程拆分
- 从 teacher/ 移到 courses/<课程名>/ 下
- 动物生理学新建专属画像：去掉了 Python/conda/uv 工具链内容（与生理课无关）
- teacher/learner_profile.md 改为模板
- CLAUDE.md 必读链：`courses/<课程名>/learner_profile.md`
- 理由：生理课不再加载 Python 工具链画像，每门课独立维护

涉及文件：CLAUDE.md、course_folder_protocol.md、courses/动物生理学/learner_profile.md（新建）、teacher/learner_profile.md、after_class_update.md

## 2026-05-24：项目清理 — 删除废弃文件

### 删除 4 个废弃文件
- `scripts/advance_reading.py`：功能已合并到 after_class.py
- `scripts/update_knowledge_map.py`：功能已合并到 after_class.py
- `characters/ling/ling.md`：旧角色索引，YAML 迁移后零引用
- `characters/xia/xia.md`：旧角色索引，YAML 迁移后零引用

### 更新引用
- CLAUDE.md 静默执行规则：advance_reading.py → after_class.py
- _shared.py docstring：update_knowledge_map.py → after_class.py
- README.md：两处 update_knowledge_map.py → after_class.py

## 2026-05-24：map.py 架构减法 — 拆分 + 终端常驻菜单

### 背景
map.py 1000+ 行融合了 Rich TUI 导航、状态管理、场景交接、知识面板。每次导航弹独立 PowerShell 窗口。用户想要在 VS Code 终端内完成导航，不弹窗、不进聊天上下文。

### 拆分结构
```
scripts/
├── _shared.py          → 扩展（80 → 290 行）：状态管理 + LOCATIONS 移入
├── map.py              → 精简（1020 → 190 行）：纯后端 --go --stdout + --server
└── map_daemon.py       → 新增（200 行）：终端常驻菜单（input+print，无依赖）
```

### _shared.py 扩展
- 移入 AppState、LOCATIONS、load_state、save_state、validate_state、write_scene_file、action_available
- map.py 和 map_daemon.py 共享同一套状态逻辑，避免代码重复
- load_state 参数从 args namespace 解耦为独立参数

### map_daemon.py（新建）
- 纯标准库：input() + print() + ANSI 加粗，无 Rich，无 msvcrt
- 在 VS Code 终端启动一次，常驻不退出
- 完整的导航流程：选老师 → 教室门口 → 选课程 → 进教学场景
- 面包屑返回（b）+ 放学（q）+ 子菜单（老师/课程列表）
- 选 scene 后写文件并退出，用户切回 Claude 面板说「上课」

### map.py 精简
- 删除：全部 Rich TUI 代码（~700 行）、动态氛围函数、按键监听、主循环
- 保留：go_quick()、start_server()、parse_args()、main()
- 增强：--teacher、--location 参数覆盖（--course 已有）
- 无参数时显示用法提示

### 路由更新
- 「上课」→ map.py --go --stdout
- 「上课 ling」→ map.py --go --stdout --teacher ling
- 「换课程 uv」→ map.py --go --stdout --course uv
- 导航 → 终端 map_daemon.py 或 CLI 参数覆盖

### 清理
- settings.local.json 删除 Start-Process 权限
- feedback_execution.md 删除 TUI 弹窗描述
- Rich 依赖不再需要

涉及文件：_shared.py、map.py、map_daemon.py（新建）、CLAUDE.md、settings.local.json、feedback_execution.md

## 2026-05-24：沉浸式体验优化 — preload + 沉浸模式

### map.py --preload 预加载
- 新增 `--preload` 参数：搭配 `--go --stdout` 时，静默写入 `scripts/_preload.json`
- `_preload.json` 含 scene 信息 + 所有启动文件内容（system_detail + 角色卡 + learner_profile + lesson_entry + 教案）
- preload 模式下 stdout 不输出（静默），所有信息通过 _preload.json 传递
- 上课流程从 5-6 次工具调用减为 2 次（1 次静默 PowerShell + 1 次 Read）
- 理由：减少聊天面板中可见的文件读取调用，提升沉浸感

### 首次使用自动创建状态
- 无 map_state.json 时，提供 --teacher 参数即可自动创建状态（不需 daemon）
- 自动导航：--mode 不匹配当前位置时自动跳到支持该 mode 的位置
- 无 --mode 时默认 teaching，自动跳教室
- 错误提示不再引用 daemon，改为引导用「上课 ling」等参数形式
- 理由：用户不需要手动启动 daemon 也能直接上课

### 沉浸模式（god_mode immersive）
- god_mode 新增第 5 级：`immersive`
- 课堂中只输出角色对话和场景描写，零技术信息
- 「停」「下课」直接响应，无确认语
- 下课流程全静默执行，只在需要用户决策时开口
- 触发：「沉浸模式」→ `{"level": "immersive"}`，「退出开发」→ `{"level": "off"}`
- 理由：用户想要纯角色对话体验，不被技术中间步骤打断

### CLAUDE.md 静默规则强化
- 文件加载过程不输出任何说明文字（不列文件清单、不说"正在加载"）
- 路由表更新：上课/复习均使用 --preload --stdout

### README 更新
- 运作流程、上课必读、脚本说明、目录地图同步更新

涉及文件：map.py、CLAUDE.md、README.md、log.md、god_mode.json、feedback_god_mode.md、feedback_execution.md
