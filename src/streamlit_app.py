import os

import streamlit as st

from client import MatchClient, MatchClientError, ProfileClient, ProfileClientError

st.set_page_config(page_title="六维画像 Agent", page_icon="🧭", layout="wide")


@st.cache_resource
def get_profile_client() -> ProfileClient:
    return ProfileClient(os.getenv("AGENT_URL", "http://127.0.0.1:8080"))


@st.cache_resource
def get_match_client() -> MatchClient:
    return MatchClient(os.getenv("AGENT_URL", "http://127.0.0.1:8080"))


def main() -> None:
    st.title("🧭 用户资料六维画像 Agent")
    workspace = st.sidebar.radio("工作区", ["资料画像", "JD 岗位匹配"])
    if workspace == "资料画像":
        render_profile_workspace(get_profile_client())
    else:
        render_match_workspace(get_profile_client(), get_match_client())


def render_profile_workspace(client: ProfileClient) -> None:
    st.caption("上传 Word、PDF、Markdown 或 PowerPoint，生成带证据和置信度的详细画像。")
    try:
        tasks = client.list_profiles()
    except ProfileClientError as exc:
        st.error(f"无法连接 Agent 服务：{exc}")
        return

    labels = {task["id"]: f"{task['title']} · {task['status']}" for task in tasks}
    selected = st.sidebar.selectbox(
        "历史任务",
        options=["", *list(labels)],
        format_func=lambda value: "新建任务" if not value else labels[value],
    )
    if not selected:
        render_upload(client)
    else:
        render_task(client, selected)


def render_match_workspace(profile_client: ProfileClient, match_client: MatchClient) -> None:
    st.caption("选择历史画像并粘贴岗位 JD，生成匹配分析和六维简历投递文案。")
    try:
        profiles = [
            task
            for task in profile_client.list_profiles()
            if task["status"] in {"completed", "partial_success"}
        ]
        matches = match_client.list_matches()
    except (ProfileClientError, MatchClientError) as exc:
        st.error(f"无法连接 Agent 服务：{exc}")
        return
    labels = {item["id"]: f"{item['title']} · {item['status']}" for item in matches}
    selected = st.sidebar.selectbox(
        "JD 匹配历史",
        options=["", *list(labels)],
        format_func=lambda value: "新建 JD 匹配" if not value else labels[value],
    )
    if selected:
        render_match_task(match_client, selected)
    else:
        render_match_create(match_client, profiles)


def render_match_create(client: MatchClient, profiles: list[dict]) -> None:
    if not profiles:
        st.info("请先完成至少一个资料画像任务。")
        return
    profile_labels = {item["id"]: item["title"] for item in profiles}
    with st.form("match-create-form"):
        profile_task_id = st.selectbox(
            "选择用户画像",
            options=list(profile_labels),
            format_func=lambda value: profile_labels[value],
        )
        title = st.text_input("匹配任务名称")
        jd_text = st.text_area("岗位 JD", height=320, placeholder="请粘贴完整岗位职责和任职要求")
        submitted = st.form_submit_button("开始匹配", type="primary")
    if submitted:
        try:
            response = client.create_match(profile_task_id, jd_text, title)
            st.success(f"JD 匹配任务已创建：{response['match_id']}")
            st.rerun()
        except MatchClientError as exc:
            st.error(str(exc))


def render_match_task(client: MatchClient, match_id: str) -> None:
    try:
        task = client.get_task(match_id)
    except MatchClientError as exc:
        st.error(str(exc))
        return
    st.subheader(task["title"])
    st.progress(task["progress"] / 100, text=f"{task['stage']} · {task['status']}")
    with st.expander("岗位 JD"):
        st.text(task["jd_text"])
    if task.get("error"):
        st.warning(task["error"])
    if st.button("刷新匹配状态"):
        st.rerun()
    if task["status"] in {"completed", "partial_success"}:
        render_match_result(client, match_id)
    elif task["status"] in {"failed", "failed_retryable"}:
        if st.button("重试 JD 匹配", type="primary"):
            client.retry(match_id)
            st.rerun()
    if task["status"] not in {"queued", "analyzing_jd", "matching", "generating", "auditing"}:
        st.divider()
        if st.button("删除 JD 匹配任务"):
            client.delete(match_id)
            st.rerun()


