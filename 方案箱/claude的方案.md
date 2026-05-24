# 知识地图幻想风改造方案

## 总体愿景

把知识地图从一个"功能面板"变成一个**冒险者的羊皮地图**——可爱、有探索感、越学越亮。学生在终端上课，在这个页面看自己的冒险进度。

## 视觉参考

- **RoadHub**（RPG 技能树）—— 毛玻璃节点、拖拽交互、暗色底 + 荧光色
- **Azgaar's Fantasy Map Generator** —— 程序化幻想地图、羊皮纸纹理、墨水标注
- **Codex Cryptica** —— 羊皮纸边框、墨渍标记、做旧纹理、战争迷雾
- **Hearthglen UI Kit** —— 羊皮纸/木材/金色镶边的暖色调 RPG 界面

---

## 需要你生成的图片

### 1. 冒险者小人（核心）

一个可爱的 Q 版/chibi 风格小冒险者，背面俯视视角（站在地图上的感觉）：

```
提示词（主图——站立待机）：
A cute chibi adventurer character viewed from behind/top-down perspective,
small round shape, wearing a tiny brown cloak and a pointed wizard hat,
carrying a little wooden staff, kawaii style, simple clean design,
transparent background, soft warm colors, game asset style,
the character should look like they're exploring a magical world,
about 200x200 pixels --
no watermarks, no text, simple flat colors with soft shading
```

如果可以生成同一角色的几个变体姿态（同一张 sprite sheet 更佳）：

| 姿态 | 用途 |
|------|------|
| 站立待机 | 默认停在当前节点上 |
| 迈步前进 | 点击节点后沿路移动 |
| 举手跳跃 | 概念变为稳固时庆祝 |
| 坐下看书 | 在稳固节点旁边 |
| 挠头困惑 | 在卡住节点旁边 |

### 2. 羊皮纸背景纹理

```
提示词：
A dark fantasy parchment paper texture, deep brown-gray tones,
subtle worn edges and stains, very faint decorative border,
old treasure map feel but dark enough for dark-mode UI,
seamless tileable 1024x1024, minimalist, not too busy,
muted earth tones, very subtle grain --
no watermarks, no text, texture only
```

### 3. 可选装饰

**A. 罗盘玫瑰**（地图角落装饰）
```
提示词：
A tiny elegant compass rose, gold line art on transparent background,
simple 4-point star design, fantasy style, 128x128 pixels --
no watermarks, no text, line art only
```

**B. 地图标记图标**（宝藏/旗帜/篝火/卷轴）
```
提示词：
A set of 4 tiny cute fantasy map markers on transparent background:
treasure chest, flag, campfire, scroll,
all simple gold/amber line art, each about 32x32 pixels,
minimalist icons matching a fantasy adventure map --
no watermarks, no text, icons only
```

---

## 技术方案

### 布局：从"分层树"变为"力导向网络"

- 当前：固定 X 轴层级排列
- 改为：力导向布局，节点像神经网络一样自由分布
- 连线像魔法丝线，粒子沿连线流动
- 不引入 D3 等额外库，纯 Canvas 2D 手写力导向算法

### 节点设计

圆形发光球体，三层渲染：

```
外圈：光晕（CSS glow），半径随熟练度变化
主体：渐变球体
内心：高光白点

熟练度 → 视觉效果：
  未学 → 暗灰球体、无光晕、被"战争迷雾"薄雾笼罩
  不稳 → 暖黄色球体、微光晕、边缘微微闪动
  稳固 → 亮金色球体、明显光晕、有呼吸脉动动画
  卡住 → 暗红色球体、快速闪烁、有裂纹纹理
```

### 小人系统

