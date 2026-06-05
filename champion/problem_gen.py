"""LLM 기반 문제 생성 및 도메인 추정 모듈"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from .profiler import DataProfile

# 5가지 고정 문제 유형 (순서 중요 - 번호와 파일명 연동)
PROBLEM_TYPE_DEFS = [
    {"id": "html_dashboard",  "name": "HTML 대시보드 제작",        "ext": "html", "file": "problem_01_dashboard.html"},
    {"id": "html_filter",     "name": "HTML 검색/필터 서비스 제작", "ext": "html", "file": "problem_02_filter_service.html"},
    {"id": "excel_vba",       "name": "Excel VBA 자동 보고서 생성","ext": "xlsm", "file": "problem_03_vba_report.xlsm"},
    {"id": "png_infographic", "name": "PNG 인포그래픽 제작",        "ext": "png",  "file": "problem_04_infographic.png"},
    {"id": "html_policy",     "name": "HTML 정책 제안 리포트 제작", "ext": "html", "file": "problem_05_policy_report.html"},
]


@dataclass
class RubricItem:
    criterion: str
    score: int
    description: str


@dataclass
class Problem:
    number: int
    type_id: str
    type_name: str
    title: str
    scenario: str
    requirements: list[str]
    submission_filename: str
    rubric: list[RubricItem]
    hint: str = ""
    total_score: int = 100


# ── 도메인 추정 ────────────────────────────────────────────────
_DOMAIN_SYSTEM = """당신은 데이터 분석 전문가입니다. 컬럼명과 샘플 데이터를 보고
공공행정 도메인(예: 범죄, 보건, 환경, 교육, 교통, 사회복지, 재정, 인구 등)을
한 줄로 추정합니다. 반드시 단어 1~3개로만 응답합니다."""


def estimate_domain(client: genai.Client, model: str, profile: DataProfile) -> str:
    prompt = f"다음 데이터셋의 공공행정 도메인을 추정해줘:\n{profile.summary_text[:800]}"
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_DOMAIN_SYSTEM,
            temperature=0.2,
            max_output_tokens=30,
        ),
    )
    return (resp.text or "공공행정").strip().replace("\n", " ")


# ── 문제 생성 ──────────────────────────────────────────────────
_PROBLEM_SYSTEM = """당신은 공공기관 AI 역량평가 전문 출제 위원입니다.
제공된 데이터셋을 기반으로 공공행정 시나리오가 포함된 데이터분석 실습 문제 5개를 생성합니다.
반드시 JSON 배열 형식으로만 응답하며 코드블록이나 다른 텍스트는 포함하지 않습니다."""


def _build_problem_prompt(profile: DataProfile, domain: str) -> str:
    col_list = ", ".join(
        f"{c.name}({c.category})" for c in profile.columns
    )
    return f"""다음 공공 데이터셋을 기반으로 AI챔피언 그린 수준의 데이터분석 실습 문제 5개를 생성하라.

[데이터셋 정보]
{profile.summary_text[:1500]}

추정 도메인: {domain}
컬럼 구성: {col_list}

[출제 조건]
1. 시험자는 AI(ChatGPT 등) 사용이 허용된다
2. 결과물 파일(HTML/Excel/PNG) 중심 채점 문제다
3. 채점자가 파일을 열어보면 즉시 채점 가능해야 한다
4. 공공행정 업무 맥락의 시나리오가 포함되어야 한다

[문제 유형 (반드시 순서대로, 각 1개씩)]
1번: HTML 대시보드 제작 → 제출파일: problem_01_dashboard.html
2번: HTML 검색/필터 서비스 제작 → 제출파일: problem_02_filter_service.html
3번: Excel VBA 자동 보고서 생성 → 제출파일: problem_03_vba_report.xlsm
4번: PNG 인포그래픽 제작 → 제출파일: problem_04_infographic.png
5번: HTML 정책 제안 리포트 제작 → 제출파일: problem_05_policy_report.html

