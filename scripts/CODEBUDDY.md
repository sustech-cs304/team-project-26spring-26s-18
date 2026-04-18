# CODEBUDDY.md This file provides guidance to WorkBuddy when working with code in this repository.

## Project Overview

**Student Productivity Agent** — 面向南科大学生的 AI 智能助理平台（软件工程 2026 春季第 18 组课程项目）。

核心功能：AI 对话（含 RAG 知识检索）、多源日程管理（个人待办 / 官方校历 / Blackboard / 课程表）、知识库文件上传、本地自动化脚本（作业处理 + TIS 系统）。

**后端已从 Java SpringBoot 切换为 Python FastAPI**（`java_demo已弃用/` 目录可忽略）。

---

## Commands

### Backend (`python_demo/`)

```bash
# 首次：使用 Conda 创建环境
conda env create -f python_demo/environment.yml

# 激活环境（每次启动前）
conda activate fastApi_env

# 启动开发服务器（热重载，默认 http://127.0.0.1:8000）
cd python_demo
uvicorn main:app --reload

# 查看交互式 API 文档
# 浏览器访问 http://127.0.0.1:8000/docs

# 首次或新增 scheduler 模型后初始化数据库表
cd python_demo
python init_scheduler_tables.py

# 添加新依赖后更新 environment.yml
conda env export > python_demo/environment.yml
```

**必须设置的环境变量：**
```
DASHSCOPE_API_KEY   # 阿里云百炼 AI API Key（对话、Embedding）
OSS_ACCESS_KEY_ID   # 阿里云 OSS 访问密钥 ID
OSS_ACCESS_KEY_SECRET  # 阿里云 OSS 访问密钥 Secret
```

### Frontend (`vue/`)

```bash
# 安装依赖（需 Node.js >=20.19 或 >=22.12）
cd vue && npm install

# 开发模式（热重载，默认 http://localhost:5173）
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

修改后端地址：`vue/src/config/config.js` 中 `export const ip = "127.0.0.1:8000"`。

### Scripts (`scripts/`)

```bash
cd scripts

# 测试 User Story 1：自动重命名单个作业并转 PDF
# （需先在 scripts/test_workspace/111.docx 放入测试文档）
python test1.py

# 测试 User Story 2：扫描并按课程分类下载文件夹
# （需在 scripts/test_workspace/downloads/ 放入 .docx/.pdf 文件）
python test2.py

# 测试 TIS 成绩获取（需替换 test3.py 中的学号/密码）
python test3.py

# 直接运行 TIS 喵课助手
python tis.py
```

Scripts 依赖与后端不同，需单独安装：`pip install dashscope python-docx PyMuPDF docx2pdf colorama`。  
`file_converter.py` 依赖本机安装的 Microsoft Word（Windows/macOS）。

---

## Architecture

### 整体架构

本项目采用**前后端分离 + 后端分层架构**，三个独立子系统：

```
vue/         ← 前端 SPA（Vue 3 + Vite）
                  ↕ REST API over HTTP
python_demo/ ← 后端 API 服务（FastAPI）
                  ↕ 独立脚本，不经过 API
scripts/     ← 本地自动化脚本（独立 Python 工具）
```

### 后端分层（`python_demo/`）

后端严格遵循 **Router → CRUD → Model** 三层分离：

```
HTTP Request
    ↓
routers/        ← 路由层：定义 API 端点，输入验证，调用 crud
    ↓
crud/           ← 数据访问层：封装 SQLAlchemy 异步查询（CRUD 操作）
    ↓
models/         ← ORM 模型层：SQLAlchemy Table 定义
    ↓
