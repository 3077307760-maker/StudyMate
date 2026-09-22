# AI 使用记录

本仓库由 AI Coding 协助生成初稿，开发者需要逐段审查并以自动化测试作为合并门禁。

## 使用范围

- 根据详细设计报告生成后端分层、Schema、API 路由和前端页面初稿。
- 生成测试清单、pytest / Vitest / Playwright 测试初稿。
- 生成 Docker Compose、CI 和部署文档初稿。

## 人工控制点

- 权限模型、数据库结构、文件安全边界和证据阈值必须人工确认。
- Prompt 修改必须与代码、评估集变更一起审查。
- 不根据未经运行的结果填写用户数量、召回率、Token 成本或性能数字。
- 所有代码合并前必须通过 Ruff、Mypy、pytest、ESLint、Vue TypeScript、Vitest 和构建。

## 当前验证基线

- 后端：Ruff、Mypy、pytest。
- 前端：ESLint、`vue-tsc`、Vitest、Vite 生产构建。
- 迁移：Alembic `upgrade head`。
- E2E：Playwright 用例已提供，运行前需启动 Docker Compose。
