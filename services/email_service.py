"""
Email Service
Handles sending email notifications to managers and other stakeholders
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from config.config_manager import ConfigurationManager

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.company_name = os.getenv("COMPANY_NAME", "Your Company")
        
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email service will not work.")
    
    def send_manager_escalation_email(self, 
                                    manager_email: str, 
                                    employee_name: str,
                                    employee_email: str,
                                    overdue_tasks: List[Dict[str, Any]],
                                    employee_start_date: datetime) -> bool:
        """Send escalation email to manager about overdue employee tasks"""
        
        if not self._validate_email_config():
            return False
        
        try:
            config_manager = ConfigurationManager()
            
            # Load email template from config
            email_config = config_manager.email_config
            template_config = email_config.get("email_templates", {}).get("manager_escalation", {})
            
            subject = template_config.get("subject", "🚨 Onboarding Task Overdue - Action Required: {employee_name}")
            subject = subject.format(employee_name=employee_name)
            
            html_template = template_config.get("html_template", "")
            
            # Prepare template data
            days_since_start = (datetime.now() - employee_start_date).days
            
            # Process tasks for template
            task_details = ""
            reminder_history = ""
            
            for task in overdue_tasks:
                days_overdue = (datetime.now() - task['due_date']).days
                task_details += f"<li><strong>{task['title']}</strong> - {days_overdue} days overdue (Due: {task['due_date'].strftime('%Y-%m-%d')})</li>"
                reminder_history += f"<li>{task['title']}: {task['reminder_count']} reminders sent</li>"
            
            # Get email settings for HR email
            email_settings = email_config.get("email_settings", {})
            hr_email = email_settings.get("hr_support_email", "hr@company.com")
            
            # Format the HTML template
            html_content = html_template.format(
                employee_name=employee_name,
                employee_role="New Employee",  # Could be passed as parameter
                employee_department="",  # Could be passed as parameter
                join_date=employee_start_date.strftime('%Y-%m-%d'),
                task_details=task_details,
                reminder_history=reminder_history,
                hr_email=hr_email
            )
            
            # Send email
            return self._send_email(
                to_email=manager_email,
                subject=subject,
                html_content=html_content,
                cc_emails=[employee_email] if employee_email else None
            )
            
        except Exception as e:
            logger.error(f"Error sending manager escalation email: {str(e)}")
            return False
    
    def send_task_completion_summary(self, 
                                   manager_email: str,
                                   employee_name: str, 
                                   completion_summary: Dict[str, Any]) -> bool:
        """Send completion summary email to manager"""
        
        if not self._validate_email_config():
            return False
        
        try:
            config_manager = ConfigurationManager()
            
            # Load email template from config
            email_config = config_manager.email_config
            
            # Use welcome email template as base for completion (or create a new one)
            template_config = email_config.get("email_templates", {}).get("welcome_email", {})
            
            subject = f"✅ Onboarding Completed: {employee_name}"
            
            # Simple completion HTML since we don't have a specific template yet
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background-color: #d4edda; padding: 20px; border-left: 4px solid #28a745; }}
                    .content {{ padding: 20px; }}
                    .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                    .success {{ color: #28a745; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>🎉 Onboarding Successfully Completed!</h2>
                    <p><strong>Employee:</strong> {employee_name}</p>
                </div>
                
                <div class="content">
                    <p>Dear Manager,</p>
                    
                    <p class="success">Great news! {employee_name} has successfully completed their onboarding process.</p>
                    
                    <div class="stats">
                        <h3>📊 Completion Summary</h3>
                        <ul>
                            <li><strong>Total Tasks:</strong> {completion_summary.get('total_tasks', 'N/A')}</li>
                            <li><strong>Completed:</strong> {completion_summary.get('completed_tasks', 'N/A')}</li>
                            <li><strong>Completion Rate:</strong> {completion_summary.get('completion_percentage', 'N/A')}%</li>
                            <li><strong>Start Date:</strong> {completion_summary.get('start_date', 'N/A')}</li>
                            <li><strong>Completion Date:</strong> {completion_summary.get('completion_date', 'N/A')}</li>
                            <li><strong>Total Days:</strong> {completion_summary.get('total_days', 'N/A')}</li>
                        </ul>
                    </div>
                    
                    <p>{employee_name} is now fully onboarded and ready to contribute to the team!</p>
                    
                    <p>Best regards,<br>
                    {self.company_name} Onboarding System</p>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(
                to_email=manager_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending completion summary email: {str(e)}")
            return False
    
    def _send_email(self, 
                   to_email: str, 
                   subject: str, 
                   html_content: str,
                   cc_emails: List[str] = None,
                   attachments: List[str] = None) -> bool:
        """Send an email using SMTP"""
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Add attachments if any
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        msg.attach(part)
            
            # Connect to server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                
                recipients = [to_email]
                if cc_emails:
                    recipients.extend(cc_emails)
                
                server.send_message(msg, to_addrs=recipients)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def _validate_email_config(self) -> bool:
        """Validate email configuration"""
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured")
            return False
        return True
    
    def test_email_connection(self) -> bool:
        """Test email connection and configuration"""
        if not self._validate_email_config():
            return False
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            
            logger.info("Email connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Email connection test failed: {str(e)}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Test email service
    email_service = EmailService()
    
    # Test connection
    if email_service.test_email_connection():
        print("✅ Email service configured correctly")
    else:
        print("❌ Email service configuration issues")
        print("Please check your email environment variables:")
        print("- SMTP_SERVER")
        print("- SMTP_PORT") 
        print("- SMTP_USERNAME")
        print("- SMTP_PASSWORD")
        print("- FROM_EMAIL")