MySQL (阿里云 RDS)
```

**横切关注点（utils/ 和 config/）：**
- `utils/Result.py`：统一 API 响应格式 `{code: 0|1, message: str, data: Any}`
- `utils/jwt_util.py`：JWT 生成/解析（HS256，24 小时有效）
- `utils/ai_util.py`：AI 对话核心（见下方 AI 流程）
- `utils/rag_util.py`：RAG 三件套（EmbeddingService / VectorStore / Reranker）
- `utils/oss_util.py`：阿里云 OSS 上传/下载（图片存储）
- `config/db_config.py`：MySQL 异步连接池（SQLAlchemy async，连接池 size=10/overflow=20）
- `config/redis.py`：Redis 连接（用于验证码缓存，5 分钟 TTL）
- `schemas/`：Pydantic v2 请求/响应模型

**`main.py` 的职责：**
1. 创建 FastAPI 实例，挂载所有 router
2. 配置 CORS 中间件（开发环境允许所有源）
3. 全局 JWT 鉴权中间件（目前已注释，开发调试状态）

### API 路由结构

| 前缀 | 模块 | 核心端点 |
|------|------|---------|
| `/user` | `routers/user.py` | POST `/sendCode` `/register` `/login` `/updateInfo` `/updateAvatar` |
| `/session` | `routers/session.py` | GET/POST/DELETE 会话管理；POST `/aicontent` 触发 AI 对话 |
| `/rag` | `routers/rag.py` | POST `/upload` 批量上传文件至向量库 |
| `/scheduler` | `routers/scheduler.py` | 待办 CRUD；官方校历 / 课程表 / Blackboard 导入；聚合分析 |
| `/test` | `routers/test.py` | 内部测试接口 |

### AI 对话流程（`utils/ai_util.py`）

每次调用 `/session/aicontent` 时：

1. **历史上下文**：从 MySQL 加载最近 5 条对话消息
2. **多模态处理**：
   - 图片 → Base64 解码 → 上传至阿里云 OSS → 获取 URL
   - PDF → `pdfplumber` 提取文本（最多 5000 字符）
   - Markdown → Base64 解码为纯文本
3. **RAG 检索**：用当前问题调用 `text-embedding-v1` 生成向量，在 ChromaDB 中余弦相似度搜索最相关 3 条知识块，注入为 `system` 消息
4. **拼装 messages**：历史消息 → RAG 上下文 → 当前用户输入
5. **调用大模型**：`qwen3.5-plus`（通过 OpenAI 兼容 SDK，`run_in_executor` 避免阻塞事件循环）
6. **持久化**：用户消息和 AI 回复写入 MySQL `session_content` 表

### RAG 知识库（`utils/rag_util.py`）

- **入库**：`/rag/upload` → `store_document()` → 文本提取（支持 txt/md/pdf/docx/pptx）→ 按 500 字符分块 → `text-embedding-v1` 向量化 → 存入 ChromaDB（`campus_handbook` collection）
- **检索**：每次 AI 对话时自动触发，`top_k=3`，余弦相似度
- ChromaDB 数据本地持久化在 `python_demo/chroma_db/` 目录

### 日程模块（最复杂，`routers/scheduler.py` + `crud/scheduler.py`）

数据库有三张独立表（对应 `models/scheduler.py`）：
- `PersonalTodo`：用户手动创建的待办（deadline 或 start_time+end_time，状态 pending/done/cancelled，优先级 1-3）
- `OfficialCalendarEvent`：全局官方校历（管理员或用户导入，display_mode: background/event）
- `CourseScheduleEvent`：用户个人课程表（支持从 .xlsx 批量导入，按学期标签管理）

`crud/scheduler.py`（87KB，最大文件）包含：
- 数据导入解析：`parse_import_rows()`（JSON/CSV/ICS 通用解析）、`parse_course_schedule_xlsx()`
- 冲突检测：创建/修改待办时自动检测时间块重叠（`find_conflicting_range_todo`）
- 聚合分析：`build_schedule_aggregate_data()` 整合三类数据，输出时间线、冲突、堆叠、AI 建议

### 前端架构（`vue/`）

Vue 3 Composition API，单页应用，Hash 路由模式：

```
src/
├── main.js          ← 入口：注册 Pinia（含持久化）/ Router / ElementPlus
├── App.vue          ← 根组件：Navbar + RouterView
├── config/config.js ← 后端地址（修改此处切换环境）
├── api/
│   ├── request.js   ← fetch 封装：自动注入 token，统一错误处理（code≠1 抛异常）
│   └── todo.js      ← 日程相关 API 函数
├── stores/user.js   ← Pinia：用户信息 + token，localStorage 持久化
├── router/index.js  ← Hash 路由
├── views/           ← 页面组件（Login/Chat/Rag/Todo/User/Navbar）
├── components/todo/ ← Todo 页面拆分的子组件（Calendar/Timetable/AiPanel 等）
└── utils/
    ├── todoTime.js       ← 复杂时间计算工具（19KB）
    └── todoActionMatcher.js ← 解析 AI 回复中的操作指令（实现 AI → 前端动作）
