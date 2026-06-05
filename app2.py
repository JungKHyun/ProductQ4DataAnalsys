"""
데이터 분석 교육용 문제 제작 웹 애플리케이션 v2
- CSV 업로드 → 10가지 유형 선택(1~5개) → LLM 문제 생성 → 풀이·해답·차트 다운로드
"""

import io
import json
import os
import re
import textwrap
import traceback
import zipfile
from contextlib import redirect_stdout

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ── 한글 폰트 설정 (Windows 우선) ───────────────────────────
def _set_korean_font():
    candidates = ["Malgun Gothic", "NanumGothic", "AppleGothic", "DejaVu Sans"]
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False

_set_korean_font()
plt.show = lambda *a, **k: None  # Streamlit 환경에서 plt.show() 차단

# ── Streamlit 페이지 설정 ────────────────────────────────────
st.set_page_config(
    page_title="데이터 분석 문제 생성기",
    page_icon="📊",
    layout="wide",
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
MAX_SAMPLE_ROWS = 5
MAX_PROFILE_ROWS = 10_000

# ── 10가지 문제 유형 정의 ─────────────────────────────────────
PROBLEM_TYPES: dict[int, dict] = {
    1: {
        "name": "기술통계",
        "desc": "수치형 변수의 평균·중앙값·표준편차·최솟값·최댓값 등 기초 통계 계산",
        "chart_required": False,
    },
    2: {
        "name": "빈도수 측정",
        "desc": "범주형 변수의 항목별 빈도수(개수·비율)를 측정하고 최빈값 파악",
        "chart_required": True,
        "chart_type": "막대차트",
    },
    3: {
        "name": "상관관계 분석",
        "desc": "두 연속형 변수 사이의 피어슨/스피어만 상관계수 계산",
        "chart_required": True,
        "chart_type": "산점도",
    },
    4: {
        "name": "분포 시각화",
        "desc": "수치형 변수의 분포를 히스토그램/KDE로 시각화하고 왜도·첨도 파악",
        "chart_required": True,
        "chart_type": "히스토그램",
    },
    5: {
        "name": "그룹별 비교",
        "desc": "범주형 변수로 그룹을 나누어 수치형 변수의 분포를 박스플롯으로 비교",
        "chart_required": True,
        "chart_type": "박스플롯",
    },
    6: {
        "name": "집계 막대차트",
        "desc": "그룹별 합계·평균을 막대차트로 시각화하고 최대·최소 그룹 파악",
        "chart_required": True,
        "chart_type": "막대차트",
    },
    7: {
        "name": "이상치 탐지",
        "desc": "IQR 방법으로 수치형 변수의 이상치 개수·비율을 측정하고 박스플롯으로 시각화",
        "chart_required": True,
        "chart_type": "박스플롯",
    },
    8: {
        "name": "시계열 추이",
        "desc": "날짜·시간 컬럼이 있을 때 시간에 따른 수치 변화를 선 그래프로 시각화",
        "chart_required": True,
        "chart_type": "선 그래프",
    },
    9: {
        "name": "순위 분석",
        "desc": "특정 기준으로 정렬하여 상위 N개·하위 N개 항목을 수평 막대차트로 표시",
        "chart_required": True,
        "chart_type": "수평 막대차트",
    },
    10: {
        "name": "비율 파이차트",
        "desc": "전체 대비 범주별 비율(%)을 계산하고 파이/도넛 차트로 시각화",
        "chart_required": True,
        "chart_type": "파이차트",
    },
}

TYPE_EMOJI = {
    "기술통계": "📈", "빈도수 측정": "📊", "상관관계 분석": "🔗",
    "분포 시각화": "📉", "그룹별 비교": "⚖️", "집계 막대차트": "🏆",
    "이상치 탐지": "🔍", "시계열 추이": "📅", "순위 분석": "🥇",
    "비율 파이차트": "🥧",
}


# ── Gemini 클라이언트 ────────────────────────────────────────
@st.cache_resource
def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error(
            "GEMINI_API_KEY가 설정되지 않았습니다. "
            ".env 파일에 GEMINI_API_KEY=... 를 추가하거나 "
            "PowerShell에서 $env:GEMINI_API_KEY=... 설정 후 재실행하세요."
        )
        st.stop()
    return genai.Client(api_key=api_key)


# ── 데이터 로딩 ──────────────────────────────────────────────
def load_dataframe(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file, encoding="utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="cp949")
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("CSV 또는 XLSX 파일만 지원합니다.")


# ── 데이터 요약 (LLM 프롬프트용) ────────────────────────────
def build_data_summary(df: pd.DataFrame) -> str:
    col_info = []
    for col in df.columns:
        null_pct = df[col].isna().mean() * 100
        col_info.append(
            f"  - {col} (타입: {df[col].dtype}, 결측률: {null_pct:.1f}%, 고유값: {df[col].nunique()}개)"
        )
    num_cols = df.select_dtypes(include="number")
    stats = num_cols.describe().round(3).to_string() if not num_cols.empty else "(수치형 컬럼 없음)"
    return textwrap.dedent(f"""
    [데이터셋 기본 정보]
    - 행 수: {len(df):,}
    - 열 수: {len(df.columns)}

    [컬럼 정보]
    {chr(10).join(col_info)}

    [수치형 컬럼 요약 통계]
    {stats}

    [샘플 데이터 (상위 {MAX_SAMPLE_ROWS}행)]
    {df.head(MAX_SAMPLE_ROWS).to_csv(index=False)}
    """).strip()


# ── 데이터 프로파일링 렌더링 ─────────────────────────────────
def render_profile(df: pd.DataFrame):
    st.subheader("📋 데이터 개요")
    col1, col2, col3 = st.columns(3)
    col1.metric("전체 행 수", f"{len(df):,}")
    col2.metric("전체 열 수", len(df.columns))
    col3.metric("결측치 비율", f"{df.isna().mean().mean() * 100:.1f}%")

    with st.expander("상위 5행 미리보기", expanded=True):
        st.dataframe(df.head(), use_container_width=True)

    with st.expander("컬럼 정보 (타입 / 결측 / 고유값)"):
        st.dataframe(
            pd.DataFrame({
                "컬럼명": df.columns,
                "데이터 타입": df.dtypes.values,
                "결측치 수": df.isna().sum().values,
                "결측률 (%)": (df.isna().mean() * 100).round(1).values,
                "고유값 수": df.nunique().values,
            }),
            use_container_width=True,
        )

    with st.expander("수치형 컬럼 요약 통계"):
        num_df = df.select_dtypes(include="number")
        if not num_df.empty:
            st.dataframe(num_df.describe().round(3), use_container_width=True)
        else:
            st.info("수치형 컬럼이 없습니다.")


# ── LLM: 문제 생성 ───────────────────────────────────────────
_PROBLEM_SYSTEM = """당신은 데이터 분석 교육 전문가입니다.
주어진 데이터셋과 선택된 문제 유형에 맞춰 학습자가 실제로 풀 수 있는
현실적이고 평가하기 쉬운 문제를 출제합니다.
반드시 JSON 배열 형식으로만 응답하며, 코드블록이나 다른 텍스트는 포함하지 않습니다."""


def _build_problem_prompt(data_summary: str, selected_types: list[dict]) -> str:
    type_lines = "\n".join(
        f"{i+1}. 유형명: \"{t['name']}\" — {t['desc']}"
        for i, t in enumerate(selected_types)
    )
    n = len(selected_types)
    return f"""제공된 데이터셋 정보는 다음과 같다:

{data_summary}

다음 {n}가지 분석 유형에 맞춰 각각 1개씩 총 {n}개의 문제를 출제해줘:
{type_lines}

반드시 아래 JSON 배열 형식으로만 응답해:
[
  {{
    "번호": 1,
    "유형": "유형명 (위 목록의 정확한 유형명 사용)",
    "제목": "짧고 명확한 문제 제목",
    "내용": "어떤 컬럼을 사용해 무엇을 계산/시각화하는지 구체적으로 기술",
    "평가기준": "숫자 1개로 채점 가능한 기준 (허용 오차·반올림 규칙 포함)",
    "정답형식": "숫자 1개 (예: 소수점 둘째 자리 반올림)",
    "시각화요구": "차트가 필요하면 '차트종류, x축=컬럼명, y축=컬럼명' 형식으로 명시; 차트 불필요면 '없음'",
    "python_hint": "pandas/matplotlib/seaborn 핵심 함수 힌트 1~2개"
  }},
  ...
]

절대 지켜야 할 규칙:
1) 모든 문제의 최종 정답은 숫자 1개여야 한다.
2) 문제 내용에서 사용할 컬럼명을 데이터셋에 실제 존재하는 이름으로 명시한다.
3) 차트가 필요한 유형은 시각화요구에 차트 종류·x축·y축을 반드시 명시한다.
4) 차트 문제도 최종 채점 기준은 숫자 1개 (예: 최댓값, 최빈 카테고리의 빈도수 등)이어야 한다.
5) 평가기준에는 허용 오차(예: ±0.01)와 반올림 규칙을 명시한다."""


def _parse_json_problems(raw: str) -> list[dict]:
    raw = re.sub(r"^```[a-z]*\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw.strip())
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    for v in parsed.values():
        if isinstance(v, list):
            return v
    raise ValueError("예상치 못한 JSON 구조")


def generate_problems(
    client: genai.Client,
    data_summary: str,
    selected_types: list[dict],
) -> list[dict]:
    prompt = _build_problem_prompt(data_summary, selected_types)
    last_error = ""
    for _ in range(3):
        resp = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_PROBLEM_SYSTEM,
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        raw = (resp.text or "").strip()
        try:
            return _parse_json_problems(raw)
        except Exception as e:
            last_error = str(e)
            prompt += f"\n\n이전 응답이 JSON 파싱 불가 (오류: {e}). JSON 배열만 다시 출력해."
    raise ValueError(f"문제 생성 실패: {last_error}")


# ── LLM: 풀이·해답 생성 ─────────────────────────────────────
_SOLUTION_SYSTEM = """당신은 데이터 분석 및 Python 프로그래밍 전문가입니다.
주어진 문제에 대해 실제로 실행 가능한 풀이 코드와 명확한 해답을 제공합니다.

코드 작성 규칙:
- `df` 변수가 이미 로드되어 있다고 가정한다.
- pandas, numpy, matplotlib, seaborn만 사용한다.
- 차트가 필요하면 matplotlib/seaborn으로 그리고, plt.show()는 호출하지 않는다.
- 최종 정답 숫자는 반드시 `final_answer = <숫자>` 형태로 코드 마지막에 저장한다.
- plt.savefig() 는 호출하지 않는다 (시스템이 자동 캡처한다)."""


def _build_solution_prompt(data_summary: str, problem: dict) -> str:
    return f"""아래 데이터셋 정보와 분석 문제를 해결해줘.

[데이터셋 정보]
{data_summary}

[선택된 문제]
유형: {problem.get("유형", "")}
제목: {problem.get("제목", "")}
내용: {problem.get("내용", "")}
시각화요구: {problem.get("시각화요구", "없음")}
평가기준: {problem.get("평가기준", "")}
Python 힌트: {problem.get("python_hint", "")}

다음 두 섹션을 마크다운으로 작성해줘. 각 섹션 앞에 구분자를 반드시 넣어줘.

===문제풀이===
# [{problem.get("유형", "")}] {problem.get("제목", "")}

## 1. 분석 접근 방향
(분석 전략 설명)

## 2. Python 풀이 코드
```python
# df 변수가 이미 로드되어 있다고 가정
# 최종 정답은 반드시 final_answer = <숫자> 형태로 저장
# 차트가 필요하면 matplotlib/seaborn으로 그리기 (plt.show() / plt.savefig() 호출 금지)
```

## 3. 코드 설명 및 인사이트
(코드 각 단계 설명과 분석 결과 인사이트)

===해답===
# 문제 최종 해답

## 예상 정답
- **final_answer**: (계산된 최종 정답 숫자와 단위)
- **해석**: (이 숫자의 데이터 분석적 의미)
- **평가 기준 충족**: (허용 오차 범위 내인지 확인)

## 비즈니스 시사점
(이 분석 결과가 실무에서 갖는 의미)
"""


def generate_solution(
    client: genai.Client,
    data_summary: str,
    problem: dict,
) -> tuple[str, str]:
    resp = client.models.generate_content(
        model=MODEL,
        contents=_build_solution_prompt(data_summary, problem),
        config=types.GenerateContentConfig(
            system_instruction=_SOLUTION_SYSTEM,
            temperature=0.3,
            max_output_tokens=4096,
        ),
    )
    raw = (resp.text or "").strip()
    if "===문제풀이===" in raw and "===해답===" in raw:
        parts = raw.split("===해답===")
        sol = parts[0].replace("===문제풀이===", "").strip()
        ans = parts[1].strip()
    else:
        sol = raw
        ans = "# 문제 최종 해답\n\n(LLM 응답 구조를 확인해 주세요.)"
    return sol, ans


def extract_python_code(md: str) -> str:
    m = re.search(r"```python\s*(.*?)```", md, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*(.*?)```", md, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


# ── 풀이 코드 실행 (차트 자동 캡처) ─────────────────────────
def execute_solution_code(code: str, df: pd.DataFrame) -> dict:
    """풀이 코드 실행 후 stdout·final_answer·차트 PNG bytes 반환."""
    plt.close("all")

    local_env: dict = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
    }
    stdout_buf = io.StringIO()

    try:
        with redirect_stdout(stdout_buf):
            exec(code, {"__builtins__": __builtins__}, local_env)  # noqa: S102

        # 차트 캡처: 실행 후 열려 있는 figure가 있으면 PNG로 저장
        chart_bytes: bytes | None = None
        fignums = plt.get_fignums()
        if fignums:
            buf = io.BytesIO()
            plt.figure(fignums[-1])
            plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            buf.seek(0)
            chart_bytes = buf.getvalue()

        result_value = local_env.get("final_answer")
        if result_value is None:
            for k in ("answer", "result", "final_value", "score", "metric"):
                if k in local_env:
                    result_value = local_env[k]
                    break

        return {
            "ok": True,
            "stdout": stdout_buf.getvalue().strip(),
            "result_value": result_value,
            "chart_bytes": chart_bytes,
            "error": "",
            "traceback": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": stdout_buf.getvalue().strip(),
            "result_value": None,
            "chart_bytes": None,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        plt.close("all")


# ── ZIP 패키징 ────────────────────────────────────────────────
def build_zip(problems: list[dict], solutions: dict) -> bytes:
    buf = io.BytesIO()
    all_sol_md = ""
    all_ans_md = ""

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in problems:
            num = p.get("번호")
            sol = solutions.get(num, {})
            title = p.get("제목", f"문제{num}")

            if sol.get("solution_md"):
                zf.writestr(f"문제{num}_문제풀이.md", sol["solution_md"])
                all_sol_md += f"\n\n---\n\n# 문제 {num}: {title}\n\n{sol['solution_md']}"

            if sol.get("answer_md"):
                zf.writestr(f"문제{num}_해답.md", sol["answer_md"])
                all_ans_md += f"\n\n---\n\n# 문제 {num}: {title}\n\n{sol['answer_md']}"

            if sol.get("chart_bytes"):
                zf.writestr(f"문제{num}_차트.png", sol["chart_bytes"])

        if all_sol_md:
            zf.writestr("전체_문제풀이.md", all_sol_md.strip())
        if all_ans_md:
            zf.writestr("전체_해답.md", all_ans_md.strip())

    buf.seek(0)
    return buf.getvalue()


# ── 세션 초기화 ───────────────────────────────────────────────
def init_session():
    defaults = {
        "_last_filename": None,
        "df": None,
        "data_summary": None,
        "problems": None,
        "solutions": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── 메인 앱 ──────────────────────────────────────────────────
def main():
    init_session()
    client = get_client()

    st.title("📊 데이터 분석 문제 생성기")
    st.caption(
        "CSV 업로드 → 10가지 유형 중 선택(1~5개) → AI 문제 생성 "
        "→ 풀이·해답.md·차트 이미지 다운로드"
    )

    # ── 1단계: 파일 업로드 ───────────────────────────────────
    st.header("1단계: CSV 파일 업로드")
    uploaded = st.file_uploader(
        "CSV 또는 XLSX 파일을 선택하세요",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded is not None:
        if st.session_state["_last_filename"] != uploaded.name:
            st.session_state.update({
                "_last_filename": uploaded.name,
                "df": None,
                "data_summary": None,
                "problems": None,
                "solutions": {},
            })
        if st.session_state["df"] is None:
            with st.spinner("파일을 읽는 중..."):
                try:
                    df = load_dataframe(uploaded)
                    st.session_state["df"] = df
                    st.session_state["data_summary"] = build_data_summary(
                        df.head(MAX_PROFILE_ROWS)
                    )
                    st.success(f"✅ '{uploaded.name}' 로드 완료  ({len(df):,}행 × {len(df.columns)}열)")
                except Exception as e:
                    st.error(f"파일 읽기 오류: {e}")
                    st.stop()

    if st.session_state["df"] is None:
        st.info("👆 파일을 업로드하면 분석이 시작됩니다.")
        return

    df: pd.DataFrame = st.session_state["df"]

    # ── 2단계: 데이터 프로파일링 ────────────────────────────
    st.header("2단계: 데이터 프로파일링")
    render_profile(df)

    # ── 3단계: 문제 유형 선택 ───────────────────────────────
    st.header("3단계: 문제 유형 선택 (1~5개)")
    st.caption(
        "아래 10가지 분석 유형 중 원하는 유형을 1~5개 선택하면 "
        "AI가 각 유형에 맞는 문제를 1개씩 생성합니다."
    )

    type_options = {
        f"{k}. **{v['name']}** — {v['desc']}": k
        for k, v in PROBLEM_TYPES.items()
    }
    selected_labels: list[str] = st.multiselect(
        "분석 유형 선택 (최소 1개, 최대 5개)",
        options=list(type_options.keys()),
        max_selections=5,
        key="type_multiselect",
        format_func=lambda x: x,
    )
    selected_keys = [type_options[lbl] for lbl in selected_labels]

    if not selected_keys:
        st.info("👆 문제 유형을 1~5개 선택해 주세요.")
        return

    selected_types = [PROBLEM_TYPES[k] for k in selected_keys]
    st.success(f"선택된 유형 ({len(selected_types)}개): " + " | ".join(
        f"{TYPE_EMOJI.get(t['name'], '📌')} {t['name']}" for t in selected_types
    ))

    # ── 4단계: 문제 생성 ────────────────────────────────────
    st.header("4단계: AI 문제 생성")
    col_gen, col_regen = st.columns(2)
    with col_gen:
        gen_disabled = st.session_state["problems"] is not None
        if st.button("🤖 문제 생성하기", type="primary", disabled=gen_disabled):
            with st.spinner("AI가 데이터를 분석하여 문제를 생성하는 중입니다..."):
                try:
                    problems = generate_problems(
                        client, st.session_state["data_summary"], selected_types
                    )
                    st.session_state["problems"] = problems
                    st.session_state["solutions"] = {}
                    st.rerun()
                except Exception as e:
                    st.error(f"문제 생성 오류: {e}")
    with col_regen:
        if st.button("🔄 문제 다시 생성하기"):
            st.session_state["problems"] = None
            st.session_state["solutions"] = {}
            st.rerun()

    problems: list[dict] | None = st.session_state["problems"]
    if not problems:
        return

    # 문제 목록 표시
    st.subheader("생성된 문제 목록")
    for p in problems:
        emoji = TYPE_EMOJI.get(p.get("유형", ""), "📌")
        with st.container(border=True):
            st.markdown(
                f"**{emoji} 문제 {p.get('번호', '?')}. "
                f"[{p.get('유형', '')}] {p.get('제목', '')}**"
            )
            st.write(p.get("내용", ""))
            c1, c2, c3 = st.columns(3)
            viz = p.get("시각화요구", "없음")
            if viz and viz != "없음":
                c1.caption(f"📊 시각화: {viz}")
            if p.get("정답형식"):
                c2.caption(f"📝 정답형식: {p.get('정답형식')}")
            if p.get("평가기준"):
                c3.caption(f"✅ 평가기준: {p.get('평가기준')}")

    # ── 5단계: 문제별 풀이 생성 및 다운로드 ─────────────────
    st.header("5단계: 풀이 생성 및 다운로드")
    st.caption("각 문제의 '풀이 생성' 버튼을 클릭하면 Python 코드를 자동 실행해 차트와 해답을 만듭니다.")

    solutions: dict = st.session_state["solutions"]

    for p in problems:
        num = p.get("번호")
        emoji = TYPE_EMOJI.get(p.get("유형", ""), "📌")
        label = f"{emoji} 문제 {num}. [{p.get('유형', '')}] {p.get('제목', '')}"

        with st.expander(label, expanded=False):
            sol = solutions.get(num, {})

            if not sol.get("solution_md"):
                if st.button(f"✏️ 문제 {num} 풀이 생성", key=f"gen_{num}", type="primary"):
                    with st.spinner(f"문제 {num} 풀이 코드와 해답을 생성 중..."):
                        try:
                            sol_md, ans_md = generate_solution(
                                client, st.session_state["data_summary"], p
                            )
                            code = extract_python_code(sol_md)
                            exec_res: dict = {}
                            if code:
                                exec_res = execute_solution_code(code, df)
                            solutions[num] = {
                                "solution_md": sol_md,
                                "answer_md": ans_md,
                                "chart_bytes": exec_res.get("chart_bytes"),
                                "code": code,
                                "exec_result": exec_res,
                            }
                            st.session_state["solutions"] = solutions
                            st.rerun()
                        except Exception as e:
                            st.error(f"풀이 생성 오류: {e}")
            else:
                tab_sol, tab_ans, tab_chart = st.tabs(["📝 문제풀이", "✅ 해답", "📊 차트"])

                with tab_sol:
                    st.markdown(sol["solution_md"])

                    # 추출된 코드 표시 + 실행 버튼
                    code = sol.get("code", "")
                    if code:
                        st.divider()
                        st.subheader("▶ 풀이 코드 실행")
                        st.code(code, language="python")
                        if st.button(f"🚀 코드 실행하기", key=f"run_{num}", type="primary"):
                            with st.spinner("코드를 실행하는 중..."):
                                new_exec = execute_solution_code(code, df)
                                solutions[num]["chart_bytes"] = new_exec.get("chart_bytes")
                                solutions[num]["exec_result"] = new_exec
                                st.session_state["solutions"] = solutions
                                st.rerun()

                        exec_res = sol.get("exec_result", {})
                        if exec_res.get("ok"):
                            if exec_res.get("result_value") is not None:
                                st.success(f"🎯 **final_answer = {exec_res['result_value']}**")
                            if exec_res.get("stdout"):
                                st.text_area("실행 출력(stdout)", exec_res["stdout"], height=130, key=f"run_out_{num}")
                        elif exec_res.get("error"):
                            st.error(f"실행 오류: {exec_res['error']}")
                            with st.expander("에러 상세 보기"):
                                st.code(exec_res.get("traceback", ""), language="text")

                    st.divider()
                    st.download_button(
                        label=f"📥 문제{num}_문제풀이.md 다운로드",
                        data=sol["solution_md"].encode("utf-8"),
                        file_name=f"문제{num}_문제풀이.md",
                        mime="text/markdown",
                        key=f"dl_sol_{num}",
                        use_container_width=True,
                    )

                with tab_ans:
                    st.markdown(sol["answer_md"])
                    exec_res = sol.get("exec_result", {})
                    if exec_res.get("result_value") is not None:
                        st.success(f"🎯 실행된 final_answer = **{exec_res['result_value']}**")
                    if exec_res.get("stdout"):
                        st.text_area("실행 출력", exec_res["stdout"], height=120, key=f"stdout_{num}")
                    st.download_button(
                        label=f"📥 문제{num}_해답.md 다운로드",
                        data=sol["answer_md"].encode("utf-8"),
                        file_name=f"문제{num}_해답.md",
                        mime="text/markdown",
                        key=f"dl_ans_{num}",
                        use_container_width=True,
                    )

                with tab_chart:
                    chart_bytes = sol.get("chart_bytes")
                    exec_res = sol.get("exec_result", {})
                    if chart_bytes:
                        st.image(chart_bytes, caption=f"문제 {num} 차트", use_container_width=True)
                        st.download_button(
                            label=f"📥 문제{num}_차트.png 다운로드",
                            data=chart_bytes,
                            file_name=f"문제{num}_차트.png",
                            mime="image/png",
                            key=f"dl_chart_{num}",
                            use_container_width=True,
                        )
                    elif exec_res.get("error"):
                        st.error(f"코드 실행 오류: {exec_res['error']}")
                        with st.expander("에러 상세 보기"):
                            st.code(exec_res.get("traceback", ""), language="text")
                    else:
                        st.info("이 문제 유형에는 차트가 없습니다.")

                if st.button(f"🔄 문제 {num} 풀이 재생성", key=f"regen_{num}"):
                    solutions.pop(num, None)
                    st.session_state["solutions"] = solutions
                    st.rerun()

    # ── 전체 ZIP 다운로드 ────────────────────────────────────
    solved = [p for p in problems if solutions.get(p.get("번호"), {}).get("solution_md")]
    if solved:
        st.divider()
        st.subheader("📦 전체 패키지 ZIP 다운로드")
        st.caption(
            f"풀이 완료된 {len(solved)}개 문제의 문제풀이.md, 해답.md, 차트.png를 "
            "하나의 ZIP으로 다운로드합니다."
        )
        zip_bytes = build_zip(problems, solutions)
        st.download_button(
            label="📥 전체 (문제풀이 + 해답 + 차트) ZIP 다운로드",
            data=zip_bytes,
            file_name="데이터분석_문제풀이_패키지.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
