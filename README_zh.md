# 智能简历与求职信生成器

[English](README.md)

基于 AI 的系统，使用**多智能体 LangGraph 流水线**自动生成针对职位定制的简历、求职信和申请问题回答，支持自动评估、公司调研（RAG）和多种 LLM 供应商。技术栈：FastAPI + React + TypeScript。

## v3.3 新功能

- **提示词变体系统** — 为虚构开启/关闭模式使用独立的提示词文件，消除禁用 AI 虚构时的矛盾指令
  - 8 个新的禁止虚构提示词变体（简历、求职信、问答——中英文各一套）
  - 一页模式专用 LaTeX 模板（省略个人总结板块以节省空间）
  - 设置开关（`allow_ai_fabrication`）在生成时自动选择正确的提示词文件
- **设置保存修复** — 修复 `AppSettingsUpdate` 模型缺少 17+ 字段的问题（DeepSeek、Qwen、虚构、验证、个人链接、代理提供商），导致设置保存时被静默丢弃
- **DeepSeek 与 Qwen 设置** — 设置模型中新增 `deepseek_api_key/model/temperature/max_output_tokens` 和 `qwen_api_key/model/temperature/max_output_tokens`，并支持 API 密钥脱敏
- **完整提示词编辑器** — 提示词面板现显示全部 18 种提示词类型（9 英文 + 9 中文），包括禁止虚构变体和无总结格式模板
- **全面测试套件** — 560+ 后端测试和 200+ 前端测试，覆盖提示词变体选择、设置持久化、API 路由和 UI 组件

### v3.2

- **ATS 优化简历格式** — 基于 30+ 来源（FAANG 招聘官指南、ATS 系统文档、Google/Harvard/Stanford 职业服务）重新设计 LaTeX 模板：
  - **条件排版** — 有经验（2年+）：个人总结 → 工作经验 → 项目经历 → 技能 → 教育。应届生：教育 → 技能 → 项目 → 经验
  - **个人总结** — 针对 JD 的 1-2 句总结，含工作年限、核心领域、关键技术和量化亮点
  - **结构化技术技能** — 5 个类别（编程语言、框架、云计算与运维、数据库、工具），含双形式关键词
  - **X-Y-Z 要点公式** — "通过[Z方法]实现了[X成果]，达到了[Y指标]"，每个职位 3-5 个要点
  - **标准板块名称** — `技术技能`（替换 `编程技能`），所有板块使用 ATS 可识别的标准名称
- **增强质量检查清单** — 中英文提示词均强制检查个人总结、分类技能、8+ 不同动词、5+ 量化成就
- **示例简历 PDF** — `backend/output/examples/` 中包含 3 份参考 PDF（应届生、有经验工程师、高级 AI/ML 工程师）

### v3.1

- **混合多方法 ATS 评分器** — 6 种互补评分方法（BM25、语义嵌入、技能覆盖、模糊匹配、质量启发、板块感知加分），含 sigmoid 校准和同义词归一化
- **ATS 优化提示词** — 简历生成提示词现指导 AI 使用双形式关键词（如"Machine Learning (ML)"）、跨板块分布关键词、使用标准 ATS 可识别的板块标题
- **求职信文本预览** — 可复制粘贴的纯文本求职信视图
- **任务取消** — 支持在流水线执行中取消任务并保留部分结果
- **AI 专家评审修复** — LLM 评审结果现已正确缓存和显示

### v3.0

- **多智能体流水线** — LangGraph StateGraph，含 JD 分析、相关性匹配、质量门控重试、结构化输出
- **自动评估** — 确定性 ATS 评分（关键词匹配、动作动词、章节完整度）+ LLM 评审与自我批判反馈循环
- **公司调研（RAG）** — 爬取公司网站，索引至 ChromaDB，将相关上下文注入简历和求职信生成
- **现代前端** — shadcn/ui 组件、TanStack Query v5 服务端状态管理、Zod 表单验证、ATS 评分可视化、智能体流水线进度 UI
- **生产就绪** — Docker 多阶段构建、PostgreSQL 支持、GitHub Actions CI/CD、速率限制、安全扫描

## 功能

### 多智能体流水线（v3）

v3 流水线通过一系列专业智能体处理每份简历：

```
JD 分析器 → 相关性匹配器 → [公司调研] → 简历撰写器 → 质量门控
    ↻ 评分 < 0.7 时重试（最多 2 次）
    → LaTeX 编译 → [求职信 → 求职信 PDF] → 最终处理
```

