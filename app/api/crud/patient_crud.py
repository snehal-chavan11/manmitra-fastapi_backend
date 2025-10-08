# crud/patient_crud.py
from typing import Optional, List
from datetime import datetime
from app.core.db import get_db
from bson import ObjectId

# Database will be obtained through dependency injection

# insert one patient data record (we store in a 'patient_metrics' collection)
async def insert_patient_data(db, payload: dict):
    res = await db.patient_metrics.insert_one(payload)
    return res.inserted_id

# query patient metrics by patient_id range etc.
async def get_patient_metrics(db, patient_id: str, start: Optional[datetime] = None, end: Optional[datetime] = None) -> List[dict]:
    q = {"patient_id": patient_id}
    if start or end:
        q["$and"] = []
        if start:
            q["$and"].append({"timestamp": {"$gte": start}})
        if end:
            q["$and"].append({"timestamp": {"$lte": end}})
        if not q["$and"]:
            q.pop("$and")
    cursor = db.patient_metrics.find(q).sort("timestamp", 1)
    return await cursor.to_list(length=None)

# get all patients seen by a counselor (assumes sessions collection stored relations)
async def get_students_of_counselor(db, counselor_id: str) -> List[str]:
    # assume sessions collection contains {therapist_id, patient_id}
    cursor = db.sessions.distinct("patient_id", {"therapist_id": counselor_id})
    return await cursor

# fetch latest session titles for a list of patient ids
async def get_session_titles(db, patient_ids: List[str], start: Optional[datetime] = None, end: Optional[datetime] = None):
    q = {"patient_id": {"$in": patient_ids}}
    if start or end:
        q["date"] = {}
        if start: q["date"]["$gte"] = start
        if end: q["date"]["$lte"] = end
    cursor = db.session_summaries.find(q, {"patient_id": 1, "title": 1, "date": 1})
    return await cursor.to_list(length=None)
