# ruff: noqa: E501

import hashlib
import html
import json
import os
import time
from datetime import datetime

import streamlit as st

from client import (
    CareerClient,
    CareerClientError,
    MatchClient,
    MatchClientError,
    ProfileClient,
    ProfileClientError,
)

st.set_page_config(
    page_title="Resume Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

DIMENSIONS = [
    ("personal_introduction", "个人介绍", "个人定位、优势与职业方向"),
    ("professional_introduction", "专业介绍", "知识结构、技能与研究方向"),
    ("project_experiences", "项目经历", "项目行动、方法与成果"),
    ("competition_experiences", "比赛经历", "竞赛贡献、奖项与成长"),
    ("internship_experiences", "实习经历", "岗位职责、成果与协作"),
    ("education_history", "学校履历", "教育背景、课程与荣誉"),
]

STATUS_META = {
    "queued": ("等待处理", "◷", "neutral"),
    "parsing": ("解析资料", "◌", "active"),
    "extracting": ("提取事实", "◌", "active"),
    "awaiting_review": ("等待核对", "!", "warning"),
    "generating": ("生成内容", "◌", "active"),
    "auditing": ("质量审计", "◌", "active"),
    "analyzing_jd": ("分析岗位", "◌", "active"),
    "matching": ("能力匹配", "◌", "active"),
    "completed": ("已完成", "✓", "success"),
    "partial_success": ("部分完成", "!", "warning"),
    "failed": ("处理失败", "×", "danger"),
    "failed_retryable": ("可重试", "↻", "danger"),
}

PROFILE_SELECTOR_KEY = "profile_task_selector"
MATCH_SELECTOR_KEY = "match_task_selector"
SUBMISSION_DEDUP_SECONDS = 30


@st.cache_resource
def get_profile_client() -> ProfileClient:
    return ProfileClient(os.getenv("AGENT_URL", "http://127.0.0.1:8080"))


@st.cache_resource
def get_match_client() -> MatchClient:
    return MatchClient(os.getenv("AGENT_URL", "http://127.0.0.1:8080"))


@st.cache_resource
def get_career_client() -> CareerClient:
    return CareerClient(os.getenv("AGENT_URL", "http://127.0.0.1:8080"))


def main() -> None:
    inject_theme()
    render_flash()
    render_sidebar_brand()
    workspace = st.sidebar.radio(
        "主导航",
        ["我的资料", "求职设置", "岗位池", "简历工作室", "投递中心", "面试与跟进"],
        format_func=lambda value: {
            "我的资料": "◫  我的资料",
            "求职设置": "⚙  求职设置",
            "岗位池": "⌕  岗位池",
            "简历工作室": "✦  简历工作室",
            "投递中心": "➤  投递中心",
            "面试与跟进": "◎  面试与跟进",
        }[value],
        label_visibility="collapsed",
    )
    st.sidebar.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
    if workspace == "我的资料":
        render_profile_workspace(get_profile_client())
    elif workspace == "求职设置":
        render_career_settings(get_career_client())
    elif workspace == "岗位池":
        render_job_pool(get_profile_client(), get_career_client())
    elif workspace == "简历工作室":
        render_resume_studio(get_profile_client(), get_match_client(), get_career_client())
    elif workspace == "投递中心":
        render_application_center(get_career_client())
    else:
        render_interview_tracker(get_career_client())
    render_sidebar_footer()


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172033;
            --muted: #697386;
            --line: #e7eaf0;
            --panel: #ffffff;
            --canvas: #f5f7fb;
            --primary: #665cf6;
            --primary-dark: #4f46d8;
            --cyan: #24b6c7;
        }
        html, body, [class*="css"] {
            font-family: Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
        }
        .stApp { background: var(--canvas); color: var(--ink); }
        [data-testid="stHeader"], #MainMenu, footer { visibility: hidden; }
        [data-testid="stMainBlockContainer"] {
            max-width: 1460px;
            padding: 2.2rem 3.2rem 4rem;
        }
        [data-testid="stSidebar"] {
            width: 292px !important;
            min-width: 292px !important;
            left: 0 !important;
            transform: none !important;
            position: fixed !important;
            background:
                radial-gradient(circle at 15% 5%, rgba(118, 107, 255, .30), transparent 33%),
                linear-gradient(180deg, #171a2d 0%, #101321 58%, #0d101b 100%);
            border-right: 1px solid rgba(255,255,255,.06);
        }
        [data-testid="stMain"] {
            margin-left: 292px !important;
            width: calc(100% - 292px) !important;
        }
        [data-testid="stSidebarContent"] { padding: 1.4rem 1.15rem 1.5rem; }
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        [data-testid="stSidebar"] * { color: #eef0ff; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #aeb4cc; }
        [data-testid="stSidebar"] .stRadio > div { gap: .4rem; }
        [data-testid="stSidebar"] .stRadio input { position: absolute; opacity: 0; }
        [data-testid="stSidebar"] .stRadio label {
            padding: .72rem .82rem;
            border-radius: 12px;
            transition: all .18s ease;
        }
        [data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,.07); }
        [data-testid="stSidebar"] .stRadio label:has(input:checked) {
            background: linear-gradient(135deg, rgba(112,99,255,.35), rgba(47,186,207,.16));
            box-shadow: inset 0 0 0 1px rgba(153,145,255,.34);
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] .react-aria-ComboBox > div {
            background: rgba(255,255,255,.075);
            border-color: rgba(255,255,255,.13);
            border-radius: 12px;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] input {
            color: #eef0ff !important;
            -webkit-text-fill-color: #eef0ff !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] button svg { fill: #daddf3; }
        [data-testid="stSidebar"] .stSelectbox label p { color: #c5c9dc; font-size: .79rem; }
        [data-testid="stSidebar"] .stButton button {
            min-height: 2.55rem; padding: .45rem .5rem;
            background: rgba(239, 74, 91, .12); border-color: rgba(255, 120, 135, .28);
            color: #ffb6bf;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background: rgba(239, 74, 91, .2); border-color: rgba(255, 140, 151, .48);
            color: #ffd5da; box-shadow: 0 7px 18px rgba(167, 39, 61, .18);
        }
        [data-testid="stSidebar"] .stButton button:disabled {
            background: rgba(255,255,255,.045); border-color: rgba(255,255,255,.08);
            color: #69708a;
        }
        .brand-wrap { display: flex; align-items: center; gap: .75rem; margin: .1rem .15rem 1.55rem; }
        .brand-mark {
            width: 42px; height: 42px; border-radius: 13px; display: grid; place-items: center;
            font-size: 1.28rem; font-weight: 800; color: white;
            background: linear-gradient(145deg, #7a70ff, #35bfd0);
            box-shadow: 0 10px 28px rgba(87,77,236,.35);
        }
        .brand-title { color: white; font-weight: 760; letter-spacing: -.02em; font-size: 1rem; }
        .brand-sub { color: #8f96b1; font-size: .69rem; letter-spacing: .08em; text-transform: uppercase; }
        .sidebar-rule { height: 1px; background: rgba(255,255,255,.08); margin: .9rem .15rem 1rem; }
        .sidebar-label { color: #858da8; font-size: .68rem; text-transform: uppercase; letter-spacing: .12em; margin: .3rem .15rem .6rem; }
        .sidebar-stats {
            display: grid; grid-template-columns: 1fr 1fr; gap: .55rem; margin: .9rem 0;
        }
        .sidebar-stat {
            padding: .72rem .68rem; border-radius: 12px; background: rgba(255,255,255,.055);
            border: 1px solid rgba(255,255,255,.075);
        }
        .sidebar-stat strong { display: block; font-size: 1.03rem; color: #fff; }
        .sidebar-stat span { color: #8d95af; font-size: .68rem; }
        .sidebar-footer {
            margin-top: 1.2rem; padding: .85rem; border-radius: 12px;
            background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.06);
            color: #8f96af; font-size: .72rem; line-height: 1.55;
        }
        .online-dot { display: inline-block; width: 7px; height: 7px; background: #55d6a5; border-radius: 50%; margin-right: .35rem; box-shadow: 0 0 0 4px rgba(85,214,165,.11); }
        .page-hero {
            position: relative; overflow: hidden; border-radius: 22px; padding: 1.8rem 2rem;
            margin-bottom: 1.25rem; color: white;
            background: linear-gradient(125deg, #25284a 0%, #4f48c9 62%, #2aaec1 120%);
            box-shadow: 0 18px 45px rgba(45,50,105,.18);
        }
        .page-hero:after {
            content: ""; position: absolute; width: 290px; height: 290px; right: -80px; top: -150px;
            border-radius: 50%; border: 1px solid rgba(255,255,255,.20); box-shadow: 0 0 0 42px rgba(255,255,255,.035), 0 0 0 86px rgba(255,255,255,.025);
        }
        .eyebrow { font-size: .7rem; letter-spacing: .14em; text-transform: uppercase; color: #cdd1ff; font-weight: 700; }
        .hero-title { margin: .38rem 0 .4rem; font-size: 2rem; line-height: 1.18; font-weight: 780; letter-spacing: -.035em; }
        .hero-sub { max-width: 760px; color: rgba(255,255,255,.74); font-size: .91rem; line-height: 1.65; }
        .section-heading { margin: 1.4rem 0 .72rem; }
        .section-heading h3 { margin: 0; font-size: 1.05rem; letter-spacing: -.015em; }
        .section-heading p { margin: .2rem 0 0; color: var(--muted); font-size: .78rem; }
        .metric-card {
            min-height: 106px; padding: 1.05rem 1.12rem; border-radius: 17px;
            background: white; border: 1px solid var(--line); box-shadow: 0 8px 28px rgba(32,42,73,.055);
        }
        .metric-label { color: #7b8497; font-size: .72rem; font-weight: 650; letter-spacing: .03em; }
        .metric-value { color: #1d2639; font-size: 1.65rem; font-weight: 780; letter-spacing: -.035em; margin: .28rem 0 .1rem; }
        .metric-note { color: #9aa1af; font-size: .68rem; }
        .task-banner {
            padding: 1.15rem 1.25rem; border: 1px solid var(--line); border-radius: 17px;
            background: rgba(255,255,255,.92); box-shadow: 0 8px 28px rgba(32,42,73,.045);
            margin-bottom: .85rem;
        }
        .task-title { font-size: 1.16rem; font-weight: 740; color: var(--ink); }
        .task-meta { color: var(--muted); font-size: .73rem; margin-top: .25rem; }
        .status-pill { display: inline-flex; align-items: center; gap: .3rem; padding: .28rem .58rem; border-radius: 999px; font-size: .68rem; font-weight: 720; }
        .status-success { background: #e8f8f1; color: #20825f; }
        .status-active { background: #eeedff; color: #5b51dc; }
        .status-warning { background: #fff4df; color: #a76a12; }
        .status-danger { background: #feecef; color: #bd4053; }
        .status-neutral { background: #edf0f5; color: #626d80; }
        .soft-panel {
            padding: 1rem 1.1rem; border-radius: 15px; background: #f8f9fc;
            border: 1px solid #ebeef4; color: #4f596b; line-height: 1.7; font-size: .86rem;
        }
        .insight-card {
            height: 100%; padding: 1rem 1.05rem; border-radius: 15px; border: 1px solid var(--line);
            background: #fff; box-shadow: 0 7px 22px rgba(34,42,70,.045);
        }
        .insight-card.good { border-top: 3px solid #36b788; }
        .insight-card.gap { border-top: 3px solid #f3a642; }
        .insight-title { font-size: .78rem; font-weight: 740; color: #40495a; margin-bottom: .65rem; }
        .chip-wrap { display: flex; flex-wrap: wrap; gap: .42rem; margin: .45rem 0 .25rem; }
        .chip { display: inline-flex; padding: .28rem .55rem; border-radius: 999px; background: #efefff; color: #544bd0; border: 1px solid #dfdefe; font-size: .68rem; font-weight: 650; }
        .chip.cyan { background: #eaf9fb; color: #187f8e; border-color: #d1f0f4; }
        .chip.gray { background: #f1f3f6; color: #606a7c; border-color: #e4e7ec; }
        .empty-hint { padding: 1.4rem; text-align: center; color: #8790a0; background: #fafbfc; border: 1px dashed #dce0e8; border-radius: 14px; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255,255,255,.96); border-color: var(--line) !important;
            border-radius: 17px !important; box-shadow: 0 8px 28px rgba(32,42,73,.045);
        }
        [data-testid="stMetric"] {
            background: white; border: 1px solid var(--line); border-radius: 16px; padding: .9rem 1rem;
            box-shadow: 0 7px 24px rgba(32,42,73,.045);
        }
        [data-testid="stMetricLabel"] p { color: #7a8395; font-size: .75rem; }
        [data-testid="stMetricValue"] { color: #1c2537; font-weight: 760; }
        .stButton button, .stDownloadButton button {
            min-height: 2.55rem; border-radius: 11px; font-weight: 680; border-color: #dfe3eb;
            transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
        }
        .stButton button:hover, .stDownloadButton button:hover {
            transform: translateY(-1px); border-color: #8178f8; box-shadow: 0 7px 18px rgba(87,78,220,.12);
        }
        .stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {
            background: linear-gradient(135deg, #6e63f5, #554bd9); border: none; color: white;
        }
        [data-baseweb="input"] > div, [data-baseweb="textarea"] > div {
            border-radius: 11px; border-color: #e1e5ec; background: #fff;
        }
        [data-testid="stFileUploaderDropzone"] {
            border-radius: 15px; border: 1.5px dashed #cfd4e1; background: #fafbfe; padding: 1.25rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem; background: #ebeef4; padding: .34rem; border-radius: 13px; width: fit-content;
        }
        .stTabs [data-baseweb="tab"] { border-radius: 9px; padding: .45rem .78rem; height: auto; }
        .stTabs [aria-selected="true"] { background: white; box-shadow: 0 3px 10px rgba(36,43,67,.08); }
        .stTabs [data-baseweb="tab-highlight"] { display: none; }
        [data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 13px; background: #fff; }
        [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 13px; overflow: hidden; }
        [data-testid="stProgress"] [role="progressbar"] > div {
            background: linear-gradient(90deg, #6e63f5, #2cb6c6) !important;
        }
        hr { border-color: #e5e8ee; }
        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] { padding: 1.2rem 1rem 3rem; }
            .page-hero { padding: 1.35rem 1.2rem; }
            .hero-title { font-size: 1.55rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="brand-wrap">
            <div class="brand-mark">✦</div>
            <div>
                <div class="brand-title">Resume Intelligence</div>
                <div class="brand-sub">Profile & JD Agent</div>
            </div>
        </div>
        <div class="sidebar-label">Workspace</div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_footer() -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-footer">
            <div><span class="online-dot"></span>Agent 服务运行中</div>
            <div style="margin-top:.35rem;">本地部署 · 数据持续保留<br>模型输出经过事实一致性审计</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_workspace(client: ProfileClient) -> None:
    try:
        tasks = client.list_profiles()
    except ProfileClientError as exc:
        render_page_header("System", "资料画像", "连接服务后即可管理用户画像任务。")
        st.error(f"无法连接 Agent 服务：{exc}")
        return

    render_page_header(
        "Profile Builder",
        "把零散资料整理成清晰的六维画像",
        "上传 Word、PDF、Markdown 或 PowerPoint。Agent 会解析证据、聚合同一经历，并生成六份可追溯画像文档。",
    )
    labels = {task["id"]: task_label(task) for task in tasks}
    options = ["", *list(labels)]
    prepare_selector(PROFILE_SELECTOR_KEY, options)
    metric_col, spacer_col, selector_col, delete_col = st.columns(
        [1.1, 1.2, 2.5, 0.7], vertical_alignment="bottom"
    )
    with metric_col:
        render_metric_card("历史画像", str(len(tasks)), "持续保留，可随时重新生成")
    with spacer_col:
        st.empty()
    with selector_col:
        selected = st.selectbox(
            "我的画像任务",
            options=options,
            format_func=lambda value: "＋ 创建新画像" if not value else labels[value],
            key=PROFILE_SELECTOR_KEY,
        )
    with delete_col:
        delete_clicked = st.button(
            "删除",
            key="page-delete-profile",
            disabled=not selected,
            help="删除当前画像；处理中任务会立即取消",
            use_container_width=True,
        )
    if delete_clicked:
        delete_profile_task(client, selected)
    if selected:
        render_task(client, selected)
    else:
        render_upload(client)


def render_match_workspace(profile_client: ProfileClient, match_client: MatchClient) -> None:
    try:
        profiles = [
            task
            for task in profile_client.list_profiles()
            if task["status"] in {"completed", "partial_success"}
        ]
        matches = match_client.list_matches()
    except (ProfileClientError, MatchClientError) as exc:
        render_page_header("System", "JD 岗位匹配", "连接服务后即可创建岗位匹配任务。")
        st.error(f"无法连接 Agent 服务：{exc}")
        return

    completed = sum(item["status"] in {"completed", "partial_success"} for item in matches)
    active = sum(
        item["status"] in {"queued", "analyzing_jd", "matching", "generating", "auditing"}
        for item in matches
    )
    render_sidebar_stats(len(matches), completed, active)
    labels = {item["id"]: task_label(item) for item in matches}
    st.sidebar.markdown('<div class="sidebar-label">Match Tasks</div>', unsafe_allow_html=True)
    options = ["", *list(labels)]
    prepare_selector(MATCH_SELECTOR_KEY, options)
    selector_col, delete_col = st.sidebar.columns([4.6, 1.4], vertical_alignment="center")
    with selector_col:
        selected = st.selectbox(
            "JD 匹配历史",
            options=options,
            format_func=lambda value: "＋  创建岗位匹配" if not value else labels[value],
            label_visibility="collapsed",
            key=MATCH_SELECTOR_KEY,
        )
    with delete_col:
        delete_clicked = st.button(
            "删除",
            key="sidebar-delete-match",
            disabled=not selected,
            help="删除当前匹配；处理中任务会立即取消",
            use_container_width=True,
        )
    if delete_clicked:
        delete_match_task(match_client, selected)
    if selected:
        render_match_task(match_client, selected)
    else:
        render_match_create(match_client, profiles, matches)


def render_career_settings(client: CareerClient) -> None:
    render_page_header(
        "Career Rules",
        "定义你的求职边界与申请答案",
        "联系方式和敏感申请答案仅在本地加密保存；未知敏感字段不会由 Agent 猜测。",
    )
    try:
        settings = client.get_settings()
        answers = client.list_answers()
    except CareerClientError as exc:
        st.error(f"无法读取求职设置：{exc}")
        return
    profile_tab, rules_tab, answers_tab = st.tabs(["基本档案", "筛选与安全规则", "申请答案库"])
    with profile_tab:
        with st.form("career-profile-form"):
            left, right = st.columns(2)
            with left:
                display_name = st.text_input("姓名", value=settings.get("display_name", ""))
                email = st.text_input("邮箱", value=settings.get("email", ""))
                phone = st.text_input("手机", value=settings.get("phone", ""))
                city = st.text_input("当前城市", value=settings.get("city", ""))
                target_roles = st.text_input(
                    "目标岗位（逗号分隔）", value="，".join(settings.get("target_roles", []))
                )
                target_cities = st.text_input(
                    "目标城市（逗号分隔）", value="，".join(settings.get("target_cities", []))
                )
            with right:
                github_url = st.text_input("GitHub", value=settings.get("github_url", ""))
                linkedin_url = st.text_input("LinkedIn", value=settings.get("linkedin_url", ""))
                portfolio_url = st.text_input("作品集", value=settings.get("portfolio_url", ""))
                work_authorization = st.text_input(
                    "工作授权/签证说明", value=settings.get("work_authorization", "")
                )
                salary_min = st.number_input(
                    "期望最低月薪（K）",
                    min_value=0.0,
                    value=float(settings.get("salary_min_k") or 0),
                )
                salary_max = st.number_input(
                    "期望最高月薪（K）",
                    min_value=0.0,
                    value=float(settings.get("salary_max_k") or 0),
                )
            if st.form_submit_button("保存基本档案", type="primary", use_container_width=True):
                updated = dict(settings)
                updated.update(
                    {
                        "display_name": display_name,
                        "email": email,
                        "phone": phone,
                        "city": city,
                        "target_roles": split_values(target_roles),
                        "target_cities": split_values(target_cities),
                        "github_url": github_url,
                        "linkedin_url": linkedin_url,
                        "portfolio_url": portfolio_url,
                        "work_authorization": work_authorization,
                        "salary_min_k": salary_min or None,
                        "salary_max_k": salary_max or None,
                    }
                )
                try:
                    client.save_settings(updated)
                    set_flash("求职基本档案已保存")
                    st.rerun()
                except CareerClientError as exc:
                    st.error(f"保存失败：{exc}")
    with rules_tab:
        rules = settings.get("rules", {})
        with st.form("career-rules-form"):
            col1, col2 = st.columns(2)
            with col1:
                minimum_match_score = st.slider(
                    "最低匹配分", 0, 100, int(rules.get("minimum_match_score", 65))
                )
                precision_score_threshold = st.slider(
                    "推荐投递阈值", 0, 100, int(rules.get("precision_score_threshold", 82))
                )
                excluded_companies = st.text_area(
                    "排除公司", value="\n".join(rules.get("excluded_companies", []))
                )
                excluded_keywords = st.text_area(
                    "排除岗位关键词", value="\n".join(rules.get("excluded_keywords", []))
                )
            with col2:
                allow_internship = st.checkbox(
                    "接受实习岗位", value=rules.get("allow_internship", False)
                )
                allow_outsource = st.checkbox(
                    "接受外包岗位", value=rules.get("allow_outsource", False)
                )
                daily_action_limit = st.number_input(
                    "每日最大浏览器操作数",
                    min_value=1,
                    max_value=100,
                    value=int(rules.get("daily_action_limit", 10)),
                )
                require_submission_confirmation = st.checkbox(
                    "最终提交必须逐岗位确认",
                    value=rules.get("require_submission_confirmation", True),
                    disabled=True,
                )
            if st.form_submit_button("保存规则", type="primary", use_container_width=True):
                updated = dict(settings)
                updated_rules = dict(rules)
                updated_rules.update(
                    {
                        "minimum_match_score": minimum_match_score,
                        "precision_score_threshold": precision_score_threshold,
                        "excluded_companies": split_values(excluded_companies),
                        "excluded_keywords": split_values(excluded_keywords),
                        "allow_internship": allow_internship,
                        "allow_outsource": allow_outsource,
                        "daily_action_limit": daily_action_limit,
                        "require_submission_confirmation": require_submission_confirmation,
                    }
                )
                updated["rules"] = updated_rules
                try:
                    client.save_settings(updated)
                    set_flash("求职规则已保存")
                    st.rerun()
                except CareerClientError as exc:
                    st.error(f"保存失败：{exc}")
    with answers_tab:
        st.caption("仅状态为 confirmed 的答案会用于安全预填；敏感答案仍需提交前确认。")
        for index, answer in enumerate(answers):
            with st.expander(answer.get("question") or answer.get("question_key", "申请问题")):
                st.write(answer.get("answer", ""))
                st.caption(f"状态：{answer.get('status')} · 敏感级别：{answer.get('sensitivity')}")
                if st.button("删除答案", key=f"delete-answer-{answer.get('id')}-{index}"):
                    try:
                        client.save_answers(
                            [item for item in answers if item.get("id") != answer.get("id")]
                        )
                        set_flash("申请答案已删除")
                        st.rerun()
                    except CareerClientError as exc:
                        st.error(f"删除失败：{exc}")
        with st.form("answer-bank-form", clear_on_submit=True):
            question_key = st.text_input("问题键", placeholder="why_company")
            question = st.text_input("问题", placeholder="为什么选择我们公司？")
            answer_text = st.text_area("答案")
            confirmed = st.checkbox("已确认，可用于预填")
            if st.form_submit_button("添加并保存", type="primary"):
                new_answer = {
                    "question_key": question_key,
                    "question": question,
                    "answer": answer_text,
                    "sensitivity": "normal",
                    "status": "confirmed" if confirmed else "draft",
                    "tags": [],
                }
                try:
                    client.save_answers([*answers, new_answer])
                    set_flash("申请答案已保存")
                    st.rerun()
                except CareerClientError as exc:
                    st.error(f"保存失败：{exc}")


def render_job_pool(profile_client: ProfileClient, client: CareerClient) -> None:
    render_page_header(
        "Job Discovery",
        "发现、去重并筛选值得投递的岗位",
        "硬过滤先执行，不合规岗位不会调用大模型；评分只用于排序和解释。",
    )
    try:
        browser = client.browser_status()
    except CareerClientError as exc:
        browser = {"enabled": False, "connected": False, "message": str(exc)}
    with st.container(border=True):
        status_text = (
            "已登录 BOSS"
            if browser.get("boss_logged_in")
            else "Chrome 已连接"
            if browser.get("connected")
            else "等待连接"
        )
        st.markdown(f"### BOSS 直聘连接 · {status_text}")
        st.caption(
            browser.get("message") or "使用独立 Chrome 会话，不读取或保存你的日常浏览器资料。"
        )
        if not browser.get("connected"):
            st.code("sh scripts/start_boss_chrome.sh", language="bash")
        boss_actions = st.columns(2)
        with boss_actions[0]:
            if st.button("打开 BOSS 登录页", use_container_width=True):
                try:
                    client.open_boss()
                    set_flash("BOSS 登录页已在独立 Chrome 中打开")
                    st.rerun()
                except CareerClientError as exc:
                    st.error(f"打开失败：{exc}")
        with boss_actions[1]:
            if st.button("重新检测连接", use_container_width=True):
                st.rerun()
    try:
        profiles = [
            item
            for item in profile_client.list_profiles()
            if item["status"] in {"completed", "partial_success"}
        ]
        campaigns = client.list_campaigns()
    except (ProfileClientError, CareerClientError) as exc:
        st.error(f"读取岗位池失败：{exc}")
        return
    with st.expander("＋ 创建求职活动", expanded=not campaigns):
        with st.form("campaign-create-form"):
            profile_id = (
                st.selectbox(
                    "选择画像",
                    options=[item["id"] for item in profiles],
                    format_func=lambda value: next(
                        (item["title"] for item in profiles if item["id"] == value), value
                    ),
                )
                if profiles
                else ""
            )
            title = st.text_input("活动名称", placeholder="2026 秋招 · AI 应用开发")
            keywords = st.text_input("搜索关键词", placeholder="AI 应用开发，后端开发")
            cities = st.text_input("目标城市", placeholder="上海，杭州")
            if st.form_submit_button("创建活动", type="primary", disabled=not profiles):
                try:
                    client.create_campaign(
                        {
                            "profile_task_id": profile_id,
                            "title": title,
                            "strategy": "volume",
                            "search_keywords": split_values(keywords),
                            "target_cities": split_values(cities),
                            "source_platforms": ["manual", "official", "boss"],
                        }
                    )
                    set_flash("求职活动已创建")
                    st.rerun()
                except CareerClientError as exc:
                    st.error(f"创建失败：{exc}")
    if not campaigns:
        render_empty("先创建一个求职活动，再导入或发现岗位。")
        return
    campaign_id = st.selectbox(
        "当前求职活动",
        [item["id"] for item in campaigns],
        format_func=lambda value: next(item["title"] for item in campaigns if item["id"] == value),
    )
    current_campaign = next(item for item in campaigns if item["id"] == campaign_id)
    action1, action2 = st.columns([3, 1])
    with action1:
        with st.form("manual-job-form", clear_on_submit=True):
            company = st.text_input("公司")
            job_title = st.text_input("职位")
            location = st.text_input("地点")
            source_url = st.text_input("岗位链接")
            jd_text = st.text_area("JD 全文", height=220)
            if st.form_submit_button("导入并评分", type="primary", use_container_width=True):
                try:
                    client.discover(
                        campaign_id,
                        {
                            "include_official_search": False,
                            "manual_jobs": [
                                {
                                    "company": company,
                                    "title": job_title,
                                    "location": location,
                                    "source_url": source_url,
                                    "jd_text": jd_text,
                                }
                            ],
                        },
                    )
                    set_flash("岗位已导入并完成评分")
                    st.rerun()
                except CareerClientError as exc:
                    st.error(f"导入失败：{exc}")
    with action2:
        st.markdown("#### 自动发现")
        st.caption("根据活动关键词搜索官方岗位页；BOSS 需连接浏览器会话。")
        if st.button("搜索官方岗位", type="secondary", use_container_width=True):
            try:
                client.discover(
                    campaign_id,
                    {"include_official_search": True, "manual_jobs": []},
                )
                set_flash("岗位发现已完成")
                st.rerun()
            except CareerClientError as exc:
                st.error(f"发现失败：{exc}")
        if st.button(
            "从 BOSS 采集岗位",
            type="primary",
            use_container_width=True,
            disabled=not browser.get("boss_logged_in"),
        ):
            try:
                client.discover(
                    campaign_id,
                    {
                        "include_official_search": False,
                        "include_boss": True,
                        "manual_jobs": [],
                    },
                )
                set_flash("BOSS 岗位已采集、去重并完成评分")
                st.rerun()
            except CareerClientError as exc:
                st.error(f"BOSS 采集失败：{exc}")
        if st.button("删除当前活动", use_container_width=True):
            try:
                client.delete_campaign(campaign_id)
                set_flash("求职活动已删除")
                st.rerun()
            except CareerClientError as exc:
                st.error(f"删除失败：{exc}")
    try:
        jobs = client.list_jobs(campaign_id)
    except CareerClientError as exc:
        st.error(f"读取岗位失败：{exc}")
        return
    if not jobs:
        render_empty("当前活动还没有岗位。")
        return
    selected_job_ids = []
    for item in jobs:
        job = item.get("job", item)
        evaluation = item.get("evaluation") or {}
        with st.container(border=True):
            top, select_col, delete_col = st.columns([6, 1.2, 1.2])
            with top:
                st.markdown(f"### {job.get('company')} · {job.get('title')}")
                st.caption(
                    f"{job.get('location') or '地点未提供'} · {job.get('platform')} · {job.get('status')}"
                )
            with select_col:
                if st.checkbox("批量定制", key=f"select-job-{job['id']}"):
                    selected_job_ids.append(job["id"])
            with delete_col:
                if st.button("删除", key=f"delete-job-{job['id']}"):
                    try:
                        client.delete_job(job["id"])
                        set_flash("岗位已删除")
                        st.rerun()
                    except CareerClientError as exc:
                        st.error(f"删除失败：{exc}")
            render_metric_row(
                [
                    ("匹配分", str(evaluation.get("overall_score", "-")), "0–100，仅用于排序"),
                    ("建议", evaluation.get("decision", "待评分"), "已应用硬筛选规则"),
                    ("已覆盖", str(len(evaluation.get("matched_keywords", []))), "岗位关键词"),
                    ("能力缺口", str(len(evaluation.get("missing_keywords", []))), "可统一补充"),
                ]
            )
    if selected_job_ids and st.button("为选中岗位批量生成 JD 匹配", type="primary"):
        try:
            client.create_batch(current_campaign["id"], selected_job_ids, "岗位池批量定制")
            set_flash("批量定制任务已创建")
            st.rerun()
        except CareerClientError as exc:
            st.error(f"创建失败：{exc}")


def render_resume_studio(
    profile_client: ProfileClient,
    match_client: MatchClient,
    career_client: CareerClient,
) -> None:
    match_tab, resume_tab = st.tabs(["六维 JD 匹配", "ATS 简历版本"])
    with match_tab:
        render_match_workspace(profile_client, match_client)
    with resume_tab:
        render_page_header(
            "Resume Studio",
            "从匹配结果生成 ATS 简历",
            "支持标准、学生紧凑和技术三种模板，并导出 Markdown、HTML、DOCX 与 PDF。",
        )
        try:
            jobs = [item.get("job", item) for item in career_client.list_jobs()]
            matches = [
                item
                for item in match_client.list_matches()
                if item["status"] in {"completed", "partial_success"}
            ]
            resumes = career_client.list_resumes()
        except (CareerClientError, MatchClientError) as exc:
            st.error(f"读取简历工作室失败：{exc}")
            return
        if jobs and matches:
            with st.form("resume-create-form"):
                job_id = st.selectbox(
                    "岗位",
                    [item["id"] for item in jobs],
                    format_func=lambda value: next(
                        f"{item['company']} · {item['title']}"
                        for item in jobs
                        if item["id"] == value
                    ),
                )
                match_id = st.selectbox(
                    "JD 匹配结果",
                    [item["id"] for item in matches],
                    format_func=lambda value: next(
                        item["title"] for item in matches if item["id"] == value
                    ),
                )
                template = st.selectbox(
                    "模板",
                    ["ats_standard", "student_compact", "technical"],
                    format_func=lambda value: {
                        "ats_standard": "ATS 标准单列",
                        "student_compact": "学生紧凑版",
                        "technical": "技术岗位版",
                    }[value],
                )
                if st.form_submit_button("生成简历版本", type="primary", use_container_width=True):
                    try:
                        career_client.create_resume(job_id, match_id, template)
                        set_flash("简历版本已生成并保存")
                        st.rerun()
                    except CareerClientError as exc:
                        st.error(f"生成失败：{exc}")
        for resume in resumes:
            with st.container(border=True):
                document = resume.get("document", {})
                st.markdown(
                    f"### {document.get('target_title') or '定制简历'} · V{resume.get('version')}"
                )
                audit = document.get("audit", {})
                render_metric_row(
                    [
                        ("ATS 分", str(audit.get("ats_score", "-")), "自动结构检查"),
                        ("关键词覆盖", f"{audit.get('keyword_coverage', 0):.0%}", "基于当前 JD"),
                        ("预计页数", str(audit.get("estimated_pages", "-")), "不缩小到不可读字体"),
                        ("模板", resume.get("template", "-"), "可生成新版本"),
                    ]
                )
                columns = st.columns(4)
                for column, file_format in zip(columns, ["md", "html", "docx", "pdf"], strict=True):
                    with column:
                        try:
                            data = career_client.download_resume(resume["id"], file_format)
                        except CareerClientError:
                            data = b""
                        st.download_button(
                            file_format.upper(),
                            data=data,
                            file_name=f"resume-v{resume['version']}.{file_format}",
                            disabled=not data,
                            use_container_width=True,
                            key=f"resume-download-{resume['id']}-{file_format}",
                        )
                materials = document.get("application_materials", {})
                with st.expander("查看 Cover Letter、BOSS 招呼语和表单答案"):
                    st.markdown("#### Cover Letter")
                    st.write(materials.get("cover_letter", ""))
                    st.markdown("#### BOSS 招呼语")
                    st.write(materials.get("boss_greeting", ""))
                    st.markdown("#### 表单答案")
                    st.json(materials.get("form_answers", {}))


def render_application_center(client: CareerClient) -> None:
    render_page_header(
        "Application Center",
        "预填、检查，再由你逐岗位确认提交",
        "登录、验证码、2FA、敏感字段和未知控件会进入待处理队列，不会绕过平台限制。",
    )
    try:
        browser = client.browser_status()
        resumes = client.list_resumes()
        applications = client.list_applications()
    except CareerClientError as exc:
        st.error(f"读取投递中心失败：{exc}")
        return
    with st.container(border=True):
        if browser.get("boss_logged_in"):
            st.success("BOSS 直聘已连接。BOSS 岗位会在确认后发送定制招呼语。")
        elif browser.get("connected"):
            st.warning("Chrome 已连接，但尚未检测到 BOSS 登录状态。")
        else:
            st.warning("投递浏览器未连接。请先运行以下命令并登录 BOSS 直聘。")
            st.code("sh scripts/start_boss_chrome.sh", language="bash")
        st.caption("BOSS 不使用传统申请表：确认投递代表发送招呼语；简历附件不会自动发送。")
    if resumes:
        with st.form("application-create-form"):
            resume_id = st.selectbox(
                "选择简历版本",
                [item["id"] for item in resumes],
                format_func=lambda value: next(
                    f"{item['document'].get('target_title', '岗位')} · V{item['version']}"
                    for item in resumes
                    if item["id"] == value
                ),
            )
            selected_resume = next(item for item in resumes if item["id"] == resume_id)
            st.caption("将打开岗位页面并安全预填，但不会自动点击最终提交。")
            if st.form_submit_button("创建投递预览", type="primary", use_container_width=True):
                try:
                    client.create_application(selected_resume["job_id"], resume_id)
                    set_flash("投递任务已创建，正在准备预览")
                    st.rerun()
                except CareerClientError as exc:
                    st.error(f"创建失败：{exc}")
    if not applications:
        render_empty("还没有投递任务。先在简历工作室生成岗位简历。")
        return
    for application in applications:
        with st.container(border=True):
            preview = application.get("preview") or {}
            st.markdown(
                f"### {preview.get('company', '岗位申请')} · {preview.get('title', application.get('platform'))}"
            )
            st.caption(f"状态：{application.get('status')} · 阶段：{application.get('stage')}")
            if preview:
                st.write(
                    "选中经历：", "、".join(preview.get("selected_experiences", [])) or "未列出"
                )
                with st.expander("查看提交前字段"):
                    if preview.get("message_preview"):
                        st.markdown("#### 即将发送的 BOSS 招呼语")
                        st.info(preview["message_preview"])
                    if preview.get("delivery_note"):
                        st.caption(preview["delivery_note"])
                    st.dataframe(preview.get("fields", []), use_container_width=True)
                    for warning in preview.get("warnings", []):
                        st.warning(warning)
            buttons = st.columns(4)
            with buttons[0]:
                if st.button(
                    "确认提交",
                    key=f"confirm-application-{application['id']}",
                    disabled=application.get("status") != "awaiting_confirmation",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        client.confirm_application(
                            application["id"], preview.get("preview_hash", "")
                        )
                        set_flash("已确认，Agent 正在重新校验并提交")
                        st.rerun()
                    except CareerClientError as exc:
                        st.error(f"确认失败：{exc}")
            with buttons[1]:
                if st.button(
                    "继续处理",
                    key=f"resume-application-{application['id']}",
                    use_container_width=True,
                ):
                    try:
                        client.resume_application(application["id"])
                        set_flash("投递任务已继续")
                        st.rerun()
                    except CareerClientError as exc:
                        st.error(f"继续失败：{exc}")
            with buttons[2]:
                if st.button(
                    "取消", key=f"cancel-application-{application['id']}", use_container_width=True
                ):
                    try:
                        client.cancel_application(application["id"])
                        set_flash("投递任务已取消")
                        st.rerun()
                    except CareerClientError as exc:
                        st.error(f"取消失败：{exc}")
            with buttons[3]:
                if st.button(
                    "删除", key=f"delete-application-{application['id']}", use_container_width=True
                ):
                    try:
                        client.delete_application(application["id"])
                        set_flash("投递任务已删除")
                        st.rerun()
                    except CareerClientError as exc:
                        st.error(f"删除失败：{exc}")


def render_interview_tracker(client: CareerClient) -> None:
    render_page_header(
        "Interview & Tracking",
        "查看求职漏斗并准备面试",
        "面试准备包只使用当前岗位、已生成简历和证据支持的经历素材。",
    )
    try:
        dashboard = client.dashboard()
        resumes = client.list_resumes()
    except CareerClientError as exc:
        st.error(f"读取跟进面板失败：{exc}")
        return
    render_metric_row(
        [
            ("岗位池", str(dashboard.get("total_jobs", 0)), "已导入和发现"),
            ("推荐投递", str(dashboard.get("recommended_jobs", 0)), "通过规则与评分"),
            ("待确认", str(dashboard.get("awaiting_confirmation", 0)), "必须人工确认"),
            ("已提交", str(dashboard.get("submitted", 0)), "有明确成功证据"),
        ]
    )
    render_metric_row(
        [
            ("面试中", str(dashboard.get("interviews", 0)), "岗位状态"),
            ("Offer", str(dashboard.get("offers", 0)), "岗位状态"),
            ("拒绝", str(dashboard.get("rejected", 0)), "岗位状态"),
            ("阻塞", str(dashboard.get("blocked", 0)), "登录、验证码或未知字段"),
        ]
    )
    blocker_col, follow_col = st.columns(2)
    with blocker_col:
        render_section_heading("待处理阻塞", "完成登录、验证码或敏感信息确认后继续。")
        for blocker in dashboard.get("open_blockers", []):
            st.warning(f"{blocker.get('message')}\n\n{blocker.get('next_action', '')}")
    with follow_col:
        render_section_heading("近期跟进", "集中查看下一步行动。")
        for event in dashboard.get("upcoming_follow_ups", []):
            st.info(f"{event.get('title')} · {format_time(event.get('scheduled_at'))}")
    if resumes:
        render_section_heading("生成面试准备包", "选择岗位简历生成 STAR 故事、高频问题和反问清单。")
        resume_id = st.selectbox(
            "简历版本",
            [item["id"] for item in resumes],
            format_func=lambda value: next(
                f"{item['document'].get('target_title', '岗位')} · V{item['version']}"
                for item in resumes
                if item["id"] == value
            ),
            key="interview-resume-selector",
        )
        selected = next(item for item in resumes if item["id"] == resume_id)
        if st.button("生成面试准备包", type="primary"):
            try:
                kit = client.create_interview(selected["job_id"], resume_id)
                st.session_state["latest_interview_kit"] = kit
                set_flash("面试准备包已生成")
                st.rerun()
            except CareerClientError as exc:
                st.error(f"生成失败：{exc}")
    kit = st.session_state.get("latest_interview_kit")
    if kit:
        with st.container(border=True):
            st.markdown("### 岗位理解")
            st.write(kit.get("role_summary"))
            st.markdown("### 60 秒自我介绍")
            st.write(kit.get("self_introduction"))
            st.markdown("### 高频问题")
            for question in kit.get("likely_questions", []):
                with st.expander(question.get("question", "面试问题")):
                    for outline in question.get("answer_outline", []):
                        st.write("-", outline)


def split_values(value: str) -> list[str]:
    normalized = value.replace("，", ",").replace("\n", ",")
    return list(dict.fromkeys(item.strip() for item in normalized.split(",") if item.strip()))


def render_sidebar_stats(total: int, completed: int, active: int) -> None:
    st.sidebar.markdown(
        f"""
        <div class="sidebar-stats">
            <div class="sidebar-stat"><strong>{total}</strong><span>全部任务</span></div>
            <div class="sidebar-stat"><strong>{completed}</strong><span>已完成</span></div>
            <div class="sidebar-stat"><strong>{active}</strong><span>处理中</span></div>
            <div class="sidebar-stat"><strong>{max(total - completed - active, 0)}</strong><span>待处理</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload(client: ProfileClient) -> None:
    with st.container(border=True):
        with st.form("upload-form"):
            title = st.text_input("任务名称", placeholder="例如：2026 春招完整画像")
            files = st.file_uploader(
                "上传资料",
                type=["doc", "docx", "pdf", "md", "ppt", "pptx"],
                accept_multiple_files=True,
                help="最多 20 个文件，单文件默认不超过 50 MB。",
            )
            spacer_col, action_col = st.columns([2, 1], vertical_alignment="bottom")
            with spacer_col:
                st.empty()
            with action_col:
                submitted = st.form_submit_button(
                    "开始整理资料",
                    type="primary",
                    use_container_width=True,
                )
        if submitted:
            if not files:
                st.warning("请先上传至少一份资料。")
                return
            fingerprint = profile_submission_fingerprint(title, files)
            if is_duplicate_submission("profile", fingerprint):
                st.toast("该画像任务刚刚已保存，请勿重复点击。", icon="ℹ️")
                return
            try:
                response = client.create_profile(
                    files,
                    title=title,
                )
                remember_submission("profile", fingerprint)
                queue_selector(PROFILE_SELECTOR_KEY, response["task_id"])
                set_flash("画像任务已保存并加入处理队列。")
                st.rerun()
            except ProfileClientError as exc:
                st.error(str(exc))


def render_task(client: ProfileClient, task_id: str) -> None:
    try:
        task = client.get_task(task_id)
    except ProfileClientError as exc:
        st.error(str(exc))
        return
    render_task_banner(task, "资料画像任务")
    control_col, progress_col = st.columns([1, 4], vertical_alignment="center")
    with control_col:
        if st.button("↻ 刷新状态", use_container_width=True, key=f"refresh-profile-{task_id}"):
            st.rerun()
    with progress_col:
        st.progress(
            task["progress"] / 100, text=f"{stage_label(task['stage'])} · {task['progress']}%"
        )
    if task.get("error") and "未解决冲突" not in task["error"]:
        st.warning(task["error"])
    render_profile_pool(task)

    status = task["status"]
    if status in {"completed", "partial_success"}:
        render_result(client, task_id)
    elif status in {"failed", "failed_retryable"}:
        with st.container(border=True):
            st.markdown("#### 任务未完成")
            st.caption("原始资料仍然保留，可以直接重新执行处理流程。")
            if st.button("重新尝试", type="primary", key=f"retry-profile-{task_id}"):
                client.retry(task_id)
                set_flash("重试请求已保存，任务已重新加入队列。")
                st.rerun()

    render_danger_zone(
        "删除画像任务",
        "将立即取消后台处理，并删除原件、解析数据、画像结果及关联的 JD 匹配任务。",
        lambda: delete_profile_task(client, task_id),
        f"delete-profile-{task_id}",
    )


def render_profile_pool(task: dict) -> None:
    documents = task.get("documents", [])
    st.markdown("### 画像池")
    st.caption(f"当前任务共保存 {len(documents)} 份资料，文件状态会随解析进度更新。")
    if not documents:
        render_empty("当前任务暂时没有可显示的资料文件。")
        return
    rows = [
        {
            "文件名": document.get("original_name", ""),
            "格式": (document.get("extension") or "").replace(".", "").upper(),
            "大小": format_file_size(document.get("size_bytes", 0)),
            "状态": document_status_label(document.get("status", "")),
            "错误": document.get("error") or "",
        }
        for document in documents
    ]
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "文件名": st.column_config.TextColumn(width="large"),
            "格式": st.column_config.TextColumn(width="small"),
            "大小": st.column_config.TextColumn(width="small"),
            "状态": st.column_config.TextColumn(width="small"),
            "错误": st.column_config.TextColumn(width="medium"),
        },
    )


def render_result(client: ProfileClient, task_id: str) -> None:
    result = client.get_result(task_id)
    render_section_heading(
        "六维画像", "每个维度均可单独下载 Markdown，并保留事实、置信度和证据来源。"
    )
    render_metric_row(
        [
            ("引用覆盖率", f"{result['audit']['citation_coverage']:.0%}", "事实均尽量关联原始证据"),
            ("素材聚合", "已开启", "不同岗位表达作为互补素材保留"),
            ("生成模型", result.get("model") or "规则回退", "当前画像生成引擎"),
            ("生成时间", format_time(result.get("generated_at"), short=True), "最近一次结果版本"),
        ]
    )
    tabs = st.tabs([label for _, label, _ in DIMENSIONS])
    for tab, (key, label, description) in zip(tabs, DIMENSIONS, strict=True):
        with tab:
            render_dimension_header(label, description, result[key].get("status"))
            render_profile_dimension(key, result[key])
            st.download_button(
                f"下载 {label} Markdown",
                data=client.download_section(task_id, key),
                file_name=f"{key}.md",
                mime="text/markdown",
                key=f"profile-section:{task_id}:{key}",
            )
    render_export_center(
        [
            ("Markdown", client.download(task_id, "md"), "profile.md", "text/markdown"),
            (
                "DOCX",
                client.download(task_id, "docx"),
                "profile.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "JSON",
                json.dumps(result, ensure_ascii=False, indent=2),
                "profile.json",
                "application/json",
            ),
        ],
        "导出完整画像",
    )
    if st.button("根据当前事实重新生成", key=f"regenerate-profile-{task_id}"):
        client.regenerate(task_id)
        set_flash("重新生成请求已保存并加入队列。")
        st.rerun()


def render_profile_dimension(section_name: str, section: dict) -> None:
    overview = section.get("overview") or "资料未提供足够信息。"
    st.markdown(f'<div class="soft-panel">{html.escape(overview)}</div>', unsafe_allow_html=True)
    if section_name == "personal_introduction":
        render_claim_group("核心优势", section.get("core_strengths", []))
        render_claim_group("工作特点", section.get("work_characteristics", []))
        render_claim_group("职业方向", section.get("career_direction", []))
        render_chips(section.get("keywords", []))
    elif section_name == "professional_introduction":
        render_claim_group("知识结构", section.get("knowledge_domains", []))
        render_claim_group("专业技能", section.get("skills", []))
        render_claim_group("研究兴趣", section.get("research_interests", []))
        render_claim_group("证书", section.get("certifications", []))
        render_chips(section.get("tools_and_technologies", []), "cyan")
    elif section_name == "education_history":
        render_education_entries(section.get("entries", []))
    else:
        render_experience_entries(section.get("entries", []))


def render_claim_group(title: str, claims: list[dict]) -> None:
    if not claims:
        return
    st.markdown(f"##### {title}")
    for claim in claims:
        with st.container(border=True):
            text_col, score_col = st.columns([5, 1], vertical_alignment="top")
            text_col.markdown(claim["content"])
            score_col.metric("置信度", f"{claim['confidence']:.0%}")
            text_col.caption(
                f"{'事实' if claim['basis_type'] == 'fact' else '合理推断'} · {claim.get('rationale') or '基于资料归纳'}"
            )
            render_evidence(claim.get("evidence_refs", []), "查看证据")


def render_experience_entries(entries: list[dict]) -> None:
    if not entries:
        render_empty("该维度暂未识别到经历。")
        return
    for index, entry in enumerate(entries):
        with st.expander(entry["name"], expanded=index == 0):
            meta = [
                entry.get("organization") or "单位未提供",
                entry.get("period") or "时间未提供",
                entry.get("role") or "角色未提供",
            ]
            st.caption("  ·  ".join(meta))
            st.markdown(entry.get("summary") or "")
            render_chips(entry.get("technologies", []), "cyan")
            for title, claims in (
                ("行动与职责", entry.get("details", [])),
                ("成果与影响", entry.get("outcomes", [])),
            ):
                if claims:
                    st.markdown(f"**{title}**")
                    for claim in claims:
                        st.markdown(f"- {claim['content']}")
            render_evidence(entry.get("evidence_refs", []), "来源证据")


def render_education_entries(entries: list[dict]) -> None:
    if not entries:
        render_empty("资料中暂未识别到学校履历。")
        return
    for index, entry in enumerate(entries):
        with st.expander(entry["institution"], expanded=index == 0):
            st.caption(
                "  ·  ".join(
                    [
                        entry.get("degree") or "学历未提供",
                        entry.get("major") or "专业未提供",
                        entry.get("period") or "时间未提供",
                    ]
                )
            )
            st.markdown(entry.get("overview") or "")
            if entry.get("courses"):
                st.markdown("**相关课程**")
                render_chips(entry["courses"], "gray")
            for title, claims in (
                ("荣誉", entry.get("honors", [])),
                ("校园经历", entry.get("campus_experiences", [])),
            ):
                if claims:
                    st.markdown(f"**{title}**")
                    for claim in claims:
                        st.markdown(f"- {claim['content']}")
            render_evidence(entry.get("evidence_refs", []), "来源证据")


def render_match_create(client: MatchClient, profiles: list[dict], matches: list[dict]) -> None:
    render_page_header(
        "JD Tailoring",
        "用岗位能力重新组织你的最佳材料",
        "Agent 会联网研究同类岗位，识别核心能力，再从六份画像文档中挑选最相关的事实生成投递文案。",
    )
    render_metric_row(
        [
            ("可用画像", str(len(profiles)), "仅展示已完成画像"),
            ("历史匹配", str(len(matches)), "支持版本恢复与重新生成"),
            ("联网研究", "开启", "岗位说明、能力与常见工具"),
            ("事实边界", "严格", "强化表达，不新增硬事实"),
        ]
    )
    render_section_heading("创建岗位匹配", "粘贴完整 JD 能获得更准确的岗位研究与六维匹配。")
    if not profiles:
        render_empty("请先完成至少一个资料画像任务，再创建 JD 匹配。")
        return
    profile_labels = {item["id"]: item["title"] for item in profiles}
    with st.container(border=True):
        st.markdown("#### 新建 JD 匹配")
        with st.form("match-create-form"):
            left, right = st.columns(2)
            with left:
                profile_task_id = st.selectbox(
                    "选择用户画像",
                    options=list(profile_labels),
                    format_func=lambda value: profile_labels[value],
                )
            with right:
                title = st.text_input("匹配任务名称", placeholder="例如：AI 产品经理 · A 公司")
            jd_text = st.text_area(
                "岗位 JD",
                height=300,
                placeholder="请粘贴岗位职责、任职要求、加分项和学历要求……",
            )
            submitted = st.form_submit_button(
                "开始岗位研究与匹配",
                type="primary",
                use_container_width=True,
            )
        if submitted:
            fingerprint = match_submission_fingerprint(profile_task_id, title, jd_text)
            if is_duplicate_submission("match", fingerprint):
                st.toast("该岗位匹配任务刚刚已保存，请勿重复点击。", icon="ℹ️")
                return
            try:
                response = client.create_match(profile_task_id, jd_text, title)
                remember_submission("match", fingerprint)
                queue_selector(MATCH_SELECTOR_KEY, response["match_id"])
                set_flash("岗位匹配任务已保存并加入处理队列。")
                st.rerun()
            except MatchClientError as exc:
                st.error(str(exc))


def render_match_task(client: MatchClient, match_id: str) -> None:
    try:
        task = client.get_task(match_id)
    except MatchClientError as exc:
        st.error(str(exc))
        return
    render_page_header(
        "Match Task",
        task["title"],
        "查看岗位研究、匹配评分和针对 JD 优化后的六维简历文案。",
    )
    render_task_banner(task, "JD 岗位匹配")
    refresh_col, progress_col = st.columns([1, 4], vertical_alignment="center")
    with refresh_col:
        if st.button("↻ 刷新状态", use_container_width=True, key=f"refresh-match-{match_id}"):
            st.rerun()
    with progress_col:
        st.progress(
            task["progress"] / 100, text=f"{stage_label(task['stage'])} · {task['progress']}%"
        )
    with st.expander("查看原始岗位 JD"):
        st.code(task["jd_text"], language=None, wrap_lines=True)
    if task.get("error") and "未解决冲突" not in task["error"]:
        st.warning(task["error"])
    if task["status"] in {"completed", "partial_success"}:
        render_match_result(client, match_id)
    elif task["status"] in {"failed", "failed_retryable"}:
        with st.container(border=True):
            st.markdown("#### 匹配任务未完成")
            if st.button("重试 JD 匹配", type="primary", key=f"retry-match-{match_id}"):
                client.retry(match_id)
                set_flash("重试请求已保存，岗位匹配已重新加入队列。")
                st.rerun()
    render_danger_zone(
        "删除岗位匹配",
        "将立即取消后台处理，并删除该任务的全部版本和导出文件，不影响原始画像。",
        lambda: delete_match_task(client, match_id),
        f"delete-match-{match_id}",
    )


def render_match_result(client: MatchClient, match_id: str) -> None:
    try:
        result = client.get_result(match_id)
        versions = client.list_versions(match_id)
    except MatchClientError as exc:
        st.error(str(exc))
        return
    research = result["job_research"]
    render_section_heading("匹配概览", "分数用于材料排序和解释，不代表招聘录用概率。")
    render_metric_row(
        [
            ("总体匹配度", f"{result['overall_score']:.1f}", "岗位要求加权评分"),
            ("关键词覆盖", f"{result['keyword_coverage']['ratio']:.0%}", "画像事实覆盖岗位关键词"),
            ("研究来源", str(len(research["sources"])), f"联网状态：{research['status']}"),
            ("当前版本", f"v{result['version']}", result.get("model") or "规则回退"),
        ]
    )
    render_dimension_scores(result["dimension_scores"])
    render_role_research(research)
    render_strengths_and_gaps(result["strengths"], result["gaps"])
    render_keyword_coverage(result["keyword_coverage"])

    render_section_heading("六维投递文案", "内容可编辑；保存时会重新执行硬事实与技能审计。")
    updates: list[dict] = []
    tabs = st.tabs([label for _, label, _ in DIMENSIONS])
    for tab, (section_name, label, description) in zip(tabs, DIMENSIONS, strict=True):
        with tab:
            section = result[section_name]
            render_dimension_header(label, description, section.get("status"))
            source_document = result.get("section_documents", {}).get(section_name)
            if source_document:
                with st.expander(f"查看本次岗位画像母版 · {label}"):
                    st.markdown(source_document)
                    st.download_button(
                        f"下载 画像母版_{label}.md",
                        data=source_document,
                        file_name=f"画像母版_{label}.md",
                        mime="text/markdown",
                        key=f"match-source:{match_id}:v{result['version']}:{section_name}",
                    )
            render_match_section_metadata(section)
            for field_label, unit in editable_units(section):
                value = st.text_area(
                    field_label,
                    value=unit["content"],
                    height=120 if "概述" in field_label else 90,
                    key=f"match:{match_id}:v{result['version']}:{unit['id']}",
                )
                if value.strip() != unit["content"]:
                    updates.append({"unit_id": unit["id"], "content": value.strip()})
                render_evidence(unit.get("evidence_refs", []), f"{field_label} · 证据")
    action_col, info_col = st.columns([1, 3], vertical_alignment="center")
    if action_col.button(
        "保存为新版本",
        type="primary",
        disabled=not updates,
        use_container_width=True,
    ):
        try:
            client.update_draft(match_id, result["version"], updates)
            set_flash("文案已保存为新版本。")
            st.rerun()
        except MatchClientError as exc:
            st.error(str(exc))
    info_col.caption("未修改内容时按钮不可用；任何新增数字、单位、奖项或无依据技能都会被拒绝。")

    render_version_center(client, match_id, result, versions)
    render_export_center(
        [
            ("Markdown", client.download(match_id, "md"), "jd-match.md", "text/markdown"),
            (
                "DOCX",
                client.download(match_id, "docx"),
                "jd-match.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("JSON", client.download(match_id, "json"), "jd-match.json", "application/json"),
        ],
        "导出当前版本",
    )
    if st.button("重新研究岗位并生成文案", key=f"regenerate-match-{match_id}"):
        client.regenerate(match_id)
        set_flash("重新生成请求已保存并加入队列。")
        st.rerun()


def render_dimension_scores(scores: dict) -> None:
    render_section_heading("六维匹配分布", "快速判断哪些材料最适合当前岗位。")
    labels = {key: label for key, label, _ in DIMENSIONS}
    items = list(scores.items())
    for start in range(0, len(items), 3):
        columns = st.columns(3)
        for column, (key, value) in zip(columns, items[start : start + 3], strict=False):
            with column:
                with st.container(border=True):
                    score = value["score"]
                    label = labels.get(key, key)
                    label_col, score_col = st.columns([3, 1])
                    label_col.markdown(f"**{label}**")
                    score_col.markdown(f"**{score:.0f}**")
                    st.progress(score / 100)
                    st.caption(
                        f"匹配 {len(value['matched_requirement_ids'])} 项 · "
                        f"缺失 {len(value['missing_requirement_ids'])} 项"
                    )


def render_role_research(research: dict) -> None:
    render_section_heading("岗位研究", "联网研究只描述岗位，不会被当作候选人已经具备的事实。")
    left, right = st.columns([1.25, 1])
    with left:
        with st.container(border=True):
            st.markdown("#### 这是一个什么岗位")
            st.markdown(research["role_summary"])
            if research["typical_responsibilities"]:
                st.markdown("**常见职责**")
                for item in research["typical_responsibilities"]:
                    st.markdown(f"- {item}")
    with right:
        with st.container(border=True):
            st.markdown("#### 岗位能力地图")
            st.caption("核心能力")
            render_chips(research["core_capabilities"])
            st.caption("常见工具与技能")
            render_chips(research["common_tools"], "cyan")
    with st.expander(f"联网研究来源 · {len(research['sources'])} 条 · {research['status']}"):
        if research["sources"]:
            for source in research["sources"]:
                st.markdown(f"**[{source['title']}]({source['url']})**")
                if source.get("snippet"):
                    st.caption(source["snippet"])
                st.divider()
        else:
            st.caption("未获取到联网搜索来源，本次岗位说明使用 JD 回退生成。")


def render_strengths_and_gaps(strengths: list[str], gaps: list[str]) -> None:
    render_section_heading("优势与缺口", "优势来自画像事实；缺口只用于提醒，不会被补写进简历。")
    left, right = st.columns(2)
    with left:
        items = (
            "".join(f"<li>{html.escape(item)}</li>" for item in strengths)
            or "<li>暂无强匹配项</li>"
        )
        st.markdown(
            f'<div class="insight-card good"><div class="insight-title">✓ 核心优势</div><ul>{items}</ul></div>',
            unsafe_allow_html=True,
        )
    with right:
        items = "".join(f"<li>{html.escape(item)}</li>" for item in gaps) or "<li>暂无明显缺口</li>"
        st.markdown(
            f'<div class="insight-card gap"><div class="insight-title">△ 能力缺口</div><ul>{items}</ul></div>',
            unsafe_allow_html=True,
        )


def render_keyword_coverage(coverage: dict) -> None:
    with st.expander("关键词覆盖详情"):
        st.markdown("**已覆盖关键词**")
        render_chips(coverage["matched"], "cyan")
        st.markdown("**尚未覆盖关键词**")
        render_chips(coverage["missing"], "gray")


def render_match_section_metadata(section: dict) -> None:
    entries = section.get("entries", [])
    if not entries:
        return
    for entry in entries:
        name = entry.get("name") or entry.get("institution")
        meta = [
            entry.get("organization") or entry.get("degree"),
            entry.get("role") or entry.get("major"),
            entry.get("period"),
        ]
        st.caption(f"{name} · {' · '.join(item for item in meta if item)}")


def editable_units(section: dict) -> list[tuple[str, dict]]:
    output = [("章节概述", section["overview"])]
    if "bullets" in section and "entries" not in section:
        output.extend((f"要点 {index + 1}", unit) for index, unit in enumerate(section["bullets"]))
        return output
    for entry_index, entry in enumerate(section.get("entries", [])):
        name = entry.get("name") or entry.get("institution") or f"经历 {entry_index + 1}"
        output.append((f"{name} · 概述", entry["tailored_summary"]))
        output.extend(
            (f"{name} · 要点 {index + 1}", unit)
            for index, unit in enumerate(entry.get("bullets", []))
        )
    return output


def render_version_center(
    client: MatchClient, match_id: str, result: dict, versions: list[dict]
) -> None:
    if not versions:
        return
    render_section_heading("版本管理", "编辑、恢复和重新生成都会创建完整版本。")
    with st.container(border=True):
        version_map = {
            item[
                "version"
            ]: f"v{item['version']} · {version_source_label(item['source'])} · {format_time(item['created_at'])}"
            for item in versions
        }
        select_col, action_col = st.columns([3, 1], vertical_alignment="bottom")
        selected_version = select_col.selectbox(
            "历史版本",
            options=list(version_map),
            format_func=lambda value: version_map[value],
        )
        if action_col.button(
            "恢复所选版本",
            disabled=selected_version == result["version"],
            use_container_width=True,
        ):
            client.restore(match_id, selected_version)
            set_flash(f"历史版本 v{selected_version} 已恢复并保存。")
            st.rerun()


def render_export_center(items: list[tuple[str, bytes | str, str, str]], title: str) -> None:
    render_section_heading(title, "所有导出文件均对应当前页面展示的结果。")
    columns = st.columns(len(items))
    for column, (label, data, filename, mime) in zip(columns, items, strict=True):
        column.download_button(
            f"↓ 下载 {label}",
            data=data,
            file_name=filename,
            mime=mime,
            use_container_width=True,
        )


def render_page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="page-hero">
            <div class="eyebrow">{html.escape(eyebrow)}</div>
            <div class="hero-title">{html.escape(title)}</div>
            <div class="hero-sub">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_row(items: list[tuple[str, str, str]]) -> None:
    columns = st.columns(len(items))
    for column, (label, value, note) in zip(columns, items, strict=True):
        with column:
            render_metric_card(label, value, note)


def render_metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(label)}</div>
            <div class="metric-value">{html.escape(value)}</div>
            <div class="metric-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="section-heading"><h3>{html.escape(title)}</h3><p>{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def render_task_banner(task: dict, kind: str) -> None:
    label, icon, tone = status_meta(task["status"])
    st.markdown(
        f"""
        <div class="task-banner">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;">
                <div>
                    <div class="task-title">{html.escape(task["title"])}</div>
                    <div class="task-meta">{html.escape(kind)} · 创建于 {html.escape(format_time(task.get("created_at")))}</div>
                </div>
                <span class="status-pill status-{tone}">{icon} {label}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dimension_header(label: str, description: str, status: str | None) -> None:
    tone = "success" if status == "complete" else "warning"
    status_label = "资料充分" if status == "complete" else "资料不足"
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin:.95rem 0 .75rem;">
            <div><strong>{html.escape(label)}</strong><div style="font-size:.72rem;color:#7a8394;margin-top:.15rem;">{html.escape(description)}</div></div>
            <span class="status-pill status-{tone}">{status_label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chips(items: list[str], tone: str = "") -> None:
    if not items:
        return
    chips = "".join(f'<span class="chip {tone}">{html.escape(str(item))}</span>' for item in items)
    st.markdown(f'<div class="chip-wrap">{chips}</div>', unsafe_allow_html=True)


def render_evidence(evidence_refs: list[dict], title: str) -> None:
    if not evidence_refs:
        return
    with st.expander(f"{title} · {len(evidence_refs)} 条"):
        for item in evidence_refs:
            locator = item.get("page") or item.get("slide") or item.get("paragraph")
            position = f"#{locator}" if locator else ""
            st.markdown(f"**{item.get('file_name', '资料')}{position}**")
            st.caption(item.get("quote") or "")


def render_empty(message: str) -> None:
    st.markdown(f'<div class="empty-hint">{html.escape(message)}</div>', unsafe_allow_html=True)


def render_danger_zone(title: str, description: str, action, key: str) -> None:
    with st.expander("危险操作"):
        text_col, action_col = st.columns([4, 1], vertical_alignment="center")
        text_col.markdown(f"**{title}**")
        text_col.caption(description)
        if action_col.button("删除任务", key=key, use_container_width=True):
            action()


def render_flash() -> None:
    payload = st.session_state.pop("_flash_message", None)
    if payload:
        st.toast(payload["message"], icon=payload["icon"])


def set_flash(message: str, icon: str = "✅") -> None:
    st.session_state["_flash_message"] = {"message": message, "icon": icon}


def prepare_selector(selector_key: str, options: list[str]) -> None:
    pending_key = f"_{selector_key}_next"
    if pending_key in st.session_state:
        selected = st.session_state.pop(pending_key)
        st.session_state[selector_key] = selected if selected in options else ""
    elif st.session_state.get(selector_key, "") not in options:
        st.session_state[selector_key] = ""


def queue_selector(selector_key: str, selected: str) -> None:
    st.session_state[f"_{selector_key}_next"] = selected


def delete_profile_task(client: ProfileClient, task_id: str) -> None:
    try:
        client.delete(task_id)
    except ProfileClientError as exc:
        st.error(str(exc))
        return
    queue_selector(PROFILE_SELECTOR_KEY, "")
    set_flash("画像任务已删除；如任务正在处理，后台执行也已取消。", "🗑️")
    st.rerun()


def delete_match_task(client: MatchClient, match_id: str) -> None:
    try:
        client.delete(match_id)
    except MatchClientError as exc:
        st.error(str(exc))
        return
    queue_selector(MATCH_SELECTOR_KEY, "")
    set_flash("岗位匹配已删除；如任务正在处理，后台执行也已取消。", "🗑️")
    st.rerun()


def profile_submission_fingerprint(title: str, files) -> str:
    digest = hashlib.sha256()
    update_digest(digest, title.strip(), "auto")
    for file in files:
        update_digest(digest, file.name, str(getattr(file, "size", "")))
        digest.update(file.getbuffer())
    return digest.hexdigest()


def match_submission_fingerprint(profile_task_id: str, title: str, jd_text: str) -> str:
    digest = hashlib.sha256()
    update_digest(digest, profile_task_id, title.strip(), jd_text.strip())
    return digest.hexdigest()


def update_digest(digest, *values: str) -> None:
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")


def is_duplicate_submission(kind: str, fingerprint: str) -> bool:
    previous = st.session_state.get(f"_{kind}_submission")
    return bool(
        previous
        and previous["fingerprint"] == fingerprint
        and time.time() - previous["created_at"] < SUBMISSION_DEDUP_SECONDS
    )


def remember_submission(kind: str, fingerprint: str) -> None:
    st.session_state[f"_{kind}_submission"] = {
        "fingerprint": fingerprint,
        "created_at": time.time(),
    }


def task_label(task: dict) -> str:
    label, icon, _ = status_meta(task["status"])
    short_id = task["id"][:6]
    return (
        f"{icon} {task['title']} #{short_id} · {label} · "
        f"{format_time(task.get('created_at'), short=True)}"
    )


def status_meta(status: str) -> tuple[str, str, str]:
    return STATUS_META.get(status, (status, "•", "neutral"))


def stage_label(stage: str) -> str:
    labels = {
        "queued": "等待处理",
        "parsing_documents": "解析文档",
        "extracting_facts": "提取事实",
        "awaiting_review": "等待事实核对",
        "generating_profile": "生成六维画像",
        "regenerating_profile": "重新生成画像",
        "analyzing_jd": "分析岗位信息",
        "matching": "匹配岗位能力",
        "generating": "生成投递文案",
        "auditing": "执行真实性审计",
        "completed": "处理完成",
        "failed": "处理失败",
    }
    return labels.get(stage, stage.replace("_", " "))


def document_status_label(status: str) -> str:
    return {
        "stored": "等待解析",
        "parsing": "解析中",
        "parsed": "已解析",
        "failed": "失败",
    }.get(status, status or "未知")


def format_file_size(size_bytes: int) -> str:
    size = float(size_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return "0 B"


def format_time(value: str | None, short: bool = False) -> str:
    if not value:
        return "未提供"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%m-%d %H:%M" if short else "%Y-%m-%d %H:%M")
    except ValueError:
        return value[:16].replace("T", " ")


def version_source_label(source: str) -> str:
    return {
        "generated": "首次生成",
        "user_edit": "用户编辑",
        "regenerated": "重新生成",
        "restored": "版本恢复",
    }.get(source, source)


if __name__ == "__main__":
    main()
