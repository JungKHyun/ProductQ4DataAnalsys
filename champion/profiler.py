"""데이터 프로파일링 및 도메인 추정 모듈"""
from __future__ import annotations
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ColumnProfile:
    name: str
    dtype_str: str
    category: str  # numeric | categorical | datetime | text
    null_count: int
    null_pct: float
    unique_count: int
    sample_values: list
    stats: dict = field(default_factory=dict)


@dataclass
class DataProfile:
    row_count: int
    col_count: int
    columns: list[ColumnProfile]
    numeric_cols: list[str]
    categorical_cols: list[str]
    datetime_cols: list[str]
    agg_recommendations: list[dict]
    viz_recommendations: list[dict]
    summary_text: str  # LLM 프롬프트용 요약


def _categorize_column(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if series.dtype == object:
        sample = series.dropna().head(10).astype(str).tolist()
        date_hits = sum(
            1 for v in sample
            if any(k in v for k in ["-", "/", "년", "월", "일"])
            and any(c.isdigit() for c in v)
        )
        if date_hits >= len(sample) * 0.6:
            return "datetime"
    ratio = series.nunique() / max(len(series), 1)
    if ratio < 0.05 or series.nunique() <= 30:
        return "categorical"
    return "text"


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    col_profiles: list[ColumnProfile] = []
    numeric_cols: list[str] = []
    categorical_cols: list[str] = []
    datetime_cols: list[str] = []

    for col in df.columns:
        s = df[col]
        cat = _categorize_column(s)
        stats: dict = {}

        if cat == "numeric":
            numeric_cols.append(col)
            valid = pd.to_numeric(s, errors="coerce").dropna()
            stats = {
                "mean": round(float(valid.mean()), 4) if len(valid) else None,
                "median": round(float(valid.median()), 4) if len(valid) else None,
                "std": round(float(valid.std()), 4) if len(valid) else None,
                "min": float(valid.min()) if len(valid) else None,
                "max": float(valid.max()) if len(valid) else None,
                "sum": float(valid.sum()) if len(valid) else None,
            }
        elif cat == "categorical":
            categorical_cols.append(col)
            vc = s.value_counts()
            stats = {
                "top_values": {str(k): int(v) for k, v in vc.head(5).items()},
                "mode": str(vc.index[0]) if len(vc) else None,
            }
        elif cat == "datetime":
            datetime_cols.append(col)

        col_profiles.append(ColumnProfile(
            name=col,
            dtype_str=str(s.dtype),
            category=cat,
            null_count=int(s.isna().sum()),
            null_pct=round(float(s.isna().mean() * 100), 1),
            unique_count=int(s.nunique()),
            sample_values=[str(v) for v in s.dropna().head(3).tolist()],
            stats=stats,
        ))

    # 집계 추천
    agg_recs = []
    for num_col in numeric_cols[:4]:
        for cat_col in categorical_cols[:3]:
            agg_recs.append({
                "group_col": cat_col,
                "value_col": num_col,
                "description": f"{cat_col}별 {num_col} 합계/평균",
            })

    # 시각화 추천
    viz_recs = []
    if categorical_cols and numeric_cols:
        viz_recs.append({
            "type": "bar_chart",
            "x": categorical_cols[0],
            "y": numeric_cols[0],
        })
    if len(numeric_cols) >= 2:
        viz_recs.append({
            "type": "scatter",
            "x": numeric_cols[0],
            "y": numeric_cols[1],
        })
    if datetime_cols and numeric_cols:
        viz_recs.append({
            "type": "line_chart",
            "x": datetime_cols[0],
            "y": numeric_cols[0],
        })

    # LLM 프롬프트용 요약 텍스트
    lines = [
        f"행 수: {len(df):,} | 열 수: {len(df.columns)}",
        f"수치형 컬럼: {', '.join(numeric_cols) if numeric_cols else '없음'}",
        f"범주형 컬럼: {', '.join(categorical_cols) if categorical_cols else '없음'}",
        f"날짜형 컬럼: {', '.join(datetime_cols) if datetime_cols else '없음'}",
        "",
        "컬럼별 상세:",
    ]
    for cp in col_profiles:
        stat_str = ""
        if cp.category == "numeric" and cp.stats:
            stat_str = f" [평균={cp.stats.get('mean')}, 최대={cp.stats.get('max')}]"
        elif cp.category == "categorical" and cp.stats:
            top = cp.stats.get("top_values", {})
            top_str = ", ".join(f"{k}({v})" for k, v in list(top.items())[:3])
            stat_str = f" [상위값: {top_str}]"
        lines.append(f"  - {cp.name} ({cp.category}, 결측 {cp.null_pct}%){stat_str}")

    lines.append("")
    lines.append(f"샘플 데이터 (상위 5행):\n{df.head(5).to_csv(index=False)}")

    return DataProfile(
        row_count=len(df),
        col_count=len(df.columns),
        columns=col_profiles,
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        datetime_cols=datetime_cols,
        agg_recommendations=agg_recs,
        viz_recommendations=viz_recs,
        summary_text="\n".join(lines),
    )
