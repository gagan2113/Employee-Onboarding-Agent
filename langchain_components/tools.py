from langchain.tools import BaseTool
from langchain.agents import initialize_agent, AgentType
from langchain_community.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session
from database.models import User, CompanyPolicy, UserInteraction
from typing import Optional, Dict, Any, List
from pydantic import Field
import json
from datetime import datetime

class DatabaseQueryTool(BaseTool):
    """Tool for querying the database"""
    name: str = "database_query"
    description: str = """Query the database for user information, policies, or interactions. 
    Input should be a natural language query like:
    - "Get user information for slack_user_id U123456"
    - "Find policies for role software_developer"
    - "Get all active policies"
    """
    db: Session = Field(exclude=True)
    
    def __init__(self, db_session: Session, **kwargs):
        super().__init__(db=db_session, **kwargs)
    
    def _run(self, query: str) -> str:
        """Execute database query based on natural language input"""
        try:
            query_lower = query.lower()
            
            # Extract user ID from query if present
            user_id = self._extract_user_id(query)
            
            if "user information" in query_lower or "get user" in query_lower:
                if user_id:
                    user = self.db.query(User).filter(User.slack_user_id == user_id).first()
                    if user:
                        return f"User: {user.full_name}, Role: {user.role.value}, Status: {user.onboarding_status.value}"
                    return "User not found"
                else:
                    return "Please provide a user ID (e.g., U123456) to get user information"
            
            elif "policies" in query_lower:
                # Extract role from query if present
                role = self._extract_role(query)
                policies = self.db.query(CompanyPolicy).filter(
                    CompanyPolicy.is_active == True
                ).all()
                if role:
                    policies = [p for p in policies if not p.role_specific or role in p.role_specific]
                
                if policies:
                    return json.dumps([{
                        "title": policy.title,
                        "category": policy.category,
                        "content": policy.content[:200] + "..."
                    } for policy in policies])
                else:
                    return "No policies found"
            
            return "Query type not supported. Try asking for 'user information' or 'policies'"
        
        except Exception as e:
            return f"Database error: {str(e)}"
    
    def _extract_user_id(self, query: str) -> Optional[str]:
        """Extract user ID from query string"""
        import re
        # Look for patterns like U123456 or slack_user_id U123456
        match = re.search(r'U[A-Z0-9]+', query.upper())
        return match.group(0) if match else None
    
    def _extract_role(self, query: str) -> Optional[str]:
        """Extract role from query string"""
        roles = ["software_developer", "ai_engineer", "hr_associate", "product_manager"]
        query_lower = query.lower()
        for role in roles:
            if role in query_lower:
                return role
        return None
    
    async def _arun(self, query: str) -> str:
        """Async version of _run"""
        return self._run(query)

class SlackIntegrationTool(BaseTool):
    """Tool for Slack integrations"""
    name: str = "slack_integration"
    description: str = """Send messages, create channels, schedule reminders in Slack.
    Input should be a JSON-formatted string with action and parameters:
    - {"action": "send_message", "channel": "C123456", "text": "Hello!", "thread_ts": "optional"}
    - {"action": "schedule_reminder", "channel": "C123456", "text": "Reminder text", "post_at": 1234567890}
    - {"action": "create_channel", "name": "new-channel", "is_private": false}
    """
    slack_client: Any = Field(exclude=True)
    
    def __init__(self, slack_client, **kwargs):
        super().__init__(slack_client=slack_client, **kwargs)
    
    def _run(self, action_data: str) -> str:
        """Execute Slack action based on JSON input"""
        try:
            # Parse JSON input
            data = json.loads(action_data) if isinstance(action_data, str) else action_data
            action = data.get("action")
            
            if action == "send_message":
                response = self.slack_client.chat_postMessage(
                    channel=data.get("channel"),
                    text=data.get("text"),
                    thread_ts=data.get("thread_ts")
                )
                return f"Message sent successfully: {response['ts']}"
            
            elif action == "schedule_reminder":
                response = self.slack_client.chat_scheduleMessage(
                    channel=data.get("channel"),
                    text=data.get("text"),
                    post_at=data.get("post_at")
                )
                return f"Reminder scheduled: {response['scheduled_message_id']}"
            
            elif action == "create_channel":
                response = self.slack_client.conversations_create(
                    name=data.get("name"),
                    is_private=data.get("is_private", False)
                )
                return f"Channel created: {response['channel']['id']}"
            
            return f"Action '{action}' not supported"
        
        except json.JSONDecodeError:
            return "Invalid JSON format. Please provide a valid JSON string."
        except Exception as e:
            return f"Slack integration error: {str(e)}"
    
    async def _arun(self, action_data: str) -> str:
        """Async version of _run"""
        return self._run(action_data)
