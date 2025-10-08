# services/analytics.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.api.crud.patient_crud import get_patient_metrics, get_students_of_counselor, get_session_titles
from app.core.db import get_db

plt.switch_backend("Agg")  # non-GUI backend

# helper to build dataframe from metrics records
def records_to_df(records: List[dict]) -> pd.DataFrame:
    # records expected to contain fields: patient_id, timestamp, happiness (0-100), phq9.score, gad7.score, session_title
    if not records:
        return pd.DataFrame()
    normalized = []
    for r in records:
        row = {
            "patient_id": r.get("patient_id"),
            "timestamp": r.get("timestamp"),
            "happiness": r.get("happiness", None),
            "phq9": r.get("phq9_score", None),
            "gad7": r.get("gad7_score", None),
            "session_title": r.get("session_title", None)
        }
        normalized.append(row)
    df = pd.DataFrame(normalized)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

# asynchronous wrapper to run blocking pandas/matplotlib in thread
async def compute_counselor_analytics(counselor_id: str, start: Optional[datetime], end: Optional[datetime]) -> Dict[str, Any]:
    # acquire db instance
    db = None
    async for _db in get_db():
        db = _db
        break
    if db is None:
        return {"error": "DB not available"}

    # get list of students
    patient_ids = await get_students_of_counselor(db, counselor_id)
    # fetch metrics for each student
    tasks = [get_patient_metrics(db, pid, start, end) for pid in patient_ids]
    all_records_lists = await asyncio.gather(*tasks)
    # flatten and include patient_id
    combined = []
    for lst in all_records_lists:
        combined.extend(lst)
    # Run heavy computation in thread
    result = await asyncio.to_thread(_compute_analytics_sync, combined)
    return result

def _compute_analytics_sync(records: List[dict]) -> Dict[str, Any]:
    df = records_to_df(records)
    out = {"student_count": 0, "charts": {}, "insights": []}
    if df.empty:
        return out
    out["student_count"] = df["patient_id"].nunique()
    # compute happiness over time: group by date
    df["date"] = df["timestamp"].dt.date
    daily = df.groupby("date").agg({"happiness": "mean"}).reset_index()
    # Create a line plot for daily happiness average
    buf = io.BytesIO()
    plt.figure(figsize=(8,4))
    plt.plot(daily["date"], daily["happiness"], marker="o")
    plt.title("Average Happiness Over Time")
    plt.xlabel("Date")
    plt.ylabel("Avg happiness")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    out["charts"]["happiness_trend_png"] = buf.getvalue()

    # compute session_title vs happiness change
    # For each session_title, compute mean happiness after that session for patients with that title
    # We approximate: group by session_title and compute avg happiness
    df_title = df.dropna(subset=["session_title", "happiness"])
    title_stats = df_title.groupby("session_title").agg({"happiness": ["mean", "count"]})
    title_stats.columns = ["happiness_mean", "count"]
    title_stats = title_stats.reset_index().sort_values("happiness_mean", ascending=False)
    out["title_stats"] = title_stats.head(20).to_dict(orient="records")

    # Example auto-insight: compute percentage of students with session_title == 'panic attacks' whose average happiness increased
    # naive approach: for each patient with that title, compare earliest vs latest happiness
    insights = []
    if "panic" in " ".join(df_title["session_title"].astype(str).unique()).lower():
        # find patients with session_title containing 'panic'
        panic_mask = df_title["session_title"].str.contains("panic", case=False, na=False)
        panic_patients = df_title.loc[panic_mask, "patient_id"].unique()
        improved = 0
        total = len(panic_patients)
        for pid in panic_patients:
            dpid = df[df["patient_id"] == pid].sort_values("timestamp")
            if dpid["happiness"].isnull().all(): continue
            first = dpid["happiness"].iloc[0]
            last = dpid["happiness"].iloc[-1]
            if last > first: improved += 1
        if total > 0:
            pct = round((improved/total)*100)
            insights.append(f"{pct}% of students who are labeled with 'panic' in session titles show improved happiness.")
    out["insights"] = insights

    return out
