# Document Ingestion Spec

## Inputs

- multipart 文件：PDF、PPTX、UTF-8 Markdown。
- 单文件最大 20 MB。

## Pipeline

1. 校验扩展名、MIME、文件头、大小和原始文件名。
2. 以 SHA-256 检测课程内重复。
3. 使用 UUID 目录保存原文件。
4. 解析为带页码、幻灯片或章节元数据的文本。
5. 700 字目标分片，100 字重叠，1000 字硬上限。
6. 批量 Embedding，先删除旧索引再原子写入。
7. 状态从 `pending`、`processing` 更新为 `ready` 或 `failed`。

## Failures

- 不支持类型：415 `UNSUPPORTED_FILE`。
- 超大文件：413 `FILE_TOO_LARGE`。
- 无文本 PDF：状态 failed 并提示 OCR。
- Embedding 或向量写入失败：清理半成品并允许重试。
- 服务重启：将遗留 processing 文档标记为 failed。
