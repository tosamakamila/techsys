# 课程文件夹

这里用于放置不同课程的独立材料。每门课一个子文件夹，避免教材、进度和课堂状态混在一起。

## 使用方式

如果你想上一门课，可以说：

> 上「课程名」课

例如：

> 上机器学习课

Claude Code 应在 `courses/` 下寻找对应课程文件夹，读取该课程的教材、进度和课堂状态，再由澪开始上课。

## 推荐课程结构

每门课建议使用以下结构：

```text
courses/
  course_slug/
    course.md
    progress.md
    lesson_state.md
    materials/
    transformed/
    notes/
    book_revision_notes.md
    reading_plan.md
```

## 命名建议

课程文件夹建议使用英文或拼音短名，例如：

- `machine_learning`
- `ai_science`
- `econometrics`
- `philosophy`

课程的中文名称写在该课程文件夹的 `course.md` 中。

