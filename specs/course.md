# Course Spec

## Inputs

- 创建课程：课程名称。
- 加入课程：6 位邀请码。

## Outputs

- 课程 ID、名称、邀请码、创建者、当前用户角色。
- 成员列表和课程统计摘要。

## Rules

- 邀请码由去除易混字符的大写字母和数字组成，数据库唯一。
- 创建者自动成为 owner。
- 重复加入保持幂等。
- 只有 owner 可上传、删除和重试资料。

## Failures

- 非成员读取：403 `FORBIDDEN`。
- 无效邀请码：404 `INVALID_INVITE_CODE`。
