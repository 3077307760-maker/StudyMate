# Auth Spec

## Inputs

- `POST /api/auth/register`: email、password（至少 8 位）、display_name。
- `POST /api/auth/login`: email、password。
- `Authorization: Bearer <JWT>`。

## Outputs

- 注册：201、JWT、用户信息。
- 登录：200、JWT、用户信息。
- 当前用户：用户 ID、邮箱、昵称和创建时间。

## Boundaries

- JWT 默认有效期 7 天。
- 密码只保存 bcrypt 哈希。
- 首版不提供邮箱验证、找回密码和第三方登录。

## Failures

- 重复邮箱：409 `EMAIL_EXISTS`。
- 错误凭据：401 `INVALID_CREDENTIALS`。
- 缺失或过期令牌：401 `AUTH_REQUIRED`。
