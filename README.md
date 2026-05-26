<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║  🏛️  SUGELADI — 苏格拉底式 AI 伙伴共学系统                    ║
║  不喂答案。推推理支点、追思维误区、把理解钉进长期记忆              ║
╚══════════════════════════════════════════════════════════════╝
```

[![Claude Code](https://img.shields.io/badge/Powered_by-Claude_Code-6b4c3b?style=flat-square)](https://claude.ai/code)
[![License](https://img.shields.io/badge/License-MIT-8ab88a?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-c99b45?style=flat-square)](https://github.com/tosamakamila/My-Socratic-Tutoring-System)

</div>

---

## LLM 能秒答，但回答 ≠ 学会

AI 扔给你一个答案——你读完了、点头了、第二天忘了。这不是你的问题，是**"被告知"和"自己推出"的记忆深度差了一个数量级**。

这个系统做的事：

| 常规 LLM 用法 | 这个系统 |
|---------------|----------|
| 直接给答案 | 给你推理支点，等你跨过来 |
| 一问一答即结束 | 追着你的误区连环追问，直到那声"啊" |
| 聊完就没了 | 知识地图 + 闪卡间隔复习，**再也没忘** |
| 网页 UI 束缚 | 终端沉浸上课 + Web 可视化双通道 |

---

## 三个机制，各管一段

### 🧠 苏格拉底引擎 — 管"理解"

5 级渐进引导（S5→S1）。从开放推演开始，卡住了自动降级：给类比 → 给线索 → 缩小范围 → 终极兜底才直接讲。

**理解层过关了，才给卷面标准答案。** 两步不可颠倒——先懂再记，不是先背再想。

### 🗺️ 知识大陆 — 管"看见"

所有知识点渲染成一张**维多利亚风 Canvas 地图**。力导向布局、依赖箭头、战争迷雾。你一眼能看到：为什么这个节点卡住了、下游哪些跟着崩、哪条路径是最短修补路线。

<sub>Canvas 2D 手绘 | 河流/山脉/森林/宝箱地形 | 粒子流动 | 6 种节点状态资产</sub>

### 🃏 闪卡系统 — 管"记住"

考什么、怎么出题、阅卷人按什么给分、往届学生掉过什么坑——每张卡都按**考试标准**设计。SM-2 间隔复习算法驱动，过关出池，不浪费复习时间。

---

## 终端 + Web 双通道

| 做什么 | 用什么 | 为什么 |
|--------|--------|--------|
| 上课 / 复习 | 终端（Claude Code） | 沉浸对话，零 UI |
| 看地图 / 进度 / 闪卡 | Web 面板 | 可视化仪表盘 |
| 选课 / 切角色 | 终端 daemon | 零 token 菜单 |

上课时说"上课"，复习时说"闪卡复习"，看面板就启动 `python web/knowledge_panel.py`。**人不该适配系统。**

---

## 一眼看懂

```
sugeladi/
├── CLAUDE.md                   ← 联邦路由表
├── teacher/                    ← 教学内核（system + 细则 + 角色 + 模板）
│   ├── characters/                角色 = profile.yaml + scenes/
│   └── dialogue_reference/        对话写作参考
├── function/                    ← 功能脚本
│   ├── scripts/                   map / daemon / 课后更新 / 知识地图构建
│   └── card/                      闪卡（制卡规则 + 素材 + 复习算法）
├── web/                         ← Web 可视化面板（独立）
│   ├── knowledge_panel.py         Canvas 知识地图 + 闪卡 + 进度 + 统计
│   ├── chat_panel.py              群聊面板
│   └── templates/                 HTML/CSS/JS + 资产
├── courses/                     ← 课程（教材 + 进度 + 画像）
└── log.md                       ← 变更日志
```

---

## 快速开始

```bash
# 上课 —— 终端中直接说
上课

# Web 面板 —— 地图 / 闪卡 / 进度 / 统计
python web/knowledge_panel.py      # → http://127.0.0.1:8765

# 导航菜单 —— 选角色 / 选课 / 选场景
python function/scripts/map_daemon.py

# 闪卡复习
闪卡复习                            # 终端直接说，或在 Web 面板操作
```

> Claude Code + Python 3.11+。`pip install pyyaml`。

---

## 设计哲学

> **"教材即教案。"** 不生成二次加工文件。AI 看到的就是学生看到的。

> **"记忆比回答重要。"** LLM 的回答是瞬时的。变成长期记忆，靠的是间隔重复、锚点框架、错误对照。

> **"人不该适配系统。"** 你想终端就终端，想看可视化就看可视化。选谁、切什么、怎么复习——你定。

---

<div align="center">

### ⭐ 如果它让你想起了某个值得更好的学习方式

<sub>MIT · 一个人做的，欢迎 Issue 和 PR</sub>

</div>