```

**Token 传递方式**：前端在请求头中附加 `token: <jwt_value>`（非标准 Bearer 格式），后端 `scheduler` 路由同时支持 `token` 头和 `Authorization: Bearer` 头。

**Todo 页面的 AI 联动**：`TodoAiPanel.vue` 展示 AI 对话，`todoActionMatcher.js` 解析 AI 回复中的结构化操作（如创建/更新待办），并触发 `Todo.vue` 中对应的数据操作，实现"AI 代理操作日程"。

### 本地脚本架构（`scripts/`）

完全独立于 Web 服务，直接在本地运行，实现两条 AI Agent 流水线：

**流水线 1（作业处理）**：
```
test1.py → workflows.process_single_homework()
    → document_parser（提取文本）
    → agent_analyzer（qwen-turbo 识别课程+作业类型）
    → file_manager（重命名）
    → file_converter（docx → PDF，依赖 Word）
```

**流水线 2（文件归档）**：
```
test2.py → workflows.organize_downloads_folder()
    → 遍历 downloads/ 中的 docx/pdf 文件
    → document_parser + agent_analyzer（识别所属课程）
    → file_manager（移动到对应课程文件夹）
    → 自动学习新课程写回 config.json（自我进化机制）
```

**TIS 工具**：`tis_agent.py`（成绩查询）和 `tis.py`（喵课助手）均通过模拟浏览器 CAS 登录南科大 TIS 系统，`requests.Session` 维持会话，多线程抢课。

### 外部服务依赖

| 服务 | 用途 | 配置位置 |
|------|------|---------|
| 阿里云百炼 DashScope | AI 对话（qwen3.5-plus）、Embedding（text-embedding-v1）、Rerank | `DASHSCOPE_API_KEY` 环境变量 |
| 阿里云 MySQL RDS | 主数据库 | `python_demo/config/db_config.py`（硬编码连接串） |
| 阿里云 OSS | 图片/文件存储（bucket: experience-tree） | `OSS_ACCESS_KEY_ID/SECRET` 环境变量 |
| Redis（39.107.193.66） | 验证码缓存 | `python_demo/config/redis.py`（硬编码） |
| ChromaDB（本地） | 向量知识库 | `python_demo/chroma_db/`（本地持久化） |
| 南科大 CAS / TIS | 成绩查询、选课 | `scripts/tis.py` `scripts/tis_agent.py` |

### 数据模型关系

```
User (id, email, password, userName, phone, avatarURL)
  ↓ 1:N
Session (id, user_id, title)
  ↓ 1:N
SessionContent (id, session_id, role[user/assistant], content, content_type[text/image/pdf/markdown], name)

PersonalTodo (id, user_id, title, content, deadline, start_time, end_time, status, priority, import_source, import_uid)
OfficialCalendarEvent (id, source_year, title, start_time, end_time, display_mode)
CourseScheduleEvent (id, user_id, course_name, section_text, start_time, end_time, weekday, week_start, week_end, term_label, import_source, import_uid)
```
