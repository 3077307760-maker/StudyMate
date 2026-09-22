# Review Spec

## Wrong Item Rules

- 首次答错创建错题，错误次数为 1。
- 再次答错递增错误次数并清零连续答对次数。
- 连续答对两次标记为 mastered。
- 掌握后再次答错，重置为未掌握。

## Practice

- 错题只能由所有者重练。
- 单题提交仍创建 attempt 和 attempt_answer，并复用统一评分规则。

## Weekly Plan

- 自然周从周一开始。
- 只包含未掌握错题。
- 按错误次数和最近错误时间排序，优先级 1–3。
- 完成状态独立记录在 `review_completions`。
