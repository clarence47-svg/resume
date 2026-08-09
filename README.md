# 一体化智能投简历 Agent

基于 `LangGraph + FastAPI + Streamlit + Pydantic` 的本地单用户求职工作台。项目提供五维画像和 JD 匹配能力，并扩展岗位池、批量定制、ATS 简历、安全浏览器投递、进度跟踪与面试准备。

## 完整流程

```text
资料上传 → 五维画像 → 求职规则 → 岗位发现 → 硬筛选与评分
→ 批量 JD 匹配 → 定制简历 → 投递预览 → 用户确认
→ 提交验证 → 跟进看板 → 面试准备
```

## 六个工作区

1. **我的资料**：上传 DOC、DOCX、PDF、Markdown、PPT、PPTX，生成可持续补充的五维画像。
2. **求职设置**：管理联系方式、目标岗位、城市、薪资、排除规则和申请答案库。
3. **岗位池**：手动导入、官方页面发现、BOSS 浏览器采集、去重、硬筛选和评分。
4. **简历工作室**：单岗位或批量 JD 匹配，生成 ATS 简历及申请材料。
5. **投递中心**：连接 Chrome，安全预填、上传简历、展示预览并逐岗位确认。
6. **面试与跟进**：查看投递漏斗、阻塞事项、跟进计划和面试准备包。

## 核心能力

- 五维画像：个人信息、项目经历、比赛经历、实习经历、学校履历。
- 个人信息边界：只提取姓名、出生年月、籍贯、学校、电话、邮箱、求职方向、作品集和所在城市。
- 比赛真实性：赛事名称通过百度/必应模糊检索核验，缺少可靠来源时不进入最终比赛画像。
- 证据约束：事实和推断保留文件、页码/幻灯片/段落、原文引用与置信度。
- 经历素材聚合：只在“我的资料”生成五维完整素材池；同一经历的岗位化标题和不同职责表达作为互补素材，不误判为冲突。
- JD 匹配：每个岗位从画像快照动态生成能力维度，按直接匹配、可迁移能力、相邻经验和成果影响评分，不把历史岗位文案反写进画像。
- 简历版本：每个岗位保存五份岗位画像母版和一份最终简历 Markdown，同时提供 HTML、DOCX、PDF 导出。
- 批量定制：一次处理 1–20 个岗位，重复能力缺口只保留一个问题。
- 岗位规则：排除公司、岗位、外包、实习、地点、薪资和发布时间。
- 简历导出：JSON、Markdown、HTML、DOCX、PDF。
- 申请材料：Cover Letter、BOSS 招呼语、自我评价、为什么选择公司、为什么适合岗位。
- 安全投递：预览哈希、提交前重新校验、逐岗位确认、明确成功证据。
- 面试准备：岗位理解、60 秒自我介绍、STAR 故事、高频问题和反问清单。
- 无模型回退：未配置密钥时继续使用规则筛选和模板文案，并标记 `heuristic-fallback`。

## 安全边界

- 不绕过 CAPTCHA、Cloudflare、登录、2FA 或 OTP。
- 不保存招聘网站密码、Cookie、OTP 或浏览器用户目录。
- 最终提交、BOSS 招呼语和发送简历必须逐岗位确认。
- 页面变化会导致 `preview_hash` 失效，必须重新预览。
- 只有出现成功文字、确认 URL、申请编号或明确发送记录才标记 `submitted`。
- 敏感字段和未知必填字段进入 `needs_user`，Agent 不猜测。
- JD、网页和上传文档均按不可信数据处理，提示注入不能改变系统任务。
- 不制造画像中不存在的技能、单位、日期、奖项、数字或成果。
- 匹配分数仅用于排序和解释，不代表录用概率。

## 本地运行

要求 Python 3.12，推荐使用 `uv`：

```bash
cp .env.example .env
uv sync --all-groups
uv run python src/run_service.py
```

另开终端：

```bash
uv run streamlit run src/streamlit_app.py
```