```
小人状态机：
  默认：停在当前学习位置的节点上，微微晃动（待机动画）
  移动：点击节点 → 沿连线路径弹跳移动 → 到达目标
  到达：目标节点短暂放大 + 光粒子爆发 + 信息面板弹出
  
  环境反应：
    在稳固节点旁 → 小人坐下看书
    在卡住节点旁 → 小人挠头困惑
    在未学节点区域 → 站着眺望（迷雾中若隐若现）
    所有节点稳固 → 小人举手转圈庆祝
```

### 连线粒子流

```
依赖方向：粒子从依赖节点流向被依赖节点

粒子密度由两端熟练度决定：
  两端稳固 + 稳固 → 密集金色粒子流
  稳固 + 不稳 → 中等淡黄色粒子流
  包含未学 → 无粒子，虚线显示

高亮模式下：选中节点的上下游链全亮
  前置依赖链 → 蓝色粒子流
  后继依赖链 → 橙色粒子流
  无关节点 → 半透明淡化
```

### 战争迷雾

```
每个节点辐射照明范围：
  未学 → 0 照明（漆黑迷雾覆盖节点周围）
  不稳 → 微弱照明（迷雾半散，隐约可见连线）
  稳固 → 完全照明（周围区域清晰，迷雾退散）

整体效果：学得越多，地图越亮
```

### 趣味系统

| 元素 | 触发条件 | 效果 |
|------|---------|------|
| 宝箱 | 一个章节所有节点稳固 | 该章节旁出现小宝箱，可点击开箱 |
| 小动物伙伴 | 连续学习 7 天 | 小人旁边多一只跟着的小猫/小鸟 |
| 萤火虫粒子 | 晚上 18:00-06:00 | 画布上有萤火虫光点飘动 |
| 晨曦粒子 | 早上 06:00-10:00 | 温暖的金色光粒从左上角洒落 |
| 星光 | 深夜 22:00-06:00 | 深蓝暗色光点缓慢漂浮 |
| 足迹轨迹 | 最近 5 次点击的节点 | 节点间留下发光足迹，慢慢消失 |
| +XP 飘字 | 节点从不稳 → 稳固 | "+10 EXP" 小字从节点飘起消失 |
| 篝火 | 当前正在学习的节点 | 节点旁有小篝火动画，小人坐旁边 |
| 升级特效 | 所有节点稳固 | 全屏金色粒子雨 + 小人举杖庆祝 |

### 信息面板

点击节点弹出（替代当前的 `#km-detail`）：

```
┌──────────────────────┐
│  ⭐ 动作电位         │
│  第1章 · ● 稳固      │
│                      │
│  前置：静息电位       │
│  后继：突触传递       │
│        神经调节       │
│                      │
│  [开始复习] [看教案]  │
└──────────────────────┘
```

羊皮纸纹理边框 + 卷轴展开动画。

---

## 实施步骤

### 第 1 步：素材准备（你来）
- 生成小人图片（至少待机姿态）
- 生成羊皮纸纹理背景
- 放到 `scripts/templates/assets/`

### 第 2 步：布局重构（我来）
- 实现力导向布局算法（纯 JS）
- 替换当前的 `computeLayers` → `forceDirectedLayout`
- 节点改为圆形光晕球体渲染
- 连线改为粒子流动画

### 第 3 步：小人接入（我来）
- 加载小人 sprite
- 点击移动动画（沿连线路径弹跳）
- 不同节点状态下的姿态切换

### 第 4 步：趣味系统（我来）
- 战争迷雾着色器
- 时间/天气粒子
- 宝箱/成就系统
- 足迹轨迹
- 小动物伙伴

---

## 灵感来源

- [RoadHub](https://github.com/nicepkg/roadhub) — RPG 技能树 UI 交互
- [Azgaar's Fantasy Map Generator](https://github.com/Azgaar/Fantasy-Map-Generator) — 幻想地图生成
- Codex Cryptica — 羊皮纸视觉风格
- Hearthglen — RPG 暖色调 UI 色板

---

## 改动范围

仅 `scripts/templates/index.html`（CSS + Canvas JS），后端 `knowledge_panel.py` 不改。
