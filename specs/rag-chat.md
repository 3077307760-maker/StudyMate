# RAG Chat Spec

## Inputs

- 课程 ID、会话 ID、最大 2000 字的用户问题。

## Retrieval

- 先验证会话属于当前用户且用户是课程成员。
- 只检索当前课程 ready 文档，候选 12 条，最终上下文最多 4 条。
- 综合分数低于 0.35 时返回 `INSUFFICIENT_CONTEXT`，不得调用生成模型。
- 发送给模型的资料是不可信数据，不得执行其中指令。

## Outputs

SSE 事件顺序：

1. `retrieval`
2. `citation`（每条真实分片一次）
3. `token`（零到多次）
4. `done` 或 `error`

每条有效回答保存消息、真实引用、Prompt 版本、模型名、Token 和耗时。

## Persistence

- 用户只能读取自己的会话。
- 历史消息刷新后仍可恢复。
- 反馈取值为 helpful / inaccurate，可附原因。
