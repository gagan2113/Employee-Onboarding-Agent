from langchain.tools import BaseTool
from langchain.agents import initialize_agent, AgentType
from langchain_community.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session
from database.models import User, CompanyPolicy, UserInteraction
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

class DatabaseQueryTool(BaseTool):
    """Tool for querying the database"""
    name: str = "database_query"
    description: str = "Query the database for user information, policies, or interactions"
    
    def __init__(self, db_session: Session):
        super().__init__()
        self.db = db_session
    
    def _run(self, query_type: str, user_id: str = None, **kwargs) -> str:
        """Execute database query"""
        try:
            if query_type == "user_info":
                user = self.db.query(User).filter(User.slack_user_id == user_id).first()
                if user:
                    return f"User: {user.full_name}, Role: {user.role.value}, Status: {user.onboarding_status.value}"
                return "User not found"
            
            elif query_type == "policies":
                role = kwargs.get("role")
                policies = self.db.query(CompanyPolicy).filter(
                    CompanyPolicy.is_active == True
                ).all()
                if role:
                    policies = [p for p in policies if not p.role_specific or role in p.role_specific]
                return json.dumps([{
                    "title": policy.title,
                    "category": policy.category,
                    "content": policy.content[:200] + "..."
                } for policy in policies])
            
            return "Query type not supported"
        
        except Exception as e:
            return f"Database error: {str(e)}"
    
    async def _arun(self, query_type: str, user_id: str = None, **kwargs) -> str:
        """Async version of _run"""
        return self._run(query_type, user_id, **kwargs)

class SlackIntegrationTool(BaseTool):
    """Tool for Slack integrations"""
    name: str = "slack_integration"
    description: str = "Send messages, create channels, schedule reminders in Slack"
    
    def __init__(self, slack_client):
        super().__init__()
        self.slack_client = slack_client
    
    def _run(self, action: str, **kwargs) -> str:
        """Execute Slack action"""
        try:
            if action == "send_message":
                response = self.slack_client.chat_postMessage(
                    channel=kwargs.get("channel"),
                    text=kwargs.get("text"),
                    thread_ts=kwargs.get("thread_ts")
                )
                return f"Message sent successfully: {response['ts']}"
            
            elif action == "schedule_reminder":
                response = self.slack_client.chat_scheduleMessage(
                    channel=kwargs.get("channel"),
                    text=kwargs.get("text"),
                    post_at=kwargs.get("post_at")
                )
                return f"Reminder scheduled: {response['scheduled_message_id']}"
            
            elif action == "create_channel":
                response = self.slack_client.conversations_create(
                    name=kwargs.get("name"),
                    is_private=kwargs.get("is_private", False)
                )
                return f"Channel created: {response['channel']['id']}"
            
            return "Action not supported"
        
        except Exception as e:
            return f"Slack integration error: {str(e)}"
    
    async def _arun(self, action: str, **kwargs) -> str:
        """Async version of _run"""
        return self._run(action, **kwargs)