- 页面：[http://127.0.0.1:8501](http://127.0.0.1:8501)
- API 文档：[http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

## 模型配置

在项目根目录 `.env` 填写：

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-key
PROFILE_MODEL=gpt-4.1-mini
MATCH_MODEL=
```

`MATCH_MODEL` 留空时复用 `PROFILE_MODEL`。OCR、Office 转换和文档解析在本机执行；必要文本片段会发送到配置的 OpenAI 兼容模型服务。

不填写 `LLM_API_KEY` 时，资料抽取、岗位匹配和材料生成使用规则回退。

## 浏览器投递配置

默认关闭浏览器自动化。BOSS 直聘连接建议使用项目提供的独立临时 Chrome 会话，关闭窗口后临时浏览器资料会被删除：

```bash
sh scripts/start_boss_chrome.sh
```

在打开的窗口中登录 BOSS 直聘，再回到“岗位池”点击“重新检测连接”。Docker 服务使用 `host.docker.internal:9222` 连接该会话。

也可以手动启动带 Remote Debugging 的 Chrome：

macOS：

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.resume-agent-chrome"
```

然后在 `.env` 设置：

```dotenv
BROWSER_AUTOMATION_ENABLED=true
CHROME_CDP_URL=http://host.docker.internal:9222
BROWSER_ACTION_TIMEOUT_SECONDS=30
BOSS_DAILY_ACTION_LIMIT=10
BOSS_ACTION_INTERVAL_MIN_SECONDS=90
BOSS_ACTION_INTERVAL_MAX_SECONDS=180
BOSS_DISCOVERY_MAX_JOBS=10
```

本地非 Docker 运行时可使用 `CHROME_CDP_URL=http://127.0.0.1:9222`。可运行 `uv run python scripts/check_chrome.py` 检查连接。

BOSS 的“直接投递”按平台实际交互实现为：生成岗位定制招呼语 → 提交前预览 → 用户逐岗位确认 → 发送招呼语 → 验证聊天记录。系统不会自动绕过登录/验证码，也不会在 HR 未请求时自动发送简历附件。

## Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Compose 启动 PostgreSQL、FastAPI 和 Streamlit，端口仅绑定本机。原件、解析结果、简历、投递证据和导出文件保存在 Docker volume 中。

更新代码后：

```bash
docker compose up -d --build agent_service streamlit_app
sh scripts/smoke_test.sh
```

## 主要 API

### 画像与 JD 匹配

- `POST/GET /profiles`
- `POST /profiles/{task_id}/documents`
- `GET/PUT /profiles/{task_id}/facts`
- `POST /profiles/{task_id}/resume|regenerate|retry`
- `GET /profiles/{task_id}/result|export`
- `DELETE /profiles/{task_id}`
- `POST/GET /matches`
- `GET /matches/{match_id}/result|versions|export`
- `PUT /matches/{match_id}/draft`
- `POST /matches/{match_id}/regenerate|retry`

### 求职设置、岗位与批量定制

- `GET/PUT /career/settings`
- `GET/PUT /career/answers`
- `POST/GET /campaigns`
- `POST /campaigns/{id}/discover`
- `GET /campaigns/{id}/jobs`
- `POST /jobs/import`
- `POST /jobs/{id}/evaluate`
- `POST /tailoring-batches`
- `GET/POST /tailoring-batches/{id}`

### 简历、投递与跟进

- `POST /jobs/{id}/resume`
- `GET /resumes/{id}/export?format=json|md|html|docx|pdf`
- `GET /resumes/{id}/documents/{personal_introduction|project_experiences|competition_experiences|internship_experiences|education_history|final_resume}`
- `POST /applications`
- `GET /applications/{id}/preview`
- `POST /applications/{id}/confirm|resume|cancel`
- `GET /tracking/dashboard`
- `POST /interviews`
- `GET /interviews/{id}/export`

## 数据目录

```text
data/
├── uploads/                 # 原始资料
├── parsed/                  # 标准化文档与五维素材
├── jobs/                    # 岗位采集数据
├── resumes/                 # 简历版本数据
├── applications/            # 提交确认截图与证据
└── exports/
    ├── matches/
    ├── resumes/
    ├── applications/
    └── interviews/
```

删除画像任务时会级联删除关联岗位快照、匹配任务、简历、投递记录、面试包和本地证据文件。

## 开发验证

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
sh scripts/smoke_test.sh
```

当前测试使用本地 HTML Fixture 验证 Greenhouse、Lever、Ashby 和通用表单，不会在 CI 操作真实招聘网站。

## 许可证

本项目使用 MIT License。行为参考和第三方许可证说明见 `THIRD_PARTY_NOTICES.md`。
