"""
데이터 분석 교육용 문제 제작 웹 애플리케이션
- 데이터 업로드 → 프로파일링 → LLM 문제 생성 → 풀이/해답 다운로드
"""

import os
import json
import io
import re
import textwrap
import traceback
from contextlib import redirect_stdout

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ────────────────────────────────────────────────────────────
# 설정
# ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="데이터 분석 문제 생성기",
    page_icon="📊",
    layout="wide",
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
MAX_SAMPLE_ROWS = 5       # 프롬프트에 포함할 샘플 행 수
MAX_PROFILE_ROWS = 10_000 # 프로파일링에 사용할 최대 행 수


# ────────────────────────────────────────────────────────────
# Gemini 클라이언트 초기화
# ────────────────────────────────────────────────────────────
@st.cache_resource
def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error(
            "GEMINI_API_KEY가 설정되지 않았습니다. "
            "프로젝트 루트의 .env 파일에 GEMINI_API_KEY=... 형태로 추가하거나, "
            "PowerShell에서 $env:GEMINI_API_KEY=... 설정 후 재실행해 주세요."
        )
        st.stop()
    return genai.Client(api_key=api_key)


# ────────────────────────────────────────────────────────────
# 데이터 로딩
# ────────────────────────────────────────────────────────────
def load_dataframe(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        # 인코딩 자동 감지 시도
        try:
            return pd.read_csv(uploaded_file, encoding="utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="cp949")
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError("CSV 또는 XLSX 파일만 지원합니다.")


# ────────────────────────────────────────────────────────────
# 데이터 프로파일링
# ────────────────────────────────────────────────────────────
def build_data_summary(df: pd.DataFrame) -> str:
    """LLM 프롬프트에 넣을 데이터 요약 문자열을 생성합니다."""
    sample = df.head(MAX_SAMPLE_ROWS)

    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_pct = df[col].isna().mean() * 100
        unique_cnt = df[col].nunique()
        col_info.append(
            f"  - {col} (타입: {dtype}, 결측률: {null_pct:.1f}%, 고유값: {unique_cnt}개)"
        )
    col_block = "\n".join(col_info)

    num_cols = df.select_dtypes(include="number")
    stats = num_cols.describe().round(3).to_string() if not num_cols.empty else "(수치형 컬럼 없음)"
    sample_csv = sample.to_csv(index=False)

    return textwrap.dedent(f"""
    [데이터셋 기본 정보]
    - 행 수: {len(df):,}
    - 열 수: {len(df.columns)}

    [컬럼 정보]
    {col_block}

    [수치형 컬럼 요약 통계]
    {stats}

    [샘플 데이터 (상위 {MAX_SAMPLE_ROWS}행, CSV 형식)]
    {sample_csv}
    """).strip()


def render_profile(df: pd.DataFrame):
    """Streamlit 화면에 데이터 프로파일을 렌더링합니다."""
    st.subheader("📋 데이터 개요")
    col1, col2, col3 = st.columns(3)
    col1.metric("전체 행 수", f"{len(df):,}")
    col2.metric("전체 열 수", len(df.columns))
    col3.metric("결측치 비율", f"{df.isna().mean().mean() * 100:.1f}%")

    with st.expander("상위 5행 미리보기", expanded=True):
        st.dataframe(df.head(), use_container_width=True)

    with st.expander("컬럼 정보 (타입 / 결측 / 고유값 수)"):
        info_df = pd.DataFrame({
            "컬럼명": df.columns,
            "데이터 타입": df.dtypes.values,
            "결측치 수": df.isna().sum().values,
            "결측률 (%)": (df.isna().mean() * 100).round(1).values,
            "고유값 수": df.nunique().values,
        })
        st.dataframe(info_df, use_container_width=True)

    with st.expander("수치형 컬럼 요약 통계"):
        num_df = df.select_dtypes(include="number")
        if not num_df.empty:
            st.dataframe(num_df.describe().round(3), use_container_width=True)
        else:
            st.info("수치형 컬럼이 없습니다.")

    with st.expander("📊 기본 시각화", expanded=True):
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        category_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

        tab1, tab2, tab3 = st.tabs(["수치형 분포", "범주형 분포", "산점도"])

        with tab1:
            if not numeric_cols:
                st.info("수치형 컬럼이 없어 분포 차트를 그릴 수 없습니다.")
            else:
                target_col = st.selectbox(
                    "분포를 볼 수치형 컬럼",
                    options=numeric_cols,
                    key="viz_hist_col",
                )
                bins = st.slider("구간 개수", min_value=5, max_value=60, value=20, key="viz_hist_bins")

                series = pd.to_numeric(df[target_col], errors="coerce").dropna()
                if series.empty:
                    st.info("유효한 수치 데이터가 없습니다.")
                else:
                    cut = pd.cut(series, bins=bins)
                    hist = cut.value_counts(sort=False)
                    hist_df = pd.DataFrame({"구간": hist.index.astype(str), "빈도": hist.values})
                    st.bar_chart(hist_df.set_index("구간"), use_container_width=True)

        with tab2:
            if not category_cols:
                st.info("범주형 컬럼이 없어 분포 차트를 그릴 수 없습니다.")
            else:
                target_col = st.selectbox(
                    "분포를 볼 범주형 컬럼",
                    options=category_cols,
                    key="viz_cat_col",
                )
                top_n = st.slider("상위 항목 수", min_value=5, max_value=30, value=10, key="viz_cat_topn")
                counts = (
                    df[target_col]
                    .astype("string")
                    .fillna("(결측)")
                    .value_counts()
                    .head(top_n)
                )
                if counts.empty:
                    st.info("표시할 범주 데이터가 없습니다.")
                else:
                    st.bar_chart(counts, use_container_width=True)

        with tab3:
            if len(numeric_cols) < 2:
                st.info("산점도는 수치형 컬럼 2개 이상일 때 표시할 수 있습니다.")
            else:
                x_col = st.selectbox("X축", options=numeric_cols, index=0, key="viz_scatter_x")
                default_y = 1 if len(numeric_cols) > 1 else 0
                y_col = st.selectbox("Y축", options=numeric_cols, index=default_y, key="viz_scatter_y")
                scatter_df = df[[x_col, y_col]].dropna().head(5000)
                if scatter_df.empty:
                    st.info("산점도로 표시할 데이터가 없습니다.")
                else:
                    st.scatter_chart(scatter_df, x=x_col, y=y_col, use_container_width=True)


def render_result_visualizations(df: pd.DataFrame, selected_problem: dict):
    """5단계 결과 영역에서 바로 확인할 수 있는 시각화 차트를 렌더링합니다."""
    st.subheader("📊 결과 시각화 차트")
    if selected_problem.get("유형") == "시각화":
        st.caption("선택한 시각화 문제에 맞춰 차트를 바로 표시합니다.")
    else:
        st.caption("선택한 문제와 함께 참고할 수 있는 기본 시각화 차트입니다.")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    category_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    tab1, tab2, tab3 = st.tabs(["수치형 분포", "범주형 분포", "산점도"])

    with tab1:
        if not numeric_cols:
            st.info("수치형 컬럼이 없어 분포 차트를 그릴 수 없습니다.")
        else:
            hist_col = st.selectbox(
                "분포를 볼 수치형 컬럼",
                options=numeric_cols,
                key="result_hist_col",
            )
            bins = st.slider("구간 개수", min_value=5, max_value=60, value=20, key="result_hist_bins")
            series = pd.to_numeric(df[hist_col], errors="coerce").dropna()
            if series.empty:
                st.info("유효한 수치 데이터가 없습니다.")
            else:
                cut = pd.cut(series, bins=bins)
                hist = cut.value_counts(sort=False)
                hist_df = pd.DataFrame({"구간": hist.index.astype(str), "빈도": hist.values})
                st.bar_chart(hist_df.set_index("구간"), use_container_width=True)

    with tab2:
        if not category_cols:
            st.info("범주형 컬럼이 없어 분포 차트를 그릴 수 없습니다.")
        else:
            cat_col = st.selectbox(
                "분포를 볼 범주형 컬럼",
                options=category_cols,
                key="result_cat_col",
            )
            top_n = st.slider("상위 항목 수", min_value=5, max_value=30, value=10, key="result_cat_topn")
            counts = (
                df[cat_col]
                .astype("string")
                .fillna("(결측)")
                .value_counts()
                .head(top_n)
            )
            if counts.empty:
                st.info("표시할 범주 데이터가 없습니다.")
            else:
                st.bar_chart(counts, use_container_width=True)

    with tab3:
        if len(numeric_cols) < 2:
            st.info("산점도는 수치형 컬럼 2개 이상일 때 표시할 수 있습니다.")
        else:
            x_col = st.selectbox("X축", options=numeric_cols, index=0, key="result_scatter_x")
            default_y = 1 if len(numeric_cols) > 1 else 0
            y_col = st.selectbox("Y축", options=numeric_cols, index=default_y, key="result_scatter_y")
            scatter_df = df[[x_col, y_col]].dropna().head(5000)
            if scatter_df.empty:
                st.info("산점도로 표시할 데이터가 없습니다.")
            else:
                st.scatter_chart(scatter_df, x=x_col, y=y_col, use_container_width=True)


# ────────────────────────────────────────────────────────────
# LLM 호출: 문제 생성
# ────────────────────────────────────────────────────────────
PROBLEM_SYSTEM_PROMPT = """당신은 데이터 분석 교육 전문가입니다.
주어진 데이터셋의 특성을 정확히 파악하여, 학습자가 실제로 풀 수 있는
현실적이고 흥미로운 데이터 분석 문제를 출제합니다.
반드시 JSON 배열 형식으로만 응답하며, 다른 텍스트는 포함하지 않습니다."""

PROBLEM_USER_TEMPLATE = """제공된 데이터의 스키마와 샘플 데이터는 다음과 같다:

{data_summary}

이 데이터를 활용해 [통계, 시각화, 예측, 분류] 유형이 골고루 섞인 데이터 분석 문제 5개를 출제해줘.
각 문제는 데이터의 비즈니스 맥락을 반영해야 해.

반드시 아래 JSON 배열 형식으로만 응답해:
[
  {{
    "번호": 1,
    "유형": "통계",
    "제목": "문제 제목",
    "내용": "구체적인 문제 내용 (어떤 분석을 수행해야 하는지 명확하게)",
    "평가기준": "정답 숫자 1개로 자동 채점 가능하도록 기준 명시",
    "정답형식": "숫자 1개 (예: 소수점 둘째 자리 반올림)",
    "시각화요구": "(시각화 유형일 때만) 차트 종류와 x축/y축/집계 기준을 명시"
  }},
  ...
]

유형은 반드시 "통계", "시각화", "예측", "분류" 중 하나이며, 5개 중 4가지 유형이 모두 포함되어야 한다.

반드시 지킬 제약:
1) 모든 문제는 최종 정답을 숫자 1개로 채점 가능해야 한다.
2) 범위형/서술형/복수정답/주관식 해석 문제는 금지한다.
3) 시각화 문제는 반드시 특정 차트를 지정해야 한다. 예: "막대차트로 x축=자치구, y축=평균 범죄건수".
4) 시각화 문제도 최종 평가는 숫자 1개여야 한다. 예: "그래프에서 최대값에 해당하는 평균 범죄건수(숫자 1개)".
5) 평가기준에는 허용 오차 및 반올림 규칙(예: 소수점 둘째 자리)을 명시한다."""


def _parse_problem_list(raw: str) -> list[dict]:
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    for v in parsed.values():
        if isinstance(v, list):
            return v
    raise ValueError(f"예상치 못한 JSON 구조: {raw[:200]}")


def _validate_problem_set(problems: list[dict]) -> tuple[bool, str]:
    required_types = {"통계", "시각화", "예측", "분류"}
    type_set = {str(p.get("유형", "")).strip() for p in problems}
    if len(problems) != 5:
        return False, "문제 수는 정확히 5개여야 합니다."
    if not required_types.issubset(type_set):
        return False, "통계/시각화/예측/분류 4가지 유형이 모두 포함되어야 합니다."

    for i, p in enumerate(problems, start=1):
        body = str(p.get("내용", ""))
        eval_rule = str(p.get("평가기준", ""))
        answer_format = str(p.get("정답형식", ""))
        chart_req = str(p.get("시각화요구", ""))

        if "숫자" not in answer_format or "1개" not in answer_format:
            return False, f"{i}번 문제: 정답형식은 '숫자 1개' 조건을 명시해야 합니다."
        if not eval_rule:
            return False, f"{i}번 문제: 평가기준이 비어 있습니다."

        if str(p.get("유형", "")).strip() == "시각화":
            chart_keywords = ["막대", "선", "산점", "히트맵", "box", "박스"]
            if not any(k in body or k in chart_req for k in chart_keywords):
                return False, f"{i}번 문제: 시각화 유형은 특정 차트 종류를 지정해야 합니다."
            if not (("x축" in body and "y축" in body) or ("x축" in chart_req and "y축" in chart_req)):
                return False, f"{i}번 문제: 시각화 유형은 x축/y축 지시가 필요합니다."

    return True, "ok"


def generate_problems(client: genai.Client, data_summary: str) -> list[dict]:
    """LLM으로 분석 문제 5개를 생성합니다."""
    prompt = PROBLEM_USER_TEMPLATE.format(data_summary=data_summary)
    last_error = ""

    for attempt in range(3):
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PROBLEM_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        raw = (response.text or "").strip()

        try:
            problems = _parse_problem_list(raw)
            ok, reason = _validate_problem_set(problems)
            if ok:
                return problems
            last_error = reason
            prompt = (
                PROBLEM_USER_TEMPLATE.format(data_summary=data_summary)
                + f"\n\n이전 응답 실패 사유: {reason}\n"
                + "반드시 실패 사유를 해결해 다시 JSON 배열만 출력해."
            )
        except Exception as e:
            last_error = str(e)
            prompt = (
                PROBLEM_USER_TEMPLATE.format(data_summary=data_summary)
                + "\n\nJSON 파싱 가능한 형식으로만 다시 출력해."
            )

    raise ValueError(f"채점 가능한 문제 형식 생성 실패: {last_error}")


# ────────────────────────────────────────────────────────────
# LLM 호출: 풀이 및 해답 생성
# ────────────────────────────────────────────────────────────
SOLUTION_SYSTEM_PROMPT = """당신은 데이터 분석 및 Python 프로그래밍 전문가입니다.
주어진 문제에 대해 실제로 실행 가능한 풀이 코드와 명확한 해답을 제공합니다.
마크다운 형식으로 응답하며, [문제풀이]와 [해답] 두 섹션을 반드시 포함합니다."""

SOLUTION_USER_TEMPLATE = """아래 데이터셋 정보와 분석 문제를 해결해줘.

[데이터셋 정보]
{data_summary}

[선택된 분석 문제]
유형: {problem_type}
제목: {problem_title}
내용: {problem_content}

다음 두 섹션을 마크다운 형식으로 작성해줘:

---

## [문제풀이] 섹션 요구사항:
# [{problem_type}] {problem_title}

## 1. 분석 접근 방향 및 가설
- 이 문제를 해결하기 위한 분석 전략과 가설을 서술

## 2. Python 풀이 코드
```python
# Pandas, Scikit-learn, Matplotlib/Seaborn/Plotly 기반의 완전한 실행 가능 코드
# 시각화 유형 문제라면 그래프 코드(예: matplotlib/seaborn/plotly) 최소 1개를 반드시 포함
# 데이터 로드는 `df` 변수가 이미 있다고 가정하고 작성
```

## 3. 코드 설명 및 인사이트
- 각 코드 블록의 역할과 분석 결과에서 얻을 수 있는 인사이트 설명

---

## [해답] 섹션 요구사항:
# 문제 최종 해답 및 결론

- 분석 결과에서 기대되는 명확한 수치, 그래프 해석 결과, 또는 모델 성능 지표 요약
- 비즈니스적 시사점 포함

---

[문제풀이]와 [해답]을 명확히 구분할 수 있도록 `===문제풀이===`와 `===해답===` 구분자를 각 섹션 시작 전에 넣어줘."""


def generate_solution(
    client: genai.Client,
    data_summary: str,
    problem: dict,
) -> tuple[str, str]:
    """LLM으로 풀이와 해답을 생성하고 (문제풀이 md, 해답 md) 튜플로 반환합니다."""
    response = client.models.generate_content(
        model=MODEL,
        contents=SOLUTION_USER_TEMPLATE.format(
            data_summary=data_summary,
            problem_type=problem.get("유형", ""),
            problem_title=problem.get("제목", ""),
            problem_content=problem.get("내용", ""),
        ),
        config=types.GenerateContentConfig(
            system_instruction=SOLUTION_SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=4096,
        ),
    )
    raw = (response.text or "").strip()

    if "===문제풀이===" in raw and "===해답===" in raw:
        parts = raw.split("===해답===")
        solution_part = parts[0].replace("===문제풀이===", "").strip()
        answer_part = parts[1].strip()
    else:
        solution_part = raw
        answer_part = "# 문제 최종 해답 및 결론\n\n(LLM 응답 구조를 확인해 주세요.)"

    return solution_part, answer_part


def extract_python_code(markdown_text: str) -> str:
    """마크다운에서 첫 번째 Python 코드 블록을 추출합니다."""
    if not markdown_text:
        return ""

    py_match = re.search(r"```python\s*(.*?)```", markdown_text, re.DOTALL | re.IGNORECASE)
    if py_match:
        return py_match.group(1).strip()

    any_match = re.search(r"```\s*(.*?)```", markdown_text, re.DOTALL)
    if any_match:
        return any_match.group(1).strip()

    return ""


def execute_solution_code(code: str, df: pd.DataFrame) -> dict:
    """풀이 코드를 실행하고 stdout/결과값/에러를 반환합니다."""
    local_env = {
        "df": df.copy(),
        "pd": pd,
        "st": st,
    }
    global_env = {"__builtins__": __builtins__}
    stdout_buffer = io.StringIO()

    try:
        with redirect_stdout(stdout_buffer):
            exec(code, global_env, local_env)

        stdout_text = stdout_buffer.getvalue().strip()
        result_value = None

        preferred_keys = ["final_answer", "answer", "result", "final_value", "score", "metric"]
        for key in preferred_keys:
            if key in local_env:
                result_value = local_env[key]
                break

        if result_value is None:
            scalar_values = [
                (k, v)
                for k, v in local_env.items()
                if not k.startswith("_") and isinstance(v, (int, float, str, bool))
            ]
            if scalar_values:
                result_value = scalar_values[-1][1]

        return {
            "ok": True,
            "stdout": stdout_text,
            "result_value": result_value,
            "error": "",
            "traceback": "",
        }
    except Exception as e:
        return {
            "ok": False,
            "stdout": stdout_buffer.getvalue().strip(),
            "result_value": None,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


# ────────────────────────────────────────────────────────────
# 세션 상태 초기화
# ────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "df": None,
        "data_summary": None,
        "problems": None,
        "selected_idx": 0,
        "solution_md": None,
        "answer_md": None,
        "exec_code": None,
        "exec_stdout": None,
        "exec_result": None,
        "exec_error": None,
        "exec_traceback": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ────────────────────────────────────────────────────────────
# 메인 애플리케이션
# ────────────────────────────────────────────────────────────
def main():
    init_session()
    client = get_client()

    st.title("📊 데이터 분석 문제 생성기")
    st.caption("CSV/XLSX 파일을 업로드하면 AI가 맞춤형 데이터 분석 문제를 자동으로 생성합니다.")

    # ── STEP 1: 파일 업로드 ─────────────────────────────────
    st.header("1단계: 데이터셋 업로드")
    uploaded = st.file_uploader(
        "CSV 또는 XLSX 파일을 선택하세요",
        type=["csv", "xlsx", "xls"],
        help="최대 200MB 파일을 지원합니다.",
    )

    if uploaded is not None:
        if st.session_state.get("_last_filename") != uploaded.name:
            for key in (
                "df",
                "data_summary",
                "problems",
                "solution_md",
                "answer_md",
                "exec_code",
                "exec_stdout",
                "exec_result",
                "exec_error",
                "exec_traceback",
            ):
                st.session_state[key] = None
            st.session_state["_last_filename"] = uploaded.name

        if st.session_state["df"] is None:
            with st.spinner("파일을 읽는 중..."):
                try:
                    df = load_dataframe(uploaded)
                    st.session_state["df"] = df
                    st.session_state["data_summary"] = build_data_summary(
                        df.head(MAX_PROFILE_ROWS)
                    )
                    st.success(f"✅ '{uploaded.name}' 파일이 성공적으로 로드되었습니다.")
                except Exception as e:
                    st.error(f"파일 읽기 오류: {e}")
                    st.stop()

    if st.session_state["df"] is None:
        st.info("👆 위에서 파일을 업로드하면 분석이 시작됩니다.")
        return

    df: pd.DataFrame = st.session_state["df"]

    # ── STEP 2: 데이터 프로파일링 ────────────────────────────
    st.header("2단계: 데이터 프로파일링")
    render_profile(df)

    # ── STEP 3: 문제 생성 ─────────────────────────────────────
    st.header("3단계: 분석 문제 생성")

    if st.session_state["problems"] is None:
        if st.button("🤖 AI로 분석 문제 5개 생성하기", type="primary"):
            with st.spinner("LLM이 데이터를 분석하여 문제를 생성 중입니다..."):
                try:
                    problems = generate_problems(client, st.session_state["data_summary"])
                    st.session_state["problems"] = problems
                    st.session_state["solution_md"] = None
                    st.session_state["answer_md"] = None
                    st.session_state["exec_code"] = None
                    st.session_state["exec_stdout"] = None
                    st.session_state["exec_result"] = None
                    st.session_state["exec_error"] = None
                    st.session_state["exec_traceback"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"문제 생성 오류: {e}")
    else:
        if st.button("🔄 문제 다시 생성하기"):
            st.session_state["problems"] = None
            st.session_state["solution_md"] = None
            st.session_state["answer_md"] = None
            st.session_state["exec_code"] = None
            st.session_state["exec_stdout"] = None
            st.session_state["exec_result"] = None
            st.session_state["exec_error"] = None
            st.session_state["exec_traceback"] = None
            st.rerun()

    problems: list[dict] | None = st.session_state["problems"]
    if not problems:
        return

    # 문제 목록 출력
    st.subheader("생성된 문제 목록")
    TYPE_EMOJI = {"통계": "📈", "시각화": "🎨", "예측": "🔮", "분류": "🏷️"}

    for p in problems:
        emoji = TYPE_EMOJI.get(p.get("유형", ""), "📌")
        with st.container(border=True):
            st.markdown(
                f"**{emoji} 문제 {p.get('번호', '?')}. [{p.get('유형', '')}] {p.get('제목', '')}**"
            )
            st.write(p.get("내용", ""))
            if p.get("시각화요구"):
                st.caption(f"시각화요구: {p.get('시각화요구')}")
            if p.get("정답형식"):
                st.caption(f"정답형식: {p.get('정답형식')}")
            if p.get("평가기준"):
                st.caption(f"평가기준: {p.get('평가기준')}")

    # ── STEP 4: 문제 선택 및 풀이 생성 ──────────────────────
    st.header("4단계: 풀이 생성")

    choices = [
        f"문제 {p.get('번호', i+1)}. [{p.get('유형', '')}] {p.get('제목', '')}"
        for i, p in enumerate(problems)
    ]
    selected_label = st.radio(
        "풀고 싶은 문제를 선택하세요",
        options=choices,
        index=st.session_state["selected_idx"],
        key="problem_radio",
    )
    if selected_label is None:
        st.info("문제를 선택해 주세요.")
        return
    selected_idx = choices.index(selected_label)
    st.session_state["selected_idx"] = selected_idx
    selected_problem = problems[selected_idx]

    if st.button("✏️ 풀이 생성하기", type="primary"):
        with st.spinner("LLM이 풀이 코드와 해답을 작성 중입니다 (약 30~60초 소요)..."):
            try:
                sol_md, ans_md = generate_solution(
                    client, st.session_state["data_summary"], selected_problem
                )
                st.session_state["solution_md"] = sol_md
                st.session_state["answer_md"] = ans_md
                st.session_state["exec_code"] = None
                st.session_state["exec_stdout"] = None
                st.session_state["exec_result"] = None
                st.session_state["exec_error"] = None
                st.session_state["exec_traceback"] = None
                st.rerun()
            except Exception as e:
                st.error(f"풀이 생성 오류: {e}")

    # ── STEP 5: 결과 표시 및 다운로드 ────────────────────────
    if st.session_state["solution_md"] and st.session_state["answer_md"]:
        st.header("5단계: 풀이 결과 및 다운로드")

        render_result_visualizations(df, selected_problem)
        st.divider()

        tab1, tab2 = st.tabs(["📝 문제풀이.md", "✅ 해답.md"])
        with tab1:
            st.markdown(st.session_state["solution_md"])
        with tab2:
            st.markdown(st.session_state["answer_md"])

        st.divider()
        st.subheader("▶ 풀이 코드 실행")
        code_to_run = extract_python_code(st.session_state["solution_md"] or "")
        if not code_to_run:
            st.warning("문제풀이 내용에서 Python 코드 블록을 찾지 못했습니다.")
        else:
            st.code(code_to_run, language="python")

            if st.button("🚀 위 코드 실행하기", type="primary"):
                with st.spinner("풀이 코드를 실행 중입니다..."):
                    exec_result = execute_solution_code(code_to_run, df)
                    st.session_state["exec_code"] = code_to_run
                    st.session_state["exec_stdout"] = exec_result.get("stdout")
                    st.session_state["exec_result"] = exec_result.get("result_value")
                    st.session_state["exec_error"] = exec_result.get("error")
                    st.session_state["exec_traceback"] = exec_result.get("traceback")

            if st.session_state.get("exec_error"):
                st.error(f"코드 실행 오류: {st.session_state['exec_error']}")
                with st.expander("상세 에러 보기"):
                    st.code(st.session_state.get("exec_traceback", ""), language="text")
            else:
                if st.session_state.get("exec_result") is not None:
                    st.success(f"최종 결과값: {st.session_state['exec_result']}")
                if st.session_state.get("exec_stdout"):
                    st.text_area(
                        "실행 출력(stdout)",
                        st.session_state["exec_stdout"],
                        height=180,
                    )

        st.divider()
        st.subheader("📥 파일 다운로드")
        col_a, col_b = st.columns(2)

        with col_a:
            st.download_button(
                label="📝 문제풀이.md 다운로드",
                data=st.session_state["solution_md"].encode("utf-8"),
                file_name="문제풀이.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_b:
            st.download_button(
                label="✅ 해답.md 다운로드",
                data=st.session_state["answer_md"].encode("utf-8"),
                file_name="해답.md",
                mime="text/markdown",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