def render_match_result(client: MatchClient, match_id: str) -> None:
    try:
        result = client.get_result(match_id)
        versions = client.list_versions(match_id)
    except MatchClientError as exc:
        st.error(str(exc))
        return
    score_col, coverage_col, version_col = st.columns(3)
    score_col.metric("总体匹配度", f"{result['overall_score']:.1f}")
    coverage_col.metric("关键词覆盖率", f"{result['keyword_coverage']['ratio']:.0%}")
    version_col.metric("当前版本", f"v{result['version']}")
    dimension_rows = [
        {"维度": key, "分数": value["score"]} for key, value in result["dimension_scores"].items()
    ]
    st.dataframe(dimension_rows, use_container_width=True, hide_index=True)
    analysis_col, gap_col = st.columns(2)
    with analysis_col:
        st.markdown("**核心优势**")
        for item in result["strengths"]:
            st.markdown(f"- {item}")
    with gap_col:
        st.markdown("**能力缺口**")
        for item in result["gaps"]:
            st.markdown(f"- {item}")
    st.caption(
        f"匹配关键词：{'、'.join(result['keyword_coverage']['matched']) or '无'}｜"
        f"缺失关键词：{'、'.join(result['keyword_coverage']['missing']) or '无'}"
    )

    updates: list[dict] = []
    tabs = st.tabs(["个人介绍", "专业介绍", "项目经历", "比赛经历", "实习经历", "学校履历"])
    section_names = [
        "personal_introduction",
        "professional_introduction",
        "project_experiences",
        "competition_experiences",
        "internship_experiences",
        "education_history",
    ]
    for tab, section_name in zip(tabs, section_names, strict=True):
        with tab:
            for label, unit in _editable_units(result[section_name]):
                value = st.text_area(
                    label,
                    value=unit["content"],
                    key=f"match:{match_id}:v{result['version']}:{unit['id']}",
                )
                if value.strip() != unit["content"]:
                    updates.append({"unit_id": unit["id"], "content": value.strip()})
                with st.expander(f"{label} · 证据"):
                    st.json(unit["evidence_refs"])
    if st.button("保存文案修改", type="primary", disabled=not updates):
        try:
            client.update_draft(match_id, result["version"], updates)
            st.success("已保存为新版本。")
            st.rerun()
        except MatchClientError as exc:
            st.error(str(exc))

    if versions:
        version_map = {
            item["version"]: f"v{item['version']} · {item['source']} · {item['created_at']}"
            for item in versions
        }
        selected_version = st.selectbox(
            "历史版本",
            options=list(version_map),
            format_func=lambda value: version_map[value],
        )
        if st.button("恢复所选版本", disabled=selected_version == result["version"]):
            client.restore(match_id, selected_version)
            st.rerun()

    col1, col2, col3, col4 = st.columns(4)
    col1.download_button(
        "下载 Markdown",
        data=client.download(match_id, "md"),
        file_name="jd-match.md",
        mime="text/markdown",
    )
    col2.download_button(
        "下载 DOCX",
        data=client.download(match_id, "docx"),
        file_name="jd-match.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    col3.download_button(
        "下载 JSON",
        data=client.download(match_id, "json"),
        file_name="jd-match.json",
        mime="application/json",
    )
    if col4.button("重新生成文案"):
        client.regenerate(match_id)
        st.rerun()


def _editable_units(section: dict) -> list[tuple[str, dict]]:
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