- **JD 分析器** — 提取职位名称、技能要求、经验级别、职责和行业
- **相关性匹配器** — 将个人资料与 JD 要求匹配，识别重点
- **公司调研**（可选）— 从 RAG 向量数据库检索已索引的公司上下文
- **简历撰写器** — 生成带有职位优化指令的 LaTeX 简历
- **质量门控** — ATS 评分并条件路由（评分 < 0.7 触发带反馈的修订）
- **求职信撰写器** — 基于简历内容、JD 分析和公司上下文生成求职信
- 经典 v2 流水线（单次 AI 调用）仍可作为备选方案

### 自动评估

- **ATS 评分细分** — 6 项子分数：关键词匹配（40%）、经验匹配（20%）、格式质量（10%）、动作动词（10%）、量化成果（10%）、章节完整度（10%）
- **LLM 评审** — 5 项评分维度：关键词匹配、专业语气、量化成果、相关性、ATS 合规性 + 推理分析和改进建议
- **自我批判循环** — 低分触发可执行反馈，附加到重试提示中
- **可视化面板** — 分数条、匹配/缺失关键词徽章、专家评审展示

### 公司调研（RAG）

- 爬取公司网站，遵循速率限制和 robots.txt
- 使用 sentence-transformers（或备选嵌入模型）进行内容分块和嵌入
- 在 ChromaDB 中建立索引，附带元数据（来源类型、公司名称、内容类型）
- **纠正式 RAG** — 检索 → 评估相关性 → 查询质量差时重写 → 再次检索
- 公司上下文自动注入简历和求职信提示词
- 30 天缓存，支持手动刷新

### 多供应商 AI 支持

- **Google Gemini** — Gemini 2.0 Flash、Gemini 3 Pro、Gemini 3.1 Pro，支持可配置思考级别
- **Anthropic Claude** — Claude Sonnet 4.5、Claude Opus 4.6，直连 API
- **Claude Code 代理** — 通过本地代理使用 Claude 模型，SSE 流式传输
- **OpenAI 兼容** — 任何 OpenAI 兼容 API（Ollama、LM Studio、vLLM 等）
- **DeepSeek** — DeepSeek Chat/Reasoner，通过 DeepSeek API
- **Qwen** — Qwen Plus/Max/Turbo，通过阿里巴巴 DashScope API
- 支持按任务指定供应商或设置全局默认值

### 简历与求职信生成

- AI 生成针对每个职位描述定制的 LaTeX 简历
- 具有简历上下文感知的专业求职信
- 页面长度验证（超过 1 页自动重新生成）
- 智能 LaTeX 编译，含错误反馈和自动重试
- 多种简历模板（经典、现代、极简）
- 双语支持（英文 / 中文）

### 申请问题回答

- 为每个任务添加自定义申请问题，可配置字数限制
- AI 基于简历和职位描述生成回答
- 支持单独生成或批量生成
- 独立的**生成答案**面板，支持逐条复制和批量复制

### 任务管理

- 多任务支持，并发生成（信号量限制）
- 任务跨服务器重启持久化（JSON 存储 + 可选 PostgreSQL）
- 实时 WebSocket 逐步进度更新
- 任务重试、取消和删除
- 职位描述历史记录，便于快速复用

### 前端

- 深色模式，localStorage 持久化
- **shadcn/ui** 组件库（Button、Card、Badge、Progress）
- **TanStack Query v5** 服务端状态管理，自动缓存和重新获取
- **Zod** 表单验证
- 智能体流水线进度可视化（v3）
- ATS 评分细分图表，含匹配/缺失技能徽章
- PDF 预览、LaTeX 源码下载
- 键盘快捷键：`Ctrl+N`（新建任务）、`Ctrl+Enter`（开始）、`Ctrl+S`（保存设置）、`Escape`（关闭弹窗）
- 所有操作的 Toast 通知

## 系统架构

