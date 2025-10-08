# app/api/services/pdf_generator.py
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.units import inch
import io
import asyncio
import base64
from typing import Dict, Any, List

class PDFService:
    """Service for PDF generation"""
    
    async def generate_admin_pdf(self, data: Dict[str, Any]) -> str:
        """Generate organization-wide PDF report"""
        try:
            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = styles['Title']
            title = Paragraph("Organization Analytics Report", title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Summary section
            summary_style = styles['Normal']
            
            # Total statistics
            stats_text = f"""
            <b>Organization Overview:</b><br/>
            Total Students: {data.get('total_students', 0)}<br/>
            Total Counselors: {data.get('total_counselors', 0)}<br/>
            Total Sessions: {data.get('total_sessions', 0)}<br/>
            Average Happiness Score: {data.get('average_happiness_score', 0)}<br/>
            """
            story.append(Paragraph(stats_text, summary_style))
            story.append(Spacer(1, 12))
            
            # Session distribution
            session_dist = data.get('session_distribution', {})
            session_text = f"""
            <b>Session Distribution:</b><br/>
            Individual Sessions: {session_dist.get('individual', 0)}<br/>
            Group Sessions: {session_dist.get('group', 0)}<br/>
            Emergency Sessions: {session_dist.get('emergency', 0)}<br/>
            """
            story.append(Paragraph(session_text, summary_style))
            story.append(Spacer(1, 12))
            
            # Top issues
            top_issues = data.get('top_issues', [])
            issues_text = f"""
            <b>Top Issues:</b><br/>
            {', '.join(top_issues)}<br/>
            """
            story.append(Paragraph(issues_text, summary_style))
            story.append(Spacer(1, 12))
            
            # Happiness trend summary
            happiness_trend = data.get('happiness_trend', [])
            if happiness_trend:
                trend_text = f"""
                <b>Happiness Trend Summary:</b><br/>
                Total Data Points: {len(happiness_trend)}<br/>
                Date Range: {happiness_trend[0]['date']} to {happiness_trend[-1]['date']}<br/>
                """
                story.append(Paragraph(trend_text, summary_style))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            # Convert to base64
            pdf_bytes = buffer.getvalue()
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            
            return pdf_base64
            
        except Exception as e:
            # Return error as base64 encoded text
            error_text = f"Error generating PDF: {str(e)}"
            error_bytes = error_text.encode()
            return base64.b64encode(error_bytes).decode()
    
    async def generate_student_pdf(self, student_id: str, data: Dict[str, Any]) -> str:
        """Generate student-specific PDF report"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = styles['Title']
            title = Paragraph(f"Student Report - ID: {student_id}", title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Student information
            summary_style = styles['Normal']
            
            happiness_data = data.get('happiness_data', {})
            avg_happiness = happiness_data.get('average_happiness', 0)
            trend = happiness_data.get('trend', 'unknown')
            
            info_text = f"""
            <b>Student Information:</b><br/>
            Student ID: {student_id}<br/>
            Average Happiness: {avg_happiness}/100<br/>
            Trend: {trend}<br/>
            """
            story.append(Paragraph(info_text, summary_style))
            story.append(Spacer(1, 12))
            
            # Happiness trend
            happiness_trend = happiness_data.get('happiness_trend', [])
            if happiness_trend:
                trend_text = f"""
                <b>Happiness Trend Data:</b><br/>
                Total Records: {len(happiness_trend)}<br/>
                Date Range: {happiness_trend[0]['date']} to {happiness_trend[-1]['date']}<br/>
                """
                story.append(Paragraph(trend_text, summary_style))
                
                # Add trend data table
                for item in happiness_trend[:10]:  # Limit to first 10 entries
                    trend_item = f"Date: {item['date']}, Happiness: {item['happiness']}<br/>"
                    story.append(Paragraph(trend_item, summary_style))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            # Convert to base64
            pdf_bytes = buffer.getvalue()
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            
            return pdf_base64
            
        except Exception as e:
            error_text = f"Error generating student PDF: {str(e)}"
            error_bytes = error_text.encode()
            return base64.b64encode(error_bytes).decode()
    
    async def generate_counselor_pdf(self, counselor_id: str, data: Dict[str, Any]) -> str:
        """Generate counselor-specific PDF report"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = styles['Title']
            title = Paragraph(f"Counselor Report - ID: {counselor_id}", title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Counselor information
            summary_style = styles['Normal']
            
            analytics = data.get('analytics', {})
            total_sessions = analytics.get('total_sessions', 0)
            active_students = analytics.get('active_students', 0)
            avg_rating = analytics.get('average_session_rating', 0)
            
            info_text = f"""
            <b>Counselor Information:</b><br/>
            Counselor ID: {counselor_id}<br/>
            Total Sessions: {total_sessions}<br/>
            Active Students: {active_students}<br/>
            Average Rating: {avg_rating}/5<br/>
            """
            story.append(Paragraph(info_text, summary_style))
            story.append(Spacer(1, 12))
            
            # Happiness trend for counselor's students
            happiness_trend = analytics.get('happiness_trend', [])
            if happiness_trend:
                trend_text = f"""
                <b>Student Happiness Trend:</b><br/>
                Total Data Points: {len(happiness_trend)}<br/>
                """
                story.append(Paragraph(trend_text, summary_style))
                
                # Add trend summary
                for item in happiness_trend[:5]:  # Limit to first 5 entries
                    trend_item = f"Date: {item['date']}, Avg Happiness: {item['average_happiness']}<br/>"
                    story.append(Paragraph(trend_item, summary_style))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            # Convert to base64
            pdf_bytes = buffer.getvalue()
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            
            return pdf_base64
            
        except Exception as e:
            error_text = f"Error generating counselor PDF: {str(e)}"
            error_bytes = error_text.encode()
            return base64.b64encode(error_bytes).decode()
