"""
Background Job Scheduler
Handles automated reminders and onboarding support
"""

import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from threading import Thread
import os

from sqlalchemy.orm import Session
from database.database import get_db
from database import models
from services.email_service import EmailService

logger = logging.getLogger(__name__)

class ReminderService:
    """Service for handling automated reminders and onboarding support"""
    
    def __init__(self, slack_app=None):
        self.slack_app = slack_app
        self.email_service = EmailService()
        self.is_running = False
        self.scheduler_thread = None
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        
        # For development/testing: frequent checks
        if os.getenv("ENVIRONMENT", "production").lower() in ["development", "dev", "test"]:
            logger.info("🔧 Starting scheduler in DEVELOPMENT mode with frequent checks")
            schedule.every(5).minutes.do(self._daily_progress_check)
            schedule.every(10).minutes.do(self._weekly_summary)
            check_interval = 30  # Check every 30 seconds
        else:
            # Production schedule: more reasonable intervals
            logger.info("🏭 Starting scheduler in PRODUCTION mode with normal intervals")
            schedule.every().day.at("09:00").do(self._daily_progress_check)
            schedule.every().monday.at("09:00").do(self._weekly_summary)
            check_interval = 60  # Check every minute
        
        # Start scheduler in separate thread
        self.scheduler_thread = Thread(target=self._run_scheduler, args=(check_interval,), daemon=True)
        self.scheduler_thread.start()
        
        logger.info("📅 Background scheduler started")
    
    def _run_scheduler(self, check_interval: int = 60):
        """Run the scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)  # Wait 1 minute on error
    
    def _daily_progress_check(self):
        """Send daily progress check to active users"""
        try:
            with next(get_db()) as db:
                # Get users who are in progress with onboarding
                active_users = db.query(models.User).filter(
                    models.User.onboarding_status == models.OnboardingStatus.IN_PROGRESS
                ).all()
                
                if active_users:
                    logger.info(f"Sending daily check-in to {len(active_users)} active users")
                    
                    for user in active_users:
                        self._send_daily_checkin(user)
                
        except Exception as e:
            logger.error(f"Error in daily progress check: {str(e)}")
    
    def _send_daily_checkin(self, user: models.User):
        """Send a daily check-in message to user"""
        try:
            if not self.slack_app:
                return
            
            message = f"""👋 Hi {user.full_name}! 

🚀 How's your onboarding going today? 

I'm here to help with:
• 📚 Company policies and procedures
• ❓ Any questions you might have
• 🤝 General onboarding guidance

Feel free to ask me anything! Type `help` to see what I can do."""
            
            self.slack_app.client.chat_postMessage(
                channel=user.slack_user_id,
                text=message
            )
            
            logger.info(f"Sent daily check-in to {user.full_name}")
            
        except Exception as e:
            logger.error(f"Error sending daily check-in to {user.full_name}: {str(e)}")
    
    def _weekly_summary(self):
        """Send weekly onboarding summary"""
        try:
            with next(get_db()) as db:
                # Get statistics
                total_users = db.query(models.User).count()
                completed_users = db.query(models.User).filter(
                    models.User.onboarding_status == models.OnboardingStatus.COMPLETED
                ).count()
                in_progress_users = db.query(models.User).filter(
                    models.User.onboarding_status == models.OnboardingStatus.IN_PROGRESS
                ).count()
                
                logger.info(f"📊 Weekly Summary: {total_users} total users, {completed_users} completed, {in_progress_users} in progress")
                
        except Exception as e:
            logger.error(f"Error generating weekly summary: {str(e)}")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("🛑 Background scheduler stopped")
    
    def send_reminder(self, user_id: str, reminder_type: str, context: Dict[str, Any]):
        """Send a reminder to a specific user"""
        try:
            if not self.slack_app:
                logger.warning("No Slack app available for sending reminder")
                return
            
            with next(get_db()) as db:
                user = db.query(models.User).filter(models.User.slack_user_id == user_id).first()
                if not user:
                    logger.error(f"User {user_id} not found for reminder")
                    return
                
                message = self._generate_reminder_message(user, reminder_type, context)
                
                self.slack_app.client.chat_postMessage(
                    channel=user_id,
                    text=message
                )
                
                logger.info(f"Sent {reminder_type} reminder to {user.full_name}")
                
        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
    
    def _generate_reminder_message(self, user: models.User, reminder_type: str, context: Dict[str, Any]) -> str:
        """Generate reminder message based on type"""
        if reminder_type == "daily_checkin":
            return f"""👋 Hi {user.full_name}!

🤝 Just checking in on your onboarding progress. 

Need any help with:
• Company policies or procedures?
• Questions about your role or team?
• General onboarding guidance?

I'm here to help! Feel free to ask me anything."""
        
        elif reminder_type == "welcome_followup":
            return f"""🎉 Welcome again, {user.full_name}!

Hope you're settling in well! I'm here to support your onboarding journey.

💡 **Quick reminders:**
• Ask me about company policies anytime
• Let me know your role for personalized guidance  
• Type `help` to see all my capabilities

How are things going so far?"""
        
        else:
            return f"Hi {user.full_name}! This is a reminder about your onboarding. Feel free to ask me any questions!"


# Global scheduler instance
_scheduler_instance = None

def start_background_jobs(slack_app=None) -> ReminderService:
    """Start the background job scheduler"""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = ReminderService(slack_app)
        _scheduler_instance.start_scheduler()
    
    return _scheduler_instance

def stop_background_jobs():
    """Stop the background job scheduler"""
    global _scheduler_instance
    
    if _scheduler_instance:
        _scheduler_instance.stop_scheduler()
        _scheduler_instance = None