def render_upload(client: ProfileClient) -> None:
    with st.form("upload-form"):
        title = st.text_input("任务名称")
        files = st.file_uploader(
            "上传资料",
            type=["doc", "docx", "pdf", "md", "ppt", "pptx"],
            accept_multiple_files=True,
        )
        review = st.toggle("生成前核对事实")
        submitted = st.form_submit_button("开始整理", type="primary")
    if submitted:
        if not files:
            st.warning("请先上传资料。")
            return
        try:
            response = client.create_profile(
                files,
                review_mode="pause" if review else "auto",
                title=title,
            )
            st.success(f"任务已创建：{response['task_id']}")
            st.rerun()
        except ProfileClientError as exc:
            st.error(str(exc))


def render_task(client: ProfileClient, task_id: str) -> None:
    try:
        task = client.get_task(task_id)
    except ProfileClientError as exc:
        st.error(str(exc))
        return
    st.subheader(task["title"])
    st.progress(task["progress"] / 100, text=f"{task['stage']} · {task['status']}")
    if task.get("error"):
        st.warning(task["error"])
    with st.expander("文件处理状态"):
        st.dataframe(task["documents"], use_container_width=True)
    if st.button("刷新状态"):
        st.rerun()

    status = task["status"]
    if status == "awaiting_review":
        render_fact_review(client, task_id)
    elif status in {"completed", "partial_success"}:
        render_result(client, task_id)
    elif status in {"failed", "failed_retryable"}:
        if st.button("重试任务", type="primary"):
            client.retry(task_id)
            st.rerun()

    st.divider()
    if status not in {"queued", "parsing", "extracting", "generating", "auditing"}:
        if st.button("删除任务", type="secondary"):
            client.delete(task_id)
            st.rerun()


def render_fact_review(client: ProfileClient, task_id: str) -> None:
    payload = client.get_facts(task_id)
    facts = payload["facts"]
    st.info("可修改事实文本、分类、置信度和状态；证据引用会被保留。")
    rows = [
        {
            "id": fact["id"],
            "category": fact["category"],
            "statement": fact["statement"],
            "confidence": fact["confidence"],
            "status": fact["status"],
        }
        for fact in facts
    ]
    edited = st.data_editor(rows, use_container_width=True, num_rows="fixed")
    if payload["conflicts"]:
        st.warning("检测到材料冲突，请结合来源核对。")
        st.json(payload["conflicts"])
    col1, col2 = st.columns(2)
    if col1.button("保存修改"):
        by_id = {fact["id"]: fact for fact in facts}
        updated = []
        for row in edited:
            fact = by_id[row["id"]]
            fact.update(row)
            updated.append(fact)
        client.update_facts(task_id, updated)
        st.success("事实已保存。")
    if col2.button("确认并生成画像", type="primary"):
        client.resume(task_id)
        st.rerun()


def render_result(client: ProfileClient, task_id: str) -> None:
    result = client.get_result(task_id)
    tabs = st.tabs(["个人介绍", "专业介绍", "项目经历", "比赛经历", "实习经历", "学校履历"])
    keys = [
        "personal_introduction",
        "professional_introduction",
        "project_experiences",
        "competition_experiences",
        "internship_experiences",
        "education_history",
    ]
    for tab, key in zip(tabs, keys, strict=True):
        with tab:
            st.json(result[key], expanded=True)
    if result.get("conflicts"):
        with st.expander("待核对冲突"):
            st.json(result["conflicts"])
    st.caption(f"引用覆盖率：{result['audit']['citation_coverage']:.0%}")
    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "下载 Markdown",
        data=client.download(task_id, "md"),
        file_name="profile.md",
        mime="text/markdown",
    )
    col2.download_button(
        "下载 DOCX",
        data=client.download(task_id, "docx"),
        file_name="profile.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    col3.download_button(
        "下载 JSON",
        data=__import__("json").dumps(result, ensure_ascii=False, indent=2),
        file_name="profile.json",
        mime="application/json",
    )
    if st.button("根据当前事实重新生成"):
        client.regenerate(task_id)
        st.rerun()


if __name__ == "__main__":
    main()
