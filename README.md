# 用户资料六维画像 Agent

这是一个参考 `agent-service-toolkit` 架构实现的双 Agent 服务。资料画像 Agent 接收 Word、PDF、Markdown 和 PowerPoint，生成可追溯的六维中文画像；JD 匹配 Agent 使用历史画像和岗位描述，生成岗位匹配分析与六维简历投递文案。

## 特性

- FastAPI 多文件上传、异步任务、状态查询、失败重试和彻底删除。
- LangGraph 分块事实抽取、冲突合并、可选人工确认、六路并行生成和审计。
- Docling 主解析，PDF/DOCX/PPTX 本地解析回退，扫描 PDF 使用 RapidOCR。
- `.doc/.ppt` 使用 LibreOffice 无头转换，Docker 镜像内已安装。
- PostgreSQL 或 SQLite 持久化，LangGraph 检查点可恢复人工确认流程。
- Streamlit 上传与审核页面，支持 JSON、Markdown、DOCX 下载。
- JD 匹配度、六维评分、关键词覆盖、优势、缺口和最相关经历筛选。
- JD 文案可编辑、保存版本、恢复历史版本并重新生成。
- 未配置模型时可明确使用规则回退，结果会标记为 `heuristic-fallback`。

## 本地运行

要求 Python 3.12–3.14。推荐使用 `uv`：

```bash
cp .env.example .env
uv sync --dev
uv run python src/run_service.py
```

另开终端启动页面：

```bash
uv run streamlit run src/streamlit_app.py
```

访问 `http://127.0.0.1:8501`。API 文档位于 `http://127.0.0.1:8080/docs`。

要获得完整 AI 画像，请在 `.env` 配置：

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-key
PROFILE_MODEL=gpt-4.1-mini
MATCH_MODEL=
```

`MATCH_MODEL` 留空时复用 `PROFILE_MODEL`。

该接口兼容支持 OpenAI API 协议的模型服务。必要文本片段会发送到这里配置的服务，OCR 和文件解析在本机完成。

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Compose 会启动 PostgreSQL、Agent 服务和 Streamlit，并把端口仅绑定到本机。原始文件、解析结果和导出文件保存在 Docker volume 中。
API 与 Streamlit 复用同一个服务镜像，避免重复打包 Docling；Linux 镜像固定解析为 CPU 版 Torch，不会下载 CUDA 运行库。

## API

创建任务：

```bash
curl -X POST http://127.0.0.1:8080/profiles \
  -F 'files=@resume.pdf' \
  -F 'files=@portfolio.pptx' \
  -F 'review_mode=pause' \
  -F 'title=个人画像'
```

主要接口：

- `GET /profiles`：历史任务。
- `GET /profiles/{task_id}`：进度和文件状态。
- `GET/PUT /profiles/{task_id}/facts`：查看或修改事实。
- `POST /profiles/{task_id}/resume`：人工核对后继续。
- `POST /profiles/{task_id}/regenerate`：根据当前事实重生成。
- `POST /profiles/{task_id}/retry`：重试失败任务。
- `GET /profiles/{task_id}/result`：结构化结果。
- `GET /profiles/{task_id}/export?format=md|docx`：下载文档。
- `DELETE /profiles/{task_id}`：彻底删除任务资料。

JD 匹配接口：

- `POST /matches`：选择已完成画像并提交 JD。
- `GET /matches`：获取岗位匹配历史。
- `GET /matches/{match_id}/result`：获取匹配分析和六维文案。
- `GET /matches/{match_id}/versions`：查看文案版本。
- `PUT /matches/{match_id}/draft`：编辑文案并保存新版本。
- `POST /matches/{match_id}/versions/{version}/restore`：恢复历史版本。
- `POST /matches/{match_id}/regenerate`：使用原始快照重新生成。
- `GET /matches/{match_id}/export?format=json|md|docx`：导出结果。
- `DELETE /matches/{match_id}`：删除匹配任务和全部版本。

## 文件处理说明

- 支持 `.doc/.docx/.pdf/.md/.ppt/.pptx`。
- 每次默认最多 20 个文件、单文件 50 MB、总大小 200 MB、总页数或幻灯片 500。
- 本机未安装 LibreOffice 时，旧版 `.doc/.ppt` 会返回明确错误；Docker 镜像内可直接处理。
- Docling 首次处理复杂文档时可能下载本地模型，首次启动耗时会更长。
- 加密 PDF、损坏文件、扩展名与内容不一致、压缩炸弹会被拒绝。
- Markdown 中的外部链接和本地图片不会被主动下载。

## 安全与画像原则

- 文档内容始终作为不可信数据，文件中的提示注入不会改变系统任务。
- 每条事实和推断保留文件、页码或段落、原文引用和置信度。
- 可深入归纳专业能力、工作特点和职业方向，但不推断健康、政治、宗教、民族、性取向等敏感属性。
- 不制造材料中不存在的日期、单位、学校、奖项和量化数字。
- JD 文案可以强化表达，但不得加入画像事实不支持的岗位技能或硬事实。
- JD 匹配分数用于排序和解释，不代表招聘录用概率。
- 服务默认单机使用且无账号系统，不应未经加固直接暴露到公网。

## 开发验证

```bash
uv run ruff check .
uv run pytest
```

服务启动后可运行：

```bash
sh scripts/smoke_test.sh
```
