# app/api/services/analytics_service.py
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
import asyncio
from app.core.db import get_db

class AnalyticsService:
    """Service for analytics and reporting"""
    
    def __init__(self):
        self.db = None
    
    async def _get_db(self):
        """Get database instance"""
        if self.db is None:
            async for db in get_db():
                self.db = db
                break
        return self.db
    
    async def get_student_happiness(self, student_id: str) -> Dict[str, Any]:
        """Get happiness trend for a student"""
        try:
            db = await self._get_db()
            
            # Query patient metrics for happiness data
            pipeline = [
                {"$match": {"patient_id": student_id}},
                {"$sort": {"timestamp": 1}},
                {"$project": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "happiness": "$happiness"
                }},
                {"$group": {
                    "_id": "$date",
                    "avg_happiness": {"$avg": "$happiness"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            cursor = db.patient_metrics.aggregate(pipeline)
            happiness_data = await cursor.to_list(length=None)
            
            # Format the data
            happiness_trend = []
            total_happiness = 0
            count = 0
            
            for item in happiness_data:
                if item["avg_happiness"] is not None:
                    happiness_trend.append({
                        "date": item["_id"],
                        "happiness": round(item["avg_happiness"], 2)
                    })
                    total_happiness += item["avg_happiness"]
                    count += 1
            
            average_happiness = round(total_happiness / count, 2) if count > 0 else 0
            
            # Determine trend
            trend = "stable"
            if len(happiness_trend) >= 2:
                first_half = happiness_trend[:len(happiness_trend)//2]
                second_half = happiness_trend[len(happiness_trend)//2:]
                first_avg = sum(item["happiness"] for item in first_half) / len(first_half)
                second_avg = sum(item["happiness"] for item in second_half) / len(second_half)
                
                if second_avg > first_avg + 5:
                    trend = "improving"
                elif second_avg < first_avg - 5:
                    trend = "declining"
            
            return {
                "student_id": student_id,
                "happiness_trend": happiness_trend,
                "average_happiness": average_happiness,
                "trend": trend
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get student happiness data"
            }
    
    async def generate_student_pdf(self, student_id: str) -> Dict[str, Any]:
        """Generate PDF report for a student"""
        try:
            # Get student data
            happiness_data = await self.get_student_happiness(student_id)
            
            # Generate chart
            if happiness_data.get("happiness_trend"):
                plt.figure(figsize=(10, 6))
                dates = [item["date"] for item in happiness_data["happiness_trend"]]
                happiness_values = [item["happiness"] for item in happiness_data["happiness_trend"]]
                
                plt.plot(dates, happiness_values, marker='o', linewidth=2, markersize=6)
                plt.title(f"Student Happiness Trend - ID: {student_id}")
                plt.xlabel("Date")
                plt.ylabel("Happiness Score")
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                # Save chart to bytes
                chart_buffer = io.BytesIO()
                plt.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                chart_buffer.seek(0)
                chart_bytes = chart_buffer.getvalue()
                
                # Convert to base64 for PDF
                import base64
                chart_base64 = base64.b64encode(chart_bytes).decode()
                
                return {
                    "student_id": student_id,
                    "chart_base64": chart_base64,
                    "happiness_data": happiness_data,
                    "message": "Student PDF report generated successfully"
                }
            else:
                return {
                    "student_id": student_id,
                    "message": "No data available for PDF generation"
                }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to generate student PDF"
            }
    
    async def get_students_for_counselor(self, counselor_id: str) -> Dict[str, Any]:
        """Get list of students for a counselor"""
        try:
            db = await self._get_db()
            
            # Query sessions to find students assigned to this counselor
            cursor = db.sessions.find(
                {"therapist_id": counselor_id},
                {"patient_id": 1, "date": 1, "_id": 0}
            ).sort("date", -1)
            
            sessions = await cursor.to_list(length=None)
            
            # Get unique students with their latest session date
            student_sessions = {}
            for session in sessions:
                patient_id = session["patient_id"]
                if patient_id not in student_sessions:
                    student_sessions[patient_id] = session["date"]
            
            # Format response
            students = []
            for patient_id, last_session in student_sessions.items():
                students.append({
                    "id": patient_id,
                    "last_session": last_session.isoformat() if last_session else None
                })
            
            return {
                "counselor_id": counselor_id,
                "students": students,
                "total_students": len(students)
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get students for counselor"
            }
    
    async def get_counselor_analytics(self, counselor_id: str) -> Dict[str, Any]:
        """Get analytics for a counselor"""
        try:
            db = await self._get_db()
            
            # Get students for this counselor
            students_data = await self.get_students_for_counselor(counselor_id)
            student_ids = [student["id"] for student in students_data["students"]]
            
            # Get session analytics
            pipeline = [
                {"$match": {"therapist_id": counselor_id}},
                {"$group": {
                    "_id": None,
                    "total_sessions": {"$sum": 1},
                    "unique_patients": {"$addToSet": "$patient_id"}
                }},
                {"$project": {
                    "total_sessions": 1,
                    "unique_patients": {"$size": "$unique_patients"}
                }}
            ]
            
            session_cursor = db.sessions.aggregate(pipeline)
            session_data = await session_cursor.to_list(length=1)
            
            # Get happiness trend for all students
            if student_ids:
                happiness_pipeline = [
                    {"$match": {"patient_id": {"$in": student_ids}}},
                    {"$sort": {"timestamp": 1}},
                    {"$project": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "happiness": "$happiness"
                    }},
                    {"$group": {
                        "_id": "$date",
                        "avg_happiness": {"$avg": "$happiness"}
                    }},
                    {"$sort": {"_id": 1}}
                ]
                
                happiness_cursor = db.patient_metrics.aggregate(happiness_pipeline)
                happiness_data = await happiness_cursor.to_list(length=None)
                
                happiness_trend = [
                    {"date": item["_id"], "average_happiness": round(item["avg_happiness"], 2)}
                    for item in happiness_data if item["avg_happiness"] is not None
                ]
            else:
                happiness_trend = []
            
            session_stats = session_data[0] if session_data else {"total_sessions": 0, "unique_patients": 0}
            
            return {
                "counselor_id": counselor_id,
                "total_sessions": session_stats["total_sessions"],
                "active_students": session_stats["unique_patients"],
                "average_session_rating": 4.2,  # Mock data - would need rating system
                "happiness_trend": happiness_trend
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get counselor analytics"
            }
    
    async def generate_counselor_pdf(self, counselor_id: str) -> Dict[str, Any]:
        """Generate PDF report for a counselor"""
        try:
            # Get counselor analytics
            analytics = await self.get_counselor_analytics(counselor_id)
            
            # Generate chart if we have happiness trend data
            chart_base64 = None
            if analytics.get("happiness_trend"):
                plt.figure(figsize=(12, 8))
                dates = [item["date"] for item in analytics["happiness_trend"]]
                happiness_values = [item["average_happiness"] for item in analytics["happiness_trend"]]
                
                plt.plot(dates, happiness_values, marker='o', linewidth=2, markersize=6, color='blue')
                plt.title(f"Counselor Analytics - ID: {counselor_id}")
                plt.xlabel("Date")
                plt.ylabel("Average Happiness Score")
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                # Save chart to bytes
                chart_buffer = io.BytesIO()
                plt.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight')
                plt.close()
                chart_buffer.seek(0)
                
                import base64
                chart_base64 = base64.b64encode(chart_buffer.getvalue()).decode()
            
            return {
                "counselor_id": counselor_id,
                "analytics": analytics,
                "chart_base64": chart_base64,
                "message": "Counselor PDF report generated successfully"
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to generate counselor PDF"
            }
    
    async def get_admin_overall_analytics(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get organization-wide analytics for admin"""
        try:
            db = await self._get_db()
            
            # Date filter
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Get total counts
            total_students = await db.patient_metrics.distinct("patient_id")
            total_counselors = await db.sessions.distinct("therapist_id")
            total_sessions = await db.sessions.count_documents({})
            
            # Get happiness trend across all students
            happiness_pipeline = [
                {"$sort": {"timestamp": 1}},
                {"$project": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "happiness": "$happiness"
                }},
                {"$group": {
                    "_id": "$date",
                    "avg_happiness": {"$avg": "$happiness"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            if date_filter:
                happiness_pipeline.insert(0, {"$match": {"timestamp": date_filter}})
            
            happiness_cursor = db.patient_metrics.aggregate(happiness_pipeline)
            happiness_data = await happiness_cursor.to_list(length=None)
            
            happiness_trend = [
                {"date": item["_id"], "average_happiness": round(item["avg_happiness"], 2)}
                for item in happiness_data if item["avg_happiness"] is not None
            ]
            
            # Calculate overall average happiness
            avg_happiness = 0
            if happiness_data:
                total_happiness = sum(item["avg_happiness"] for item in happiness_data if item["avg_happiness"] is not None)
                count = len([item for item in happiness_data if item["avg_happiness"] is not None])
                avg_happiness = round(total_happiness / count, 2) if count > 0 else 0
            
            # Get session distribution
            session_dist_pipeline = [
                {"$group": {
                    "_id": "$session_type",
                    "count": {"$sum": 1}
                }}
            ]
            
            session_cursor = db.sessions.aggregate(session_dist_pipeline)
            session_dist_data = await session_cursor.to_list(length=None)
            
            session_distribution = {
                "individual": 0,
                "group": 0,
                "emergency": 0
            }
            
            for item in session_dist_data:
                session_type = item["_id"] or "individual"
                session_distribution[session_type] = item["count"]
            
            return {
                "total_students": len(total_students),
                "total_counselors": len(total_counselors),
                "total_sessions": total_sessions,
                "average_happiness_score": avg_happiness,
                "happiness_trend": happiness_trend,
                "top_issues": ["anxiety", "academic_stress", "depression"],  # Mock data
                "session_distribution": session_distribution
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get admin analytics"
            }
    
    async def get_all_therapists(self) -> Dict[str, Any]:
        """Get list of all therapists"""
        try:
            db = await self._get_db()
            
            # Get therapist data from sessions
            pipeline = [
                {"$group": {
                    "_id": "$therapist_id",
                    "session_count": {"$sum": 1},
                    "unique_patients": {"$addToSet": "$patient_id"}
                }},
                {"$project": {
                    "therapist_id": "$_id",
                    "session_count": 1,
                    "active_students": {"$size": "$unique_patients"}
                }},
                {"$sort": {"active_students": -1}}
            ]
            
            cursor = db.sessions.aggregate(pipeline)
            therapist_data = await cursor.to_list(length=None)
            
            # Format response
            therapists = []
            for item in therapist_data:
                therapists.append({
                    "id": item["therapist_id"],
                    "session_count": item["session_count"],
                    "active_students": item["active_students"]
                })
            
            return {
                "therapists": therapists,
                "total_therapists": len(therapists)
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to get therapists list"
            }
