# StudyMate

StudyMate 是面向 5–10 人小范围课程试点的资料 AI 问答与错题复习助手。系统把课程资料解析、证据检索、带引用回答、练习生成、自动批改、错题沉淀和每周复习串成一个闭环。

## 核心能力

- 邮箱注册、登录、JWT 鉴权；课程创建、6 位邀请码加入和成员权限。
- PDF、PPTX、Markdown 上传，SHA-256 去重、UUID 存储、后台解析和索引状态跟踪。
- 中文分片、Embedding、ChromaDB 检索、关键词重排和证据阈值拒答。
- SSE 流式回答；每条有效回答强制保存真实资料引用。
- 5/10 道单选与简答题生成，结构化校验、自动批改、答案解析。
- 错题按知识点聚合；重练、连续两次答对掌握、每周规则复习清单。
- SQLite WAL、Alembic、结构化日志、请求 ID、Docker Compose 和自动化测试。
- 未配置模型密钥时自动使用本地哈希 Embedding 和抽取式回答，便于先运行产品闭环。

## 目录

```text
studymate/
├── backend/             FastAPI、SQLAlchemy、Alembic 和 pytest
├── frontend/            Vue 3、TypeScript、Pinia、Vitest 和 Playwright
├── nginx/               生产反向代理说明（实际配置位于 frontend/nginx.conf）
├── specs/               各模块输入、输出、边界和失败场景
├── prompts/             版本化 Chat / Quiz Prompt
├── evals/               30 条 RAG 回归数据与数据集校验脚本
├── docs/                架构、部署、评估和试点模板
├── docker-compose.yml
└── .env.example
```

## 本地开发

### 1. 后端

要求 Python 3.10+（生产镜像使用 Python 3.12）。

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[test]"
mkdir -p data
alembic upgrade head
uvicorn app.main:app --reload
```

接口文档：`http://localhost:8000/docs`，健康检查：`http://localhost:8000/api/health`。

默认不配置 `LLM_API_KEY`，可直接体验本地降级检索与回答。要启用真实模型：

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-key
CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
ENABLE_CHROMA=true
CHROMA_URL=http://localhost:8000
```

### 2. 前端

要求 Node.js 22+。

```bash
cd frontend
npm install
npm run dev
```

开发地址：`http://localhost:5173`。Vite 会把 `/api` 代理到 `http://localhost:8000`。

## Docker Compose 启动

```bash
cp .env.example .env
# 编辑 .env；至少修改 APP_SECRET_KEY。模型密钥可以留空。
docker compose up -d --build
```

访问 `http://localhost:8080`。首次启动时 `api` 容器会自动执行 `alembic upgrade head`。

服务组成：

- `nginx`：托管 Vue 生产构建并代理 `/api`，SSE 缓冲已关闭。
- `api`：FastAPI、文档解析、RAG、练习与复习业务。
- `chroma`：0.5.23 持久化向量库。

## 质量检查

后端：

```bash
cd backend
ruff check .
mypy app
pytest --cov=app --cov-report=term-missing
alembic upgrade head
```

前端：

```bash
cd frontend
npm run lint
npm run type-check
npm run test
npm run build
```

端到端：

```bash
docker compose up -d --build
cd frontend
npx playwright install chromium
npm run test:e2e
```

## 数据和安全边界

- SQLite 是用户、权限、文档状态、会话、练习和错题的事实来源。
- 原始文件保存在私有卷，不以静态文件暴露。
- ChromaDB 只保存可重建索引；失败重试会先清理旧分片。
- 上传校验扩展名、MIME、文件头和大小；Markdown 仅接受 UTF-8。
- 只向模型发送 Top-K 片段，不发送完整课程文件。
- Prompt 明确把资料视为不可信数据，资料中的指令不能覆盖系统规则。
- API Key、密码、JWT 和完整原文不得写入日志。

## RAG 行为

1. 问题生成 Query Embedding。
2. 按 `course_id` 检索 12 个候选。
3. 向量分数与中文词项分数按 0.75 / 0.25 融合。
4. 选取最多 4 条；Chroma 路径低于 0.35、本地关键词降级低于 0.25 时直接拒答，不调用生成模型。
5. 回答只保存本次检索得到的引用，模型生成的任意引用 ID 不会直接信任。

## 已知边界

- 扫描版 PDF 不做 OCR，会标记为失败并提示。
- 首版未实现刷新令牌、找回密码、成员移除、课程转让和在线协同编辑。
- 真实用户试点、性能报告和演示视频必须由实际运行记录产生，仓库不会伪造。
- 未配置 `ENABLE_CHROMA` 时使用 SQLite 本地索引，用于开发和测试；生产 Compose 默认启用 ChromaDB。
