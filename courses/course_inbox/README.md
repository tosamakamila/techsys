# 课程教材投递箱

这里用于预存尚未归档到具体课程的原始教材。

你可以把准备学习的教材先放到这里。教材文件名应尽量对应课程名。

例如：

```text
courses/course_inbox/
  机器学习.pdf
  AI经济学.md
  计量经济学.docx
```

当你说：

> 上机器学习课

Claude Code 应检查 `courses/course_inbox/` 中是否有与”机器学习”匹配的教材。

如果找到教材，并且 `courses/` 下还没有对应课程文件夹，应自动：

1. 按 `courses/_template/` 创建新课程文件夹。
2. 把教材移动到新课程的 `materials/` 文件夹。
3. 从 `courses/course_inbox/` 移走原教材文件。
4. 更新新课程的 `course.md`、`progress.md`、`lesson_state.md`。
5. 再开始上课，或询问是否先改写教材。

投递箱只是临时入口。教材一旦归档到课程文件夹，就不应继续留在这里。