```
┌─────────────────────────┐    WebSocket     ┌──────────────────────────────┐
│     React 前端            │◄───────────────►│       FastAPI 后端             │
│  TanStack Query + Zustand│    REST API      │     LangGraph 流水线          │
│  shadcn/ui + Tailwind    │                  │                              │
└─────────────────────────┘                  └──────────┬───────────────────┘
                                                        │
                    ┌───────────────────────────────────┼──────────────┐
                    │                                   │              │
           ┌────────▼────────┐                ┌────────▼────────┐     │
           │  LangGraph v3   │                │     评估系统      │     │
           │  智能体流水线     │                │  ATS + LLM 评审  │     │
           │                 │                └─────────────────┘     │
           │  JD 分析器       │                                        │
           │  相关性匹配      │                ┌───────────────────┐   │
           │  简历撰写器      │                │   RAG 流水线       │   │
           │  质量门控        │◄──────────────►│  ChromaDB + httpx │   │
           │  求职信撰写器    │                │  公司调研          │   │
           └────────┬────────┘                └───────────────────┘   │
                    │                                                  │
       ┌────────────┼────────────┐                                    │
       │            │            │                                    │
  ┌────▼────┐ ┌────▼────┐ ┌────▼────┐                      ┌────────▼────────┐
  │ Gemini  │ │ Claude  │ │ OpenAI  │                      │ LaTeX 编译器     │
  │   API   │ │   API   │ │  兼容    │                      │ PDF 生成         │
  └─────────┘ └─────────┘ └─────────┘                      └─────────────────┘
                                                                     │
                                                            ┌────────▼────────┐
                                                            │   PostgreSQL    │
                                                            │   （可选）       │
                                                            └─────────────────┘
```

## 前置要求