JSON 배열 형식으로만 응답:
[
  {{
    "number": 1,
    "type_id": "html_dashboard",
    "type_name": "HTML 대시보드 제작",
    "title": "구체적인 문제 제목 (데이터 내용 반영)",
    "scenario": "담당자 역할·업무 배경·목적·보고 대상을 포함한 공공행정 시나리오 (3~4문장)",
    "requirements": [
      "필수 구현 항목 1 (정확한 컬럼명 사용)",
      "필수 구현 항목 2",
      "필수 구현 항목 3",
      "필수 구현 항목 4",
      "필수 구현 항목 5"
    ],
    "submission_filename": "problem_01_dashboard.html",
    "rubric": [
      {{"criterion": "채점 항목명", "score": 20, "description": "구체적이고 객관적인 채점 기준"}},
      {{"criterion": "채점 항목명", "score": 20, "description": "구체적이고 객관적인 채점 기준"}},
      {{"criterion": "채점 항목명", "score": 20, "description": "구체적이고 객관적인 채점 기준"}},
      {{"criterion": "채점 항목명", "score": 20, "description": "구체적이고 객관적인 채점 기준"}},
      {{"criterion": "채점 항목명", "score": 20, "description": "구체적이고 객관적인 채점 기준"}}
    ],
    "hint": "AI 프롬프트 활용 힌트 1~2줄"
  }},
  ... (2~5번 문제도 동일 형식)
]

절대 규칙:
- requirements의 컬럼명은 실제 데이터셋 컬럼명과 정확히 일치
- rubric 항목 score 합계는 반드시 100
- 1번과 5번 문제의 type_id는 각각 html_dashboard, html_policy로 고정
- 3번 문제의 type_id는 excel_vba로 고정
- 4번 문제의 type_id는 png_infographic으로 고정"""


def _parse_raw(raw: str) -> list[dict]:
    raw = re.sub(r"^```[a-z]*\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw.strip())
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    for v in parsed.values():
        if isinstance(v, list):
            return v
    raise ValueError("JSON 배열을 찾을 수 없음")


def _validate(items: list[dict]) -> tuple[bool, str]:
    if len(items) != 5:
        return False, f"문제 수 {len(items)}개 (5개 필요)"
    type_ids = [it.get("type_id") for it in items]
    required = ["html_dashboard", "html_filter", "excel_vba", "png_infographic", "html_policy"]
    missing = [t for t in required if t not in type_ids]
    if missing:
        return False, f"누락된 유형: {missing}"
    for i, it in enumerate(items, 1):
        rubric = it.get("rubric", [])
        total = sum(r.get("score", 0) for r in rubric)
        if total != 100:
            return False, f"문제 {i} rubric 합계 {total} (100 필요)"
    return True, "ok"


def generate_problems(
    client: genai.Client,
    model: str,
    profile: DataProfile,
    domain: str,
) -> list[Problem]:
    prompt = _build_problem_prompt(profile, domain)
    last_error = ""

    for attempt in range(3):
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_PROBLEM_SYSTEM,
                response_mime_type="application/json",
                temperature=0.5,
            ),
        )
        raw = (resp.text or "").strip()
        try:
            items = _parse_raw(raw)
            ok, reason = _validate(items)
            if not ok:
                raise ValueError(reason)
            problems = []
            for it in items:
                rubric = [
                    RubricItem(
                        criterion=r["criterion"],
                        score=int(r["score"]),
                        description=r.get("description", ""),
                    )
                    for r in it.get("rubric", [])
                ]
                problems.append(Problem(
                    number=it["number"],
                    type_id=it["type_id"],
                    type_name=it["type_name"],
                    title=it["title"],
                    scenario=it["scenario"],
                    requirements=it.get("requirements", []),
                    submission_filename=it["submission_filename"],
                    rubric=rubric,
                    hint=it.get("hint", ""),
                ))
            return problems
        except Exception as exc:
            last_error = str(exc)
            prompt += f"\n\n[재시도 {attempt+1}] 이전 실패 원인: {last_error}. JSON 배열만 다시 출력."

    raise ValueError(f"문제 생성 최종 실패: {last_error}")
