from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database.database import get_db, engine
from database.models import Base
from database import models
from slack_bot_handler import SlackBotHandler
from langchain_components.agent import OnboardingAgent
from langchain_components.groq_llm import create_groq_llm
from services.background_jobs import start_background_jobs, stop_background_jobs
from app_settings import settings
import uvicorn
import logging
from typing import Dict, Any
import json
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="Employee Onboarding Agent with Slack Integration"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
slack_bot = SlackBotHandler()
llm = create_groq_llm(temperature=0.7, use_wrapper=False)  # Use raw ChatGroq for LangChain compatibility

# Start background job manager
logger.info("🚀 Starting background job manager...")
background_job_manager = start_background_jobs(slack_bot.app if not slack_bot.test_mode else None)
logger.info("✅ Background job manager started")

# Register cleanup function
atexit.register(stop_background_jobs)

# Thread-safe agent factory (creates fresh agent per request)
def get_agent(db: Session = Depends(get_db)):
    """Create a fresh onboarding agent for each request with proper database session"""
    try:
        # Get Slack client if available
        client = slack_bot.app.client if (slack_bot.app and not slack_bot.test_mode) else None
        
        # Create new agent instance with fresh database session
        agent = OnboardingAgent(llm, db, client)
        logger.info(f"✅ Created fresh onboarding agent with database session: {id(db)}")
        return agent
        
    except Exception as e:
        logger.error(f"❌ Failed to create onboarding agent: {e}")
        # Return a minimal fallback agent
        return OnboardingAgent(llm, db, None)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Employee Onboarding Agent API",
        "version": settings.API_VERSION,
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

# API Routes for managing onboarding

@app.get("/api/onboarding/status/{user_id}")
async def get_onboarding_status(user_id: str, db: Session = Depends(get_db)):
    """Get onboarding status for a user"""
    try:
        user = db.query(models.User).filter(models.User.slack_user_id == user_id).first()
        logger.info(f"🔍 Retrieved user for status check: {user_id} -> {user}")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_id": user_id,
            "status": user.onboarding_status.value,
            "role": user.role.value,
            "department": user.department,
            "start_date": user.start_date.isoformat() if user.start_date else None,
            "full_name": user.full_name,
            "email": user.email
        }
    
    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/onboarding/message")
async def process_message(
    message_data: Dict[str, Any],
    agent = Depends(get_agent),
    db: Session = Depends(get_db)
):
    """Process a message through the onboarding agent"""
    try:
        user_id = message_data.get("user_id")
        message = message_data.get("message")
        context = message_data.get("context", {})
        
        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message are required")
        
        # Process message through agent
        response = agent.process_message(user_id, message, context)
        
        # Store interaction in database
        user = db.query(models.User).filter(models.User.slack_user_id == user_id).first()
        logger.info(f"💬 Processed message for user: {user_id} -> {user}")
        logger.debug(f"🤖 Agent response: {response}")
        
        if user:
            try:
                interaction = models.UserInteraction(
                    user_id=user.id,
                    message=message,
                    response=response,
                    interaction_type="message"
                )
                db.add(interaction)
                db.commit()
                logger.info(f"✅ Stored interaction for user: {user_id}")
            except Exception as db_error:
                logger.error(f"❌ Failed to store interaction: {db_error}")
                db.rollback()  # Rollback on error
        
        return {
            "response": response,
            "user_id": user_id
        }
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reminders/send")
async def send_reminder(
    reminder_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Send a reminder to a user"""
    try:
        user_id = reminder_data.get("user_id")
        reminder_type = reminder_data.get("type", "daily_checkin")
        context = reminder_data.get("context", {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Send reminder through Slack
        slack_bot.send_reminder(user_id, reminder_type, context)
        
        return {
            "message": "Reminder sent successfully",
            "user_id": user_id,
            "type": reminder_type
        }
    
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/overview")
async def get_analytics_overview(db: Session = Depends(get_db)):
    """Get onboarding analytics overview"""
    try:
        # Total users
        total_users = db.query(models.User).count()
        
        # Users by status
        completed_users = db.query(models.User).filter(
            models.User.onboarding_status == models.OnboardingStatus.COMPLETED
        ).count()
        
        in_progress_users = db.query(models.User).filter(
            models.User.onboarding_status == models.OnboardingStatus.IN_PROGRESS
        ).count()
        
        # Average completion time (placeholder)
        avg_completion_days = 5.2
        
        return {
            "total_users": total_users,
            "completed_users": completed_users,
            "in_progress_users": in_progress_users,
            "completion_rate": (completed_users / total_users * 100) if total_users > 0 else 0,
            "average_completion_days": avg_completion_days
        }
    
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import threading
    import signal
    import sys
    import time
    
    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        logger.info("🛑 Shutting down gracefully...")
        stop_background_jobs()
        if not slack_bot.test_mode and hasattr(slack_bot, 'handler') and slack_bot.handler:
            try:
                slack_bot.handler.close()
                logger.info("✅ Slack handler closed")
            except Exception as e:
                logger.error(f"⚠️ Error closing Slack handler: {e}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start Slack bot in a separate thread (if not in test mode)
    if not slack_bot.test_mode:
        def start_slack_bot():
            try:
                logger.info("🤖 Starting Slack Socket Mode handler in background thread...")
                slack_bot.start_async()
            except Exception as e:
                logger.error(f"❌ Slack bot error: {e}")
        
        # Start Slack bot in background thread to avoid blocking FastAPI
        slack_thread = threading.Thread(target=start_slack_bot, daemon=True)
        slack_thread.start()
        
        # Give Slack bot a moment to initialize
        time.sleep(2)
        logger.info("✅ Slack bot thread started")
    else:
        logger.info("🧪 Slack bot in TEST MODE - API still available")
    
    # Start FastAPI server
    logger.info("🚀 Starting FastAPI server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,  # Keep disabled for threading stability
        log_level="info"
    )