- **Python 3.11+**
- **Node.js 18+**
- **LaTeX**（Windows 用 MiKTeX，Linux/Mac 用 TeX Live）
- 至少一个 API 密钥：[Google AI Studio](https://aistudio.google.com/)、[Anthropic](https://console.anthropic.com/) 或本地代理

## 快速开始

### 方式一：Docker（推荐）

```bash
# 克隆并配置
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 API 密钥

# 启动所有服务
docker-compose up --build
```

应用地址：**http://localhost:3000**（前端），API 地址：**http://localhost:48765**。

### 方式二：Windows 安装器

1. 运行 `install.bat`
2. 编辑 `backend/.env`，填入 API 密钥
3. 运行 `start.bat`

应用地址：**http://localhost:45173**。

### 方式三：手动安装

#### 系统依赖

**Windows：** 安装 [MiKTeX](https://miktex.org/) — 将"按需安装缺失包"设置为**始终**。

**Ubuntu/Debian：**
```bash
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**macOS：**
```bash
brew install --cask mactex
```

#### 后端

```bash
cd backend

# 方式 A：uv（推荐）
pip install uv
uv sync

# 方式 B：pip
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入 API 密钥
```

#### 前端

```bash
cd frontend
npm install
```

#### 启动

**后端**（终端 1）：
```bash
cd backend && python main.py
```

**前端**（终端 2）：
```bash
cd frontend && npm run dev
```

打开 **http://localhost:45173**。

## 使用方法

1. **创建任务** — 点击侧边栏的"新建任务"（`Ctrl+N`）
2. **粘贴职位描述** — 将完整 JD 粘贴到文本区域
3. **选择选项** — 选择模板、语言、供应商、流水线版本（v3/v2），以及是否生成求职信
4. **公司调研**（可选）— 输入公司 URL 并点击"调研"，索引公司信息用于 RAG
5. **添加申请问题**（可选）— 输入问题并设置字数限制
6. **开始** — 点击"开始任务"（`Ctrl+Enter`）
7. **监控** — 实时查看多智能体流水线进度
8. **评估** — 查看 ATS 评分细分、匹配/缺失关键词和专家评审
9. **下载** — 获取 PDF、在线预览或下载 LaTeX 源码
10. **复制答案** — 使用"生成答案"面板逐条复制或批量复制

## 配置

所有设置均可通过 UI 的**设置**面板配置，并持久化到 `backend/settings.json`。

### AI 供应商

| 供应商 | 配置项 | 说明 |
|--------|--------|------|
| Google Gemini | `gemini_api_key`、`gemini_model` | 支持思考级别、Google 搜索增强 |
| Anthropic Claude | `claude_api_key`、`claude_model` | 直连 Anthropic API |
| Claude Code 代理 | `claude_proxy_base_url`、`claude_proxy_model` | 使用 SSE 流式传输避免响应截断 |
| OpenAI 兼容 | `openai_compat_api_key`、`openai_compat_base_url`、`openai_compat_model` | 兼容任何 OpenAI 兼容端点 |

### 生成参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Temperature | `1.0` | 创造性（0.0–2.0） |
| 最大输出 Token | 模型默认 | 最大响应长度 |
| 思考级别 | `high` | Gemini 3+ 推理深度：`low`、`high` |
| Google 搜索 | `false` | 公司调研的网页搜索增强 |
| LaTeX 最大重试次数 | `3` | LaTeX 编译出错时自动重试 |

### 服务端口

默认端口选择避免常见冲突（`8000`、`5173`）：

| 设置 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `48765` | 后端 API 服务端口 |
| `FRONTEND_PORT` | `45173` | 前端开发服务端口（同时用于 CORS） |

在 `backend/.env` 中覆盖：
```env
PORT=9999
FRONTEND_PORT=9998
```

若后端使用自定义端口，前端 Vite 代理需设置 `VITE_BACKEND_PORT`：
```bash
VITE_BACKEND_PORT=9999 npm run dev
```

### 提示词模板

通过 UI 的**提示词**面板编辑，或直接编辑 `backend/prompts/`：

| 文件 | 说明 |
|------|------|
| `User_information_prompts.txt` | 个人信息（教育、经验、技能） |
| `Resume_format_prompts.txt` | LaTeX 模板结构 |
| `Resume_prompts.txt` | 主简历生成提示词 |
| `Cover_letter_prompt.txt` | 求职信生成提示词 |
| `Application_question_prompt.txt` | 申请问题回答提示词 |
| `User_information_prompts_zh.txt` | 个人信息（中文版） |
| `Resume_format_prompts_zh.txt` | LaTeX 模板结构（中文版） |
| `Resume_prompts_zh.txt` | 简历生成提示词（中文版） |
| `Cover_letter_prompt_zh.txt` | 求职信生成提示词（中文版） |
| `Application_question_prompt_zh.txt` | 申请问题回答提示词（中文版） |

**占位符**（自动替换）：
- `{{user_information}}` — 个人信息
- `{{latex_template}}` — LaTeX 模板内容
- `{{JOB_DESCRIPTION}}` — 你提供的职位描述

## API 参考

### 任务

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/tasks` | 创建新任务 |
| `GET` | `/api/tasks` | 列出所有任务 |
| `GET` | `/api/tasks/{id}` | 获取任务详情 |
| `PUT` | `/api/tasks/{id}/settings` | 更新任务设置 |
| `POST` | `/api/tasks/{id}/start` | 开始处理（v2 流水线） |
| `POST` | `/api/tasks/{id}/start-v3` | 开始处理（v3 多智能体流水线） |
| `POST` | `/api/tasks/{id}/retry` | 重试失败/完成的任务 |
| `POST` | `/api/tasks/{id}/cancel` | 取消运行中的任务 |
| `DELETE` | `/api/tasks/{id}` | 删除任务 |
| `DELETE` | `/api/tasks` | 清除已完成的任务 |
| `GET` | `/api/tasks/{id}/resume` | 下载简历 PDF |
| `GET` | `/api/tasks/{id}/cover-letter` | 下载求职信 PDF |
| `GET` | `/api/tasks/{id}/latex` | 下载 LaTeX 源码 |

### 评估

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/tasks/{id}/evaluation` | 获取 ATS 评分细分（快速，无 LLM） |
| `POST` | `/api/tasks/{id}/evaluate` | 完整评估（ATS + LLM 评审） |

### 公司调研（RAG）

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/companies/scrape` | 爬取并索引公司网站 |
| `GET` | `/api/companies/{name}/info` | 获取已索引的公司数据 |
| `DELETE` | `/api/companies/{name}` | 清除公司缓存 |
| `GET` | `/api/companies` | 列出已索引的公司 |

### 申请问题

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/tasks/{id}/questions` | 列出任务的问题 |
| `POST` | `/api/tasks/{id}/questions` | 添加问题 |
| `PUT` | `/api/tasks/{id}/questions/{qid}` | 更新问题 |
| `DELETE` | `/api/tasks/{id}/questions/{qid}` | 删除问题 |
| `POST` | `/api/tasks/{id}/questions/{qid}/generate` | 生成单个问题的回答 |
| `POST` | `/api/tasks/{id}/questions/generate-all` | 批量生成所有未回答问题 |

### 设置与提示词

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/settings` | 获取所有设置 |
| `PUT` | `/api/settings` | 更新设置 |
| `POST` | `/api/settings/reset` | 重置为默认值 |
| `GET` | `/api/prompts` | 获取所有提示词 |
| `PUT` | `/api/prompts/{key}` | 更新提示词 |
| `GET` | `/api/providers` | 列出可用 AI 供应商 |
| `GET` | `/api/templates` | 列出简历模板 |
| `GET` | `/api/jd-history` | 获取职位描述历史 |
| `WS` | `/ws` | WebSocket 实时更新 |

## 项目结构

```
backend/
├── agents/                    # LangGraph 多智能体流水线（v3）
│   ├── graph.py               # StateGraph 定义与条件路由
│   ├── state.py               # ResumeState TypedDict
│   ├── schemas.py             # Pydantic 结构化输出模式
│   ├── jd_analyzer.py         # 职位描述分析智能体
│   ├── relevance_matcher.py   # 简历-JD 匹配智能体
│   ├── resume_writer.py       # LaTeX 简历生成智能体
│   ├── quality_gate.py        # ATS 评分 + 重试路由
│   ├── cover_letter_writer.py # 求职信生成智能体
│   └── finalize.py            # LaTeX 编译 + PDF 输出
├── evaluation/                # 简历自动评估
│   ├── ats_scorer.py          # 确定性 ATS 评分（6 项子分数）
│   ├── llm_judge.py           # LLM 评审（5 项评分维度）
│   ├── feedback_generator.py  # 评分转反馈
│   └── metrics.py             # 综合评估流水线
├── rag/                       # 公司调研（RAG 流水线）
│   ├── scraper.py             # 网页爬取（httpx + BeautifulSoup）
│   ├── chunker.py             # 文本分块与元数据
│   ├── embeddings.py          # 嵌入模型封装
│   ├── vector_store.py        # ChromaDB 向量数据库
│   ├── retriever.py           # 纠正式 RAG 检索
│   └── tools.py               # LangGraph 工具节点
├── db/                        # 数据库层（可选 PostgreSQL）
│   ├── base.py                # SQLAlchemy DeclarativeBase
│   ├── models.py              # ORM 模型（Profile、Task、Version、Metadata）
│   └── session.py             # 异步 Session 工厂
├── api/
│   ├── routes.py              # REST API 端点
│   └── websocket.py           # WebSocket 连接管理器
├── services/
│   ├── task_manager.py        # 任务编排与持久化
│   ├── langgraph_executor.py  # v3 流水线执行器
│   ├── provider_registry.py   # AI 供应商工厂
│   ├── ai_client_base.py      # AI 供应商抽象基类
│   ├── gemini_client.py       # Google Gemini 供应商
│   ├── claude_client.py       # Anthropic Claude 供应商
│   ├── claude_proxy_client.py # Claude 本地代理（SSE 流式传输）
│   ├── openai_compat_client.py# OpenAI 兼容供应商
│   ├── prompt_manager.py      # 提示词加载与替换
│   ├── settings_manager.py    # 设置持久化
│   ├── latex_compiler.py      # LaTeX 转 PDF 编译
│   ├── latex_utils.py         # LaTeX 响应解析与清理
│   ├── pdf_extractor.py       # PDF 文本提取（fitz/PyMuPDF）
│   ├── pdf_page_counter.py    # PDF 页数验证
│   └── text_to_pdf.py         # 纯文本转 PDF 备选方案（ReportLab）
├── middleware/
│   └── rate_limit.py          # slowapi 速率限制
├── alembic/                   # 数据库迁移
├── prompts/                   # 提示词模板文件
├── templates/                 # 简历样式模板
├── tests/
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   └── e2e/                   # 端到端测试
├── config.py                  # Pydantic 设置
├── main.py                    # FastAPI 应用入口
├── pyproject.toml             # 项目配置（uv/pip）
├── Dockerfile                 # Docker 多阶段构建
└── requirements.txt           # 传统 pip 依赖

frontend/
├── src/
│   ├── components/
│   │   ├── ui/                # shadcn 风格组件（Button、Card、Badge、Progress）
│   │   ├── TaskPanel.tsx      # 主任务 UI + 流水线选择 + 公司调研
│   │   ├── TaskSidebar.tsx    # 任务列表侧边栏
│   │   ├── QuestionsSection.tsx # 申请问题 CRUD
│   │   ├── SettingsPanel.tsx  # 设置弹窗（所有供应商）
│   │   ├── PromptsPanel.tsx   # 提示词模板编辑器
│   │   ├── ProgressDisplay.tsx# 实时步骤进度
│   │   ├── AgentProgress.tsx  # v3 流水线可视化
│   │   ├── SkillMatchChart.tsx# ATS 评分细分可视化
│   │   └── ToastContainer.tsx # Toast 通知
│   ├── hooks/
│   │   ├── useTaskQuery.ts    # TanStack Query hooks（查询 + 变更）
│   │   └── useWebSocket.ts    # WebSocket 连接 hook
│   ├── schemas/task.ts        # Zod 验证模式
│   ├── store/taskStore.ts     # Zustand（仅 UI 状态）
│   ├── lib/utils.ts           # cn() 工具函数（clsx + tailwind-merge）
│   ├── types/task.ts          # TypeScript 类型定义
│   └── tests/                 # Vitest + Testing Library 测试
├── Dockerfile                 # Docker 多阶段构建（Vite → nginx）
├── nginx.conf                 # nginx 配置与 API 代理
├── vitest.config.ts           # 测试运行器配置
├── package.json
└── vite.config.ts

docker-compose.yml             # 后端 + 前端 + PostgreSQL
.github/workflows/
├── ci.yml                     # 代码检查 + 测试（后端和前端）
└── security.yml               # Bandit + 依赖审计
commitlint.config.js           # 约定式提交强制检查
```

## 开发

### 运行测试

**后端**（350+ 测试）：
```bash
cd backend

# 使用 uv
uv run pytest --cov --cov-report=term-missing

# 使用 pip
pytest --cov --cov-report=term-missing

# 运行特定类别的测试
pytest tests/unit/                         # 仅单元测试
pytest tests/integration/                  # 仅集成测试
pytest tests/unit/agents/                  # 仅智能体测试
pytest tests/unit/test_latex_compiler.py   # 单个文件
```

**前端**（110+ 测试）：
```bash
cd frontend
npm test              # 单次运行
npm run test:watch    # 监听模式
```

### 代码检查

**后端：**
```bash
cd backend
uv run ruff check .        # 代码检查
uv run ruff format .       # 代码格式化
uv run mypy .              # 类型检查
```

**前端：**
```bash
cd frontend
npx tsc --noEmit           # 类型检查
```

### 提交规范

本项目使用[约定式提交](https://www.conventionalcommits.org/)：

```
feat(agents): add quality gate retry routing
fix(latex): handle empty href commands
test(evaluation): add ATS scorer tests
docs(readme): update architecture diagram
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `pdflatex not found` | 安装 MiKTeX（Windows）或 texlive（Linux/Mac） |
| `pdflatex timed out` | 打开 MiKTeX Console，将"安装缺失包"设为"始终" |
| WebSocket 连接失败 | 确保后端运行在端口 48765 |
| `Errno 10048: port already in use` | 终止占用端口的进程：`netstat -ano \| findstr :48765`，然后 `taskkill /PID <pid> /F` |
| 代理响应截断 | Claude Code Proxy 客户端默认使用 SSE 流式传输 |
| `Thinking level not supported` | 使用 Gemini 3+ 模型（如 `gemini-3.1-pro-preview`） |
| ChromaDB 导入错误 | 使用 `pip install chromadb` 安装（可选 — 未安装时 RAG 功能禁用） |
| Docker 构建 LaTeX 失败 | 确保 Docker 构建上下文中有可用的 texlive 包 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 智能体编排 | LangGraph（带条件边的 StateGraph） |
| LLM 供应商 | Gemini、Claude、OpenAI 兼容 |
| 评估 | 自定义 ATS 评分器 + LLM 评审 |
| RAG | ChromaDB + httpx/BeautifulSoup + sentence-transformers |
| 后端 | FastAPI + SQLAlchemy 2.0 async + Pydantic v2 |
| 前端 | React 18 + TypeScript + Vite |
| UI 组件 | shadcn/ui 模式（cva + tailwind-merge） |
| 服务端状态 | TanStack Query v5 |
| 客户端状态 | Zustand |
| 数据验证 | Zod（前端）+ Pydantic（后端） |
| 样式 | Tailwind CSS 含深色模式 |
| PDF | LaTeX 编译（pdflatex）+ ReportLab |
| 测试 | pytest + Vitest + Testing Library |
| CI/CD | GitHub Actions（ruff、mypy、pytest、tsc、vitest） |
| 容器 | Docker 多阶段 + docker-compose |
| 安全 | Bandit 扫描、slowapi 速率限制、依赖审计 |

## 许可证

MIT License
