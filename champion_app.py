"""
AI챔피언 데이터분석 문제 자동 생성기
- CSV/XLSX 업로드 → 데이터 분석 → 문제 5개 자동 생성
- 산출물(HTML/Excel/PNG) 자동 생성 → ZIP 다운로드
"""
from __future__ import annotations
import os
import traceback

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai

from champion.profiler import profile_dataframe
from champion.problem_gen import estimate_domain, generate_problems
from champion.artifact_gen import generate_all_artifacts
from champion.grading_gen import generate_grading_rubric
from champion.packager import build_problems_html, package_all

load_dotenv()

# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="AI챔피언 문제 자동 생성기",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
MAX_PROFILE_ROWS = 10_000


# ── Gemini 클라이언트 ─────────────────────────────────────────
@st.cache_resource
def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error(
            "GEMINI_API_KEY가 설정되지 않았습니다. "
            ".env 파일에 GEMINI_API_KEY=... 를 추가해 주세요."
        )
        st.stop()
    return genai.Client(api_key=api_key)


# ── 파일 로딩 ─────────────────────────────────────────────────
def load_dataframe(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(uploaded, encoding="utf-8")
        except UnicodeDecodeError:
            uploaded.seek(0)
            return pd.read_csv(uploaded, encoding="cp949")
    return pd.read_excel(uploaded)


# ── 세션 초기화 ───────────────────────────────────────────────
def init_session():
    defaults = {
        "_last_file": None,
        "df": None,
        "profile": None,
        "domain": None,
        "problems": None,
        "artifacts": None,
        "grading_xlsx": None,
        "zip_bytes": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── 데이터 프로파일 렌더링 ────────────────────────────────────
def render_profile_view(df: pd.DataFrame, profile):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 행 수", f"{profile.row_count:,}")
    c2.metric("수치형 컬럼", len(profile.numeric_cols))
    c3.metric("범주형 컬럼", len(profile.categorical_cols))
    c4.metric("날짜형 컬럼", len(profile.datetime_cols))

    with st.expander("데이터 미리보기 (상위 5행)", expanded=True):
        st.dataframe(df.head(), use_container_width=True)

    with st.expander("컬럼 상세 분석"):
        rows = []
        for cp in profile.columns:
            stat_preview = ""
            if cp.category == "numeric" and cp.stats:
                stat_preview = f"평균 {cp.stats.get('mean')}, 최대 {cp.stats.get('max')}"
            elif cp.category == "categorical" and cp.stats:
                top = cp.stats.get("top_values", {})
                stat_preview = " / ".join(f"{k}({v})" for k, v in list(top.items())[:3])
            rows.append({
                "컬럼명": cp.name,
                "유형": cp.category,
                "결측률": f"{cp.null_pct}%",
                "고유값 수": cp.unique_count,
                "샘플": stat_preview,
            })
        st.dataframe(rows, use_container_width=True)


# ── 문제 목록 렌더링 ──────────────────────────────────────────
TYPE_COLOR = {
    "html_dashboard": "#0366d6",
    "html_filter": "#28a745",
    "excel_vba": "#6f42c1",
    "png_infographic": "#e36209",
    "html_policy": "#d73a49",
}
TYPE_ICON = {
    "html_dashboard": "📊",
    "html_filter": "🔍",
    "excel_vba": "📋",
    "png_infographic": "🎨",
    "html_policy": "📝",
}


def render_problems(problems: list):
    for p in problems:
        icon = TYPE_ICON.get(p.type_id, "📌")
        color = TYPE_COLOR.get(p.type_id, "#333")

        with st.container(border=True):
            st.markdown(
                f'<span style="background:{color};color:white;padding:3px 12px;'
                f'border-radius:12px;font-size:.85rem;font-weight:bold;">'
                f'{icon} 문제 {p.number}</span> '
                f'<span style="color:{color};font-weight:600"> {p.type_name}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**{p.title}**")
            st.caption(p.scenario[:180] + ("…" if len(p.scenario) > 180 else ""))

            with st.expander("필수 요건 & 채점 기준 보기"):
                col_l, col_r = st.columns([1, 1])
                with col_l:
                    st.markdown("**필수 구현 사항**")
                    for req in p.requirements:
                        st.markdown(f"- {req}")
                with col_r:
                    st.markdown("**채점 기준 (100점)**")
                    for ri in p.rubric:
                        st.markdown(f"- **{ri.score}점** {ri.criterion}")
                        st.caption(f"  → {ri.description}")

                st.markdown(f"📁 **제출 파일:** `{p.submission_filename}`")
                if p.hint:
                    st.info(f"💡 AI 힌트: {p.hint}")


# ── 산출물 미리보기 렌더링 ────────────────────────────────────
def render_artifacts_preview(problems: list, artifacts: dict):
    st.subheader("생성된 산출물 미리보기")

    for p in problems:
        fname = p.submission_filename
        content = artifacts.get(fname)
        if content is None:
            continue

        icon = TYPE_ICON.get(p.type_id, "📌")
        with st.expander(f"{icon} 문제 {p.number}: {p.title} — `{fname}`", expanded=False):
            if p.type_id == "png_infographic" and isinstance(content, bytes):
                st.image(content, caption=f"문제 {p.number} 인포그래픽", use_container_width=True)
                st.download_button(
                    f"📥 {fname} 다운로드",
                    content,
                    file_name=fname,
                    mime="image/png",
                    key=f"dl_art_{p.number}",
                )
            elif p.type_id == "excel_vba" and isinstance(content, bytes):
                st.info("Excel 파일은 미리보기를 지원하지 않습니다. ZIP에서 다운로드하세요.")
                st.download_button(
                    f"📥 {fname} 다운로드",
                    content,
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_art_{p.number}",
                )
                vba_code = artifacts.get("vba_code", "")
                if vba_code:
                    with st.expander("VBA 코드 미리보기"):
                        st.code(vba_code, language="vba")
                    st.download_button(
                        "📥 VBA 코드 (.bas) 다운로드",
                        vba_code.encode("utf-8"),
                        file_name="problem_03_vba_code.bas",
                        mime="text/plain",
                        key="dl_vba",
                    )
            elif isinstance(content, bytes) and fname.endswith(".html"):
                html_str = content.decode("utf-8", errors="replace")
                # HTML 미리보기 (sandboxed iframe)
                st.components.v1.html(html_str, height=420, scrolling=True)
                st.download_button(
                    f"📥 {fname} 다운로드",
                    content,
                    file_name=fname,
                    mime="text/html",
                    key=f"dl_art_{p.number}",
                )


# ── 메인 앱 ──────────────────────────────────────────────────
def main():
    init_session()
    client = get_client()

    # ── 헤더 ─────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a3a5c,#2980b9);
                color:white;padding:32px 24px;border-radius:12px;margin-bottom:24px;text-align:center">
      <h1 style="margin:0;font-size:2rem">🏆 AI챔피언 데이터분석 문제 자동 생성기</h1>
      <p style="opacity:.85;margin:8px 0 0">
        CSV/XLSX 업로드 → 데이터 분석 → 5문제 자동 출제 → 산출물·채점표 다운로드
      </p>
      <p style="opacity:.7;font-size:.85rem;margin-top:6px">
        ⚡ AI챔피언 그린 수준 | HTML · Excel VBA · PNG 결과물 중심 채점
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── STEP 1: 파일 업로드 ──────────────────────────────────
    st.header("① 데이터 파일 업로드")
    uploaded = st.file_uploader(
        "공공 데이터 CSV 또는 XLSX 파일을 선택하세요",
        type=["csv", "xlsx", "xls"],
        help="예: 서울시 범죄 현황, 지역별 인구 통계, 공공시설 이용 현황 등",
    )

    if uploaded is not None:
        if st.session_state["_last_file"] != uploaded.name:
            for k in ["df", "profile", "domain", "problems", "artifacts", "grading_xlsx", "zip_bytes"]:
                st.session_state[k] = None
            st.session_state["_last_file"] = uploaded.name

        if st.session_state["df"] is None:
            with st.spinner("파일을 읽는 중..."):
                try:
                    df = load_dataframe(uploaded)
                    st.session_state["df"] = df
                    profile = profile_dataframe(df.head(MAX_PROFILE_ROWS))
                    st.session_state["profile"] = profile
                    st.success(
                        f"✅ `{uploaded.name}` 로드 완료 "
                        f"({profile.row_count:,}행 × {profile.col_count}열 | "
                        f"수치형 {len(profile.numeric_cols)}개 · "
                        f"범주형 {len(profile.categorical_cols)}개)"
                    )
                except Exception as exc:
                    st.error(f"파일 읽기 오류: {exc}")
                    st.stop()

    if st.session_state["df"] is None:
        st.info("👆 파일을 업로드하면 분석이 시작됩니다.")
        return

    df: pd.DataFrame = st.session_state["df"]
    profile = st.session_state["profile"]

    # ── STEP 2: 데이터 프로파일링 ──────────────────────────
    st.header("② 데이터 자동 분석")
    render_profile_view(df, profile)

    # ── STEP 3: 문제 생성 ───────────────────────────────────
    st.header("③ 데이터 도메인 추정 & 문제 5개 자동 생성")

    col_gen, col_regen = st.columns([2, 1])
    with col_gen:
        gen_disabled = st.session_state["problems"] is not None
        if st.button(
            "🤖 문제 자동 생성하기 (5문제)",
            type="primary",
            disabled=gen_disabled,
            use_container_width=True,
        ):
            with st.spinner("① 데이터 도메인 추정 중..."):
                try:
                    domain = estimate_domain(client, MODEL, profile)
                    st.session_state["domain"] = domain
                except Exception:
                    domain = "공공행정"
                    st.session_state["domain"] = domain

            with st.spinner(f"② [{domain}] 도메인 기반 문제 5개 생성 중..."):
                try:
                    problems = generate_problems(client, MODEL, profile, domain)
                    st.session_state["problems"] = problems
                    st.session_state["artifacts"] = None
                    st.session_state["grading_xlsx"] = None
                    st.session_state["zip_bytes"] = None
                    st.rerun()
                except Exception as exc:
                    st.error(f"문제 생성 오류: {exc}")
                    with st.expander("에러 상세"):
                        st.code(traceback.format_exc(), language="text")

    with col_regen:
        if st.button("🔄 재생성", use_container_width=True):
            for k in ["problems", "artifacts", "grading_xlsx", "zip_bytes"]:
                st.session_state[k] = None
            st.rerun()

    problems = st.session_state.get("problems")
    if not problems:
        return

    if st.session_state.get("domain"):
        st.caption(f"🏷️ 추정 도메인: **{st.session_state['domain']}**")

    render_problems(problems)

    # ── STEP 4: 산출물 자동 생성 ───────────────────────────
    st.header("④ 예시 정답 산출물 자동 생성")
    st.caption(
        "각 문제에 대한 예시 답안 파일(HTML/Excel/PNG)을 AI가 자동으로 생성합니다. "
        "약 1~3분 소요됩니다."
    )

    if st.session_state.get("artifacts") is None:
        if st.button(
            "⚙️ 산출물 자동 생성 시작 (5개 파일 + 채점표)",
            type="primary",
            use_container_width=True,
        ):
            progress_bar = st.progress(0, "생성 준비 중...")
            status_text = st.empty()

            def on_progress(idx: int, label: str):
                pct = int(idx / len(problems) * 100)
                progress_bar.progress(pct, f"[{idx}/{len(problems)}] {label}")
                status_text.caption(f"진행: {label} 생성 중...")

            try:
                artifacts = generate_all_artifacts(
                    client, MODEL, df, profile, problems,
                    progress_callback=on_progress,
                )
                progress_bar.progress(95, "채점 기준표 생성 중...")
                grading_xlsx = generate_grading_rubric(problems)
                progress_bar.progress(100, "완료!")
                status_text.success("✅ 모든 산출물 생성 완료!")

                st.session_state["artifacts"] = artifacts
                st.session_state["grading_xlsx"] = grading_xlsx
                st.session_state["zip_bytes"] = None  # 재생성 대기
                st.rerun()
            except Exception as exc:
                progress_bar.empty()
                st.error(f"산출물 생성 오류: {exc}")
                with st.expander("에러 상세"):
                    st.code(traceback.format_exc(), language="text")
    else:
        st.success("✅ 산출물 생성 완료")
        if st.button("🔄 산출물 재생성"):
            st.session_state["artifacts"] = None
            st.session_state["grading_xlsx"] = None
            st.session_state["zip_bytes"] = None
            st.rerun()

    artifacts = st.session_state.get("artifacts")
    grading_xlsx = st.session_state.get("grading_xlsx")

    if not artifacts:
        return

    # ── STEP 5: 미리보기 & 다운로드 ────────────────────────
    st.header("⑤ 산출물 미리보기 & 다운로드")
    render_artifacts_preview(problems, artifacts)

    # 채점표 개별 다운로드
    if grading_xlsx:
        st.divider()
        st.subheader("📊 채점 기준표")
        st.download_button(
            "📥 grading_rubric.xlsx 다운로드",
            grading_xlsx,
            file_name="grading_rubric.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_rubric",
        )

    # 문제지 HTML 다운로드
    st.divider()
    st.subheader("📄 문제지")
    problems_html = build_problems_html(problems).encode("utf-8")
    st.download_button(
        "📥 problems.html 다운로드 (전체 문제지)",
        problems_html,
        file_name="problems.html",
        mime="text/html",
        key="dl_problems",
    )

    # ── 전체 ZIP 다운로드 ──────────────────────────────────
    st.divider()
    st.subheader("📦 전체 패키지 ZIP 다운로드")
    st.caption(
        "problems.html · grading_rubric.xlsx · 5개 산출물 · "
        "answer_key.json · README.md 를 하나의 ZIP으로 다운로드합니다."
    )

    if st.session_state.get("zip_bytes") is None:
        with st.spinner("ZIP 패키징 중..."):
            try:
                zip_bytes = package_all(problems, artifacts, grading_xlsx)
                st.session_state["zip_bytes"] = zip_bytes
            except Exception as exc:
                st.error(f"ZIP 생성 오류: {exc}")
                zip_bytes = None
    else:
        zip_bytes = st.session_state["zip_bytes"]

    if zip_bytes:
        st.download_button(
            label="📥 전체 패키지 ZIP 다운로드",
            data=zip_bytes,
            file_name="ai_champion_문제패키지.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

        # ZIP 내용 목록
        with st.expander("ZIP 포함 파일 목록"):
            import zipfile, io as _io
            with zipfile.ZipFile(_io.BytesIO(zip_bytes)) as zf:
                for name in zf.namelist():
                    size = zf.getinfo(name).file_size
                    st.text(f"  {name}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
