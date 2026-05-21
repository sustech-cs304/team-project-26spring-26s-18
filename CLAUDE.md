# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered student productivity tool (学生效率助手) with schedule management, intelligent planning, and document Q&A. Vue 3 frontend + FastAPI backend.

## Commands

### Frontend (`vue/`)

```bash
npm install          # Install dependencies
npm run dev          # Dev server (proxies /api → localhost:5000)
npm run build        # Production build
npm run test:run     # Run tests once (Vitest)
npm test             # Run tests in watch mode
```

### Backend (`python_demo/`)

```bash
conda env create -f environment.yml   # Create Conda env (Python 3.11, ML stack)
conda activate fastApi_env
uvicorn main:app --reload             # Dev server on port 8000
python -m pytest tests/ -v --tb=short # Run all tests
python -m pytest tests/test_user.py::TestClassName::test_method -v  # Single test
```

API docs available at `http://localhost:8000/docs`.

### Required Environment Variables

```
DASHSCOPE_API_KEY       # Aliyun 百炼 LLM key
OSS_ACCESS_KEY_ID       # Aliyun OSS credentials
OSS_ACCESS_KEY_SECRET
BOCHA_API_KEY           # Optional: web search in recommend mode
```

## Architecture

```
Vue 3 SPA (port 5173 dev)
    └── fetch + JWT token header
FastAPI (uvicorn, port 8000)
    ├── /user     → routers/user.py     → crud/user.py     → models/user.py
    ├── /session  → routers/session.py  → crud/session.py  → models/session.py
    ├── /scheduler→ routers/scheduler.py→ crud/scheduler.py (largest file, 89KB)
    └── /rag      → routers/rag.py      → utils/rag_util.py
External services:
    ├── MySQL (Aliyun RDS, async via aiomysql + SQLAlchemy)
    ├── Redis (session caching, email verification codes)
    ├── Aliyun OSS (file/avatar storage)
    ├── Aliyun DashScope (LLM: chat, RAG, planning)
    └── ChromaDB (local vector store at python_demo/chroma_db/)
```

### Backend Conventions

- All API responses use a `Result` wrapper: `{"code": 200, "msg": "...", "data": ...}`
- DB access via async SQLAlchemy sessions; dependency injected as `get_db` from `config/db_config.py`
- Redis helpers: `set_key` / `get_key` in `config/redis.py`
- JWT auth middleware exists in `main.py` but is **currently commented out**

### Frontend Conventions

- API base URL configured in `vue/src/config/config.js` (defaults to `127.0.0.1:8000`)
- Central fetch wrapper at `vue/src/api/request.js` — handles token injection and Result unwrapping
- Pinia user store (`vue/src/stores/user.js`) persists: `id`, `token`, `userName`, `email`, `phone`, `avatarURL`
- Routes: `/login`, `/chat`, `/rag`, `/todo`, `/user`; default redirects to `/chat`

### Key Utility Files

| File | Purpose |
|------|---------|
| `python_demo/utils/ai_util.py` | Core LLM integration (35KB) |
| `python_demo/utils/rag_util.py` | RAG pipeline |
| `python_demo/utils/recommend_resources_util.py` | Resource recommendation (29KB) |
| `vue/src/views/Todo.vue` | Most complex frontend component (79KB) |
| `vue/src/views/Chat.vue` | AI chat interface (56KB) |

### file_helper Package

Standalone natural-language file management utility (`file_helper/`). Entry point: `file_helper.py`. Parses user intent in Chinese/English → file system operations via `intent_parser.py`.

### CI/CD

`.github/workflows/ci-cd.yml` runs on push/PR to `main`:
- Frontend: `npm run build`
- Backend: `pytest` with live MySQL 8.0 + Redis services
