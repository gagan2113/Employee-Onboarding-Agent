from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, AIMessage
from workflows.state import OnboardingState, OnboardingStep
from database.models import User, OnboardingProgress, UserRole
from database.database import get_db
from sqlalchemy.orm import Session
import json
from datetime import datetime, timedelta

class OnboardingNodes:
    def __init__(self, llm, slack_client, db_session: Session):
        self.llm = llm
        self.slack_client = slack_client
        self.db = db_session
    
    def welcome_node(self, state: OnboardingState) -> OnboardingState:
        """Welcome new employee and start onboarding"""
        user = self.db.query(User).filter(User.slack_user_id == state.user_id).first()
        
        welcome_message = f"""
🎉 Welcome to the team, {user.full_name if user else 'there'}! 

I'm your onboarding assistant, and I'm here to guide you through your first days at the company. 

We'll cover everything you need to know:
• Personal information setup
• Company policies and guidelines  
• Tool access and accounts
• Company culture and values
• Your role-specific roadmap
• Meeting your mentor/buddy

Let's get started! Type 'ready' when you're ready to begin.
        """
        
        # Send welcome message to Slack
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=welcome_message
        )
        
        state.completed_steps.append(OnboardingStep.WELCOME)
        state.current_step = OnboardingStep.COLLECT_INFO
        
        return state
    
    def collect_info_node(self, state: OnboardingState) -> OnboardingState:
        """Collect personal and professional information"""
        user = self.db.query(User).filter(User.slack_user_id == state.user_id).first()
        
        if not user:
            # Create new user record
            info_form = """
📝 Let's collect some basic information to personalize your experience:

Please provide the following details:
1. Full Name:
2. Email:
3. Role/Position:
4. Department:
5. Manager's Name:
6. Location (City, Country):
7. Start Date:

You can provide this information in any format that's comfortable for you!
            """
        else:
            # User exists, confirm information
            info_form = f"""
📝 I have some information about you. Please confirm or update:

1. Full Name: {user.full_name}
2. Email: {user.email or 'Not provided'}
3. Role: {user.role.value if user.role else 'Not provided'}
4. Department: {user.department or 'Not provided'}
5. Manager: {user.manager_slack_id or 'Not provided'}
6. Location: {user.location or 'Not provided'}
7. Start Date: {user.start_date or 'Not provided'}

Reply with 'confirm' if this is correct, or provide any updates needed.
            """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=info_form
        )
        
        return state
    
    def share_policies_node(self, state: OnboardingState) -> OnboardingState:
        """Share relevant company policies based on role"""
        user = self.db.query(User).filter(User.slack_user_id == state.user_id).first()
        
        policies_message = f"""
📋 **Company Policies & Guidelines**

As a {user.role.value.replace('_', ' ').title() if user.role else 'team member'}, here are the key policies you should know:

**General Policies:**
• Code of Conduct
• Data Privacy & Security
• Remote Work Guidelines
• Communication Standards

**Role-Specific Guidelines:**
{self._get_role_specific_policies(user.role if user else None)}

**Important Resources:**
• Employee Handbook: [Link]
• IT Security Guidelines: [Link]
• Benefits Portal: [Link]

Please take time to review these. Reply 'reviewed' when you've gone through them.
        """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=policies_message
        )
        
        state.completed_steps.append(OnboardingStep.SHARE_POLICIES)
        state.current_step = OnboardingStep.TOOL_ACCESS
        
        return state
    
    def tool_access_node(self, state: OnboardingState) -> OnboardingState:
        """Ensure access to necessary tools and accounts"""
        user = self.db.query(User).filter(User.slack_user_id == state.user_id).first()
        
        tools_message = f"""
🔧 **Tool Access & Account Setup**

Let's make sure you have access to all the tools you need:

**Essential Tools for Everyone:**
• ✅ Slack (You're here!)
• 📧 Email Account
• 🗓️ Calendar System
• 💼 HR Portal

**Role-Specific Tools:**
{self._get_role_specific_tools(user.role if user else None)}

**Action Items:**
1. Check your email for account setup instructions
2. Log into each system to verify access
3. Set up your profile/avatar where applicable
4. Update your calendar with team meetings

Reply 'tools-ready' when you've completed the setup!
        """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=tools_message
        )
        
        state.completed_steps.append(OnboardingStep.TOOL_ACCESS)
        state.current_step = OnboardingStep.CULTURE_INTRO
        
        return state
    
    def culture_intro_node(self, state: OnboardingState) -> OnboardingState:
        """Introduce company culture and values"""
        culture_message = """
🌟 **Company Culture & Values**

Welcome to our amazing company culture! Here's what makes us special:

**Our Core Values:**
• Innovation & Creativity
• Collaboration & Teamwork  
• Integrity & Transparency
• Customer-Centricity
• Continuous Learning

**How We Work:**
• Open communication and feedback
• Flexible work arrangements
• Regular team building activities
• Learning & development opportunities
• Work-life balance

**Getting Involved:**
• Join our Slack channels (#general, #random, #tech-talks)
• Attend weekly all-hands meetings
• Participate in lunch & learns
• Join interest-based groups

**Fun Facts:**
• We have a company dog policy! 🐕
• Monthly game nights
• Annual company retreat
• Unlimited learning budget

Ready to dive into your role-specific roadmap? Reply 'culture-ready'!
        """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=culture_message
        )
        
        state.completed_steps.append(OnboardingStep.CULTURE_INTRO)
        state.current_step = OnboardingStep.ASSIGN_MENTOR
        
        return state
    
    def assign_mentor_node(self, state: OnboardingState) -> OnboardingState:
        """Assign and introduce mentor/buddy"""
        user = self.db.query(User).filter(User.slack_user_id == state.user_id).first()
        
        mentor_message = f"""
👥 **Meet Your Onboarding Buddy!**

I'd like to introduce you to your onboarding buddy who will help you settle in:

**Your Buddy:** {user.manager_slack_id or 'Sarah Johnson'} 
**Role:** Senior {user.role.value.replace('_', ' ').title() if user.role else 'Team Member'}
**Experience:** 3+ years at the company

**What Your Buddy Will Help With:**
• Answer day-to-day questions
• Introduce you to the team
• Share insider tips and best practices
• Be your go-to person for anything!

I'm setting up an introduction channel for you both. You should receive an invitation shortly.

**First Buddy Meeting:** Scheduled for tomorrow at 2 PM
• 30-minute coffee chat
• Get to know each other
• Q&A session

Looking forward to seeing you both connect! Reply 'mentor-ready' to continue.
        """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=mentor_message
        )
        
        state.completed_steps.append(OnboardingStep.ASSIGN_MENTOR)
        state.current_step = OnboardingStep.TRACK_PROGRESS
        
        return state
    
    def track_progress_node(self, state: OnboardingState) -> OnboardingState:
        """Track and update onboarding progress"""
        user = self.db.query(User).filter(User.slack_user_id == state.user_id).first()
        
        if user:
            progress = self.db.query(OnboardingProgress).filter(OnboardingProgress.user_id == user.id).first()
            if not progress:
                progress = OnboardingProgress(
                    user_id=user.id,
                    current_step=state.current_step.value,
                    completed_steps=json.dumps([step.value for step in state.completed_steps]),
                    completion_percentage=len(state.completed_steps) * 10
                )
                self.db.add(progress)
            else:
                progress.current_step = state.current_step.value
                progress.completed_steps = json.dumps([step.value for step in state.completed_steps])
                progress.completion_percentage = len(state.completed_steps) * 10
            
            self.db.commit()
        
        progress_message = f"""
📊 **Your Onboarding Progress**

Great job! Here's where you stand:

Progress: {len(state.completed_steps) * 10}% Complete
✅ Completed Steps: {len(state.completed_steps)}
🎯 Remaining Steps: {10 - len(state.completed_steps)}

**Completed:**
{chr(10).join([f'• {step.value.replace("_", " ").title()}' for step in state.completed_steps])}

**Up Next:**
• Daily check-ins and task completion
• Weekly progress reviews
• Feedback collection

Keep up the excellent work! I'll send you daily reminders and check-ins.
        """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=progress_message
        )
        
        return state
    
    def collect_feedback_node(self, state: OnboardingState) -> OnboardingState:
        """Collect feedback about onboarding experience"""
        feedback_message = """
📝 **Onboarding Feedback**

We'd love to hear about your onboarding experience! Your feedback helps us improve for future hires.

**Quick Survey:**
1. How would you rate your onboarding experience? (1-5 stars)
2. What was most helpful during onboarding?
3. What could we improve?
4. How well-prepared do you feel for your role?
5. Any additional comments or suggestions?

Please share your thoughts - your feedback is valuable to us!
        """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=feedback_message
        )
        
        state.completed_steps.append(OnboardingStep.COLLECT_FEEDBACK)
        state.current_step = OnboardingStep.COMPLETION
        
        return state
    
    def completion_node(self, state: OnboardingState) -> OnboardingState:
        """Mark onboarding as complete and congratulate"""
        user = self.db.query(User).filter(User.slack_user_id == state.user_id).first()
        
        if user:
            user.onboarding_status = "completed"
            progress = self.db.query(OnboardingProgress).filter(OnboardingProgress.user_id == user.id).first()
            if progress:
                progress.completion_percentage = 100
            self.db.commit()
        
        completion_message = f"""
🎉 **Congratulations! Onboarding Complete!** 🎉

{user.full_name if user else 'You'}, you've successfully completed the onboarding process!

**What You've Accomplished:**
✅ Personal setup complete
✅ Company policies reviewed
✅ Tool access configured
✅ Culture introduction received
✅ First-week tasks assigned
✅ Mentor connected
✅ Progress tracked
✅ Feedback provided

**You're Now Ready To:**
• Dive into your role confidently
• Collaborate effectively with your team
• Access all necessary tools and resources
• Contribute to our amazing company culture

**What's Next:**
• Your manager will schedule a 30-day check-in
• Continue with your assigned tasks and projects
• Don't hesitate to reach out with questions
• Enjoy your journey with us!

Welcome to the team! We're excited to see what you'll accomplish! 🚀
        """
        
        self.slack_client.chat_postMessage(
            channel=state.user_id,
            text=completion_message
        )
        
        state.completed_steps.append(OnboardingStep.COMPLETION)
        
        return state
    
    def _get_role_specific_policies(self, role: UserRole) -> str:
        """Get role-specific policies"""
        policies = {
            UserRole.AI_ENGINEER: "• AI Ethics Guidelines\n• Data Handling Protocols\n• Model Deployment Standards",
            UserRole.SOFTWARE_DEVELOPER: "• Code Review Process\n• Git Workflow Guidelines\n• Security Best Practices",
            UserRole.HR_ASSOCIATE: "• Confidentiality Agreements\n• GDPR Compliance\n• Employee Relations Guidelines",
            UserRole.PRODUCT_MANAGER: "• Product Development Process\n• Customer Data Guidelines\n• Feature Flag Protocols"
        }
        return policies.get(role, "• General best practices\n• Team collaboration guidelines")
    
    def _get_role_specific_tools(self, role: UserRole) -> str:
        """Get role-specific tools"""
        tools = {
            UserRole.AI_ENGINEER: "• 🤖 Jupyter Hub\n• 📊 MLflow\n• ☁️ AWS/GCP Console\n• 🐙 GitHub",
            UserRole.SOFTWARE_DEVELOPER: "• 💻 VS Code/IDE\n• 🐙 GitHub\n• 🐳 Docker\n• 📊 Monitoring Tools",
            UserRole.HR_ASSOCIATE: "• 👥 HRIS System\n• 📋 ATS Platform\n• 💰 Payroll System\n• 📊 Analytics Dashboard",
            UserRole.PRODUCT_MANAGER: "• 📋 Jira/Asana\n• 📊 Analytics Tools\n• 🎨 Figma\n• 💬 Customer Feedback Tools"
        }
        return tools.get(role, "• 💻 Standard productivity tools\n• 📊 Team collaboration platforms")
