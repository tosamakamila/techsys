# 课程进度

## 当前状态

- L001 已完成，正在推进到 L002。

## 最近一课

- 日期：2026-05-19
- 主题：uv 是什么 + pip 替代 / 虚拟环境入门
- 教材/材料：materials/uv教材.md (L001)
- 教材片段：L001
- 完成情况：发现学生对虚拟环境概念基础薄弱，即时调整为动手实操课。学生成功完成 `uv venv` 和 `uv pip install rich`。
- 本课标签：虚拟环境, conda vs uv, uv pip install
- 本课摘要：学生从 conda 痛点出发，引出虚拟环境概念。对比 conda base 和 uv 的 .venv 机制后，学生亲手创建 uv-test 项目并装包，对安装速度感到惊讶。虚拟环境概念仍需多用几次来内化。
- 学生亲自推出来的结论：
  - conda 的 base 是个默认大池子，不切环境容易弄混
  - uv 不给默认环境，需要 `.venv` 文件夹
  - `uv pip install` 比 conda 安装快很多
- 待复习：
  - 虚拟环境概念（需要多用几次来内化）

## 历史归档

- 2026-05-19 L001：虚拟环境入门——conda base vs uv .venv → 亲手建 uv-test 项目装包。下节 L002 项目初始化。

## 下一步

下一课推进到 L002（uv 项目管理：uv init、uv add、uv run）。开课时先确认学生对 .venv 的理解是否更稳了。
