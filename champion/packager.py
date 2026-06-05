"""산출물 ZIP 패키징 및 문제지 HTML 생성 모듈"""
from __future__ import annotations
import io
import json
import zipfile

from .problem_gen import Problem


def build_problems_html(problems: list[Problem]) -> str:
    """전체 문제지 단일 HTML 파일 생성"""
    type_colors = {
        "html_dashboard": "#0366d6",
        "html_filter": "#28a745",
        "excel_vba": "#6f42c1",
        "png_infographic": "#e36209",
        "html_policy": "#d73a49",
    }
    type_icons = {
        "html_dashboard": "📊",
        "html_filter": "🔍",
        "excel_vba": "📋",
        "png_infographic": "🎨",
        "html_policy": "📝",
    }

    blocks = []
    for p in problems:
        color = type_colors.get(p.type_id, "#333")
        icon = type_icons.get(p.type_id, "📌")
        reqs_html = "".join(f"<li>{r}</li>" for r in p.requirements)
        rubric_html = "".join(
            f"""<tr>
              <td class="item">{ri.criterion}</td>
              <td class="pts">{ri.score}점</td>
              <td class="desc">{ri.description}</td>
            </tr>"""
            for ri in p.rubric
        )
        hint_html = (
            f'<div class="hint-box"><span class="hint-label">💡 AI 활용 힌트</span> {p.hint}</div>'
            if p.hint else ""
        )
        blocks.append(f"""
<section class="problem" id="p{p.number}">
  <div class="p-header" style="border-left-color:{color}">
    <div class="p-meta">
      <span class="badge" style="background:{color}">{icon} 문제 {p.number}</span>
      <span class="type-tag" style="color:{color}">{p.type_name}</span>
    </div>
    <h2 class="p-title">{p.title}</h2>
  </div>
  <div class="p-body">
    <div class="section">
      <h3>📋 업무 시나리오</h3>
      <p class="scenario-text">{p.scenario}</p>
    </div>
    <div class="section">
      <h3>✅ 필수 구현 사항</h3>
      <ol class="req-list">{reqs_html}</ol>
    </div>
    <div class="section submit-section">
      <h3>📁 제출 파일</h3>
      <code class="filename" style="border-color:{color};color:{color}">{p.submission_filename}</code>
    </div>
    <div class="section">
      <h3>📊 채점 기준 <span class="total-score">총 100점</span></h3>
      <table class="rubric">
        <thead><tr><th>채점 항목</th><th>배점</th><th>세부 기준</th></tr></thead>
        <tbody>{rubric_html}</tbody>
      </table>
    </div>
    {hint_html}
  </div>
</section>""")

    toc_items = "".join(
        f'<li><a href="#p{p.number}">{type_icons.get(p.type_id,"📌")} 문제 {p.number}. {p.title[:30]}{"…" if len(p.title)>30 else ""}</a></li>'
        for p in problems
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AI챔피언 데이터분석 문제지</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;background:#f4f7fb;color:#24292f;line-height:1.6}}
.hero{{background:linear-gradient(135deg,#1a3a5c 0%,#2980b9 100%);color:#fff;padding:48px 24px;text-align:center}}
.hero h1{{font-size:2rem;margin-bottom:8px;letter-spacing:-0.5px}}
.hero .meta{{opacity:.85;font-size:.95rem;margin-top:6px}}
.hero .warn{{margin-top:14px;background:rgba(255,255,255,.15);display:inline-block;padding:6px 20px;border-radius:20px;font-size:.85rem}}
.container{{max-width:960px;margin:32px auto;padding:0 20px}}
.toc{{background:#fff;border-radius:10px;padding:20px 28px;margin-bottom:28px;box-shadow:0 1px 6px rgba(0,0,0,.08)}}
.toc h2{{font-size:1rem;color:#57606a;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}}
.toc ol{{padding-left:20px}}
.toc li{{margin:6px 0}}
.toc a{{color:#0969da;text-decoration:none}}
.toc a:hover{{text-decoration:underline}}
.problem{{background:#fff;border-radius:10px;margin-bottom:28px;box-shadow:0 1px 8px rgba(0,0,0,.09);overflow:hidden}}
.p-header{{padding:22px 28px 18px;border-left:6px solid #2980b9;background:#fafbfc}}
.p-meta{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.badge{{padding:3px 14px;border-radius:20px;color:#fff;font-weight:bold;font-size:.85rem}}
.type-tag{{font-size:.9rem;font-weight:600}}
.p-title{{font-size:1.35rem;color:#1a3a5c;font-weight:700}}
.p-body{{padding:24px 28px}}
.section{{margin-bottom:22px}}
h3{{font-size:.95rem;color:#57606a;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #eaecef;text-transform:none;letter-spacing:0}}
.scenario-text{{background:#f8f9fa;border-left:3px solid #d0d7de;padding:14px 16px;border-radius:0 6px 6px 0;color:#444;font-size:.95rem}}
.req-list{{padding-left:22px}}
.req-list li{{margin:7px 0;font-size:.95rem;color:#333}}
.submit-section{{}}
.filename{{display:inline-block;padding:8px 18px;border:2px solid;border-radius:6px;font-size:1rem;font-weight:bold;background:#f8f9fa;letter-spacing:.3px}}
.total-score{{font-weight:normal;font-size:.85rem;color:#6e7781;margin-left:8px;background:#eaecef;padding:2px 10px;border-radius:12px}}
.rubric{{width:100%;border-collapse:collapse;font-size:.9rem}}
.rubric th{{background:#1a3a5c;color:#fff;padding:9px 12px;text-align:left}}
.rubric td{{padding:9px 12px;border-bottom:1px solid #eaecef}}
.rubric tr:last-child td{{border-bottom:none}}
.rubric tr:hover{{background:#f0f7ff}}
.rubric .pts{{text-align:center;font-weight:bold;color:#e74c3c;white-space:nowrap}}
.rubric .item{{font-weight:600}}
.rubric .desc{{color:#555}}
.hint-box{{background:#fff9e6;border:1px solid #f0b429;border-radius:8px;padding:14px 18px;font-size:.9rem;color:#735c00}}
.hint-label{{font-weight:bold;margin-right:6px}}
.footer{{text-align:center;padding:32px 0 48px;color:#8c959f;font-size:.85rem}}
@media print{{
  .problem{{page-break-inside:avoid;box-shadow:none;border:1px solid #ddd}}
  .hero{{background:#1a3a5c !important;-webkit-print-color-adjust:exact}}
}}
</style>
</head>
<body>
<div class="hero">
  <h1>🏆 AI챔피언 데이터분석 실습 문제지</h1>
  <div class="meta">총 {len(problems)}문제 | 500점 만점 | 합격 기준 350점 이상</div>
  <div class="warn">⚡ AI(ChatGPT 등) 사용 허용 시험 | 제출물: HTML · Excel · PNG 파일</div>
</div>
<div class="container">
  <div class="toc">
    <h2>목차</h2>
    <ol>{toc_items}</ol>
  </div>
  {"".join(blocks)}
</div>
<div class="footer">
  <p>AI챔피언 그린 수준 데이터분석 실습 · 자동 생성 문제지</p>
</div>
</body>
</html>"""


def build_readme(problems: list[Problem]) -> str:
    rows = "\n".join(
        f"| {p.submission_filename} | 문제 {p.number} 예시 답안 ({p.type_name}) |"
        for p in problems
    )
    return f"""# AI챔피언 데이터분석 실습 문제 패키지

## 파일 구성

| 파일명 | 설명 |
|--------|------|
| problems.html | 전체 문제지 (브라우저에서 열기) |
| grading_rubric.xlsx | 채점 기준표 (Excel에서 열기) |
{rows}
| problem_03_vba_code.bas | VBA 매크로 소스 코드 (Excel에 가져오기) |
| answer_key.json | 정답 키 (JSON) |

## 채점 방법

1. `problems.html`을 브라우저에서 열어 문제지 확인
2. `grading_rubric.xlsx`를 Excel에서 열어 채점 진행
3. 제출 파일을 열어 채점 항목별 확인
4. **C열의 □ → ☑ 변경** 시 취득점수 자동 계산
5. 총점 350점 이상 → 합격

## Excel VBA 보고서 실행 방법

1. `problem_03_vba_report.xlsm` 파일 열기
2. **개발 도구** 탭 → **Visual Basic** 클릭
3. **삽입** → **모듈** 선택
4. `problem_03_vba_code.bas` 파일의 내용을 붙여넣기
5. **F5** 또는 **매크로 실행** → `자동보고서생성` 실행

## 합격 기준

- 총 500점 만점 (문제당 100점)
- **350점 이상 합격** (5문제 중 70% 수준)
- 각 문제 배점은 동일 (100점)
"""


def package_all(
    problems: list[Problem],
    artifacts: dict,
    grading_xlsx: bytes,
) -> bytes:
    """모든 파일을 ZIP으로 패키징"""
    buf = io.BytesIO()

    answer_key = {
        f"problem_{p.number:02d}": {
            "title": p.title,
            "type": p.type_name,
            "scenario": p.scenario,
            "submission_file": p.submission_filename,
            "requirements": p.requirements,
            "rubric": [
                {"criterion": ri.criterion, "score": ri.score, "description": ri.description}
                for ri in p.rubric
            ],
            "total_score": 100,
        }
        for p in problems
    }

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 문제지
        zf.writestr("problems.html", build_problems_html(problems).encode("utf-8"))

        # 채점표
        zf.writestr("grading_rubric.xlsx", grading_xlsx)

        # 산출물 파일들
        for filename, content in artifacts.items():
            if filename == "vba_code":
                zf.writestr("problem_03_vba_code.bas", content if isinstance(content, bytes) else content.encode("utf-8"))
            elif isinstance(content, bytes):
                zf.writestr(filename, content)

        # 정답 키
        zf.writestr(
            "answer_key.json",
            json.dumps(answer_key, ensure_ascii=False, indent=2),
        )

        # README
        zf.writestr("README.md", build_readme(problems))

    buf.seek(0)
    return buf.read()
