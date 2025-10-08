# models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# small submodels
class SessionSummary(BaseModel):
    session_id: str
    therapist_id: str
    title: str
    summary_text: Optional[str] = None
    date: datetime

class PHQ9Entry(BaseModel):
    score: int
    answers: List[int]   # 9 ints
    date: datetime

class GAD7Entry(BaseModel):
    score: int
    answers: List[int]   # 7 ints
    date: datetime

class HappinessEntry(BaseModel):
    value: int   # e.g., 0-100
    date: datetime

class ChatSummary(BaseModel):
    date: datetime
    summary: str

# Patient data document to be stored in DB (can be extended)
class PatientDataIn(BaseModel):
    patient_id: str
    phq9: Optional[PHQ9Entry]
    gad7: Optional[GAD7Entry]
    happiness: Optional[HappinessEntry]
    chat_summary: Optional[ChatSummary]
    session_summary: Optional[SessionSummary]

# Response models
class AnalyticsRequest(BaseModel):
    counselor_id: Optional[str] = None  # if present, analyze students of that counselor
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class PDFRequest(BaseModel):
    counselor_id: Optional[str] = None
    student_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
