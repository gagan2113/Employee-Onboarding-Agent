import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import asyncio
import threading
import re
from datetime import datetime, timedelta
from knowledge_base import knowledge_processor
from config.config_manager import ConfigurationManager

# Import our services
from database.database import get_db
from database import models
from database.models import TaskStatus, ProfileCompletionStatus, ReminderStatus
from sqlalchemy.sql import func

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackBotHandler:
    def __init__(self):
        # Check if we have valid Slack tokens
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        app_token = os.getenv("SLACK_APP_TOKEN")
        
        self.test_mode = False
        
        # Check if tokens are placeholder values or missing
        if (not bot_token or not signing_secret or not app_token or
            bot_token.startswith("xoxb-your-") or 
            signing_secret == "your-signing-secret" or
            app_token.startswith("xapp-your-")):
            
            logger.warning("🚨 Invalid or missing Slack tokens detected. Running in TEST MODE.")
            logger.warning("📝 To enable Slack integration, update .env with valid tokens from https://api.slack.com/apps")
            self.test_mode = True
            
            # Create a mock app for test mode
            self.app = None
            self.handler = None
            return
        
        try:
            # Initialize Slack app
            self.app = App(
                token=bot_token,
                signing_secret=signing_secret
            )
            
            # Set up event handlers
            self.setup_handlers()
            
            # Socket mode handler
            self.handler = SocketModeHandler(
                self.app, 
                app_token
            )
            
            logger.info("✅ Slack bot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Slack bot: {str(e)}")
            logger.warning("🔄 Falling back to TEST MODE")
            self.test_mode = True
            self.app = None
            self.handler = None
    
    def setup_handlers(self):
        """Set up all Slack event handlers"""
        
        # Add debug logging for all events
        @self.app.event("*")
        def log_all_events(event, logger):
            logger.info(f"🔍 [DEBUG] Received event: {event.get('type', 'unknown')} - {event}")
        
        # Add a catch-all message event handler for debugging AND processing
        @self.app.event("message")
        def handle_message_events(event, say, logger):
            logger.info(f"🔍 Message event received: {event}")
            
            # Skip bot messages and messages with subtypes (except channel_join)
            if event.get('bot_id') or (event.get('subtype') and event.get('subtype') != 'channel_join'):
                return
            
            # Handle direct messages
            if event.get('channel_type') == 'im':
                logger.info(f"💬 Processing direct message: {event}")
                user_id = event['user']
                text = event.get('text', '').strip()
                text_lower = text.lower()
                
                try:
                    # Skip hello messages (let the hello handler deal with them)
                    if text_lower == 'hello':
                        return
                    
                    # Handle common queries FIRST (no database setup required)
                    if 'help' in text_lower:
                        say(self.get_help_message(user_id))
                        return
                    elif 'policy' in text_lower or 'policies' in text_lower or 'handbook' in text_lower:
                        response = knowledge_processor.query_policies(text)
                        say(f"📚 {response}")
                        return
                    
                    # For other queries, try to answer them directly
                    response = knowledge_processor.general_query(text)
                    say(f"🤖 {response}")
                    
                    # Optionally create user in database for tracking (don't block on it)
                    try:
                        if not self._user_exists_in_database(user_id):
                            logger.info(f"📝 Creating user record for: {user_id}")
                            # Create basic user record without blocking the response
                            self._create_basic_user_record(user_id)
                    except Exception as db_error:
                        logger.warning(f"⚠️ Could not create user record (non-blocking): {db_error}")
                        
                except Exception as e:
                    logger.error(f"❌ Error handling direct message: {e}")
                    say("I'm sorry, I encountered an error processing your message. Please try again or contact support.")
            
            # Handle channel messages (when bot is mentioned or specific keywords)
            elif event.get('channel_type') == 'channel':
                user_id = event.get('user')
                text = event.get('text', '').strip()
                text_lower = text.lower()
                
                # Only respond if bot is mentioned or specific keywords are used
                bot_user_id = getattr(self, '_bot_user_id', None)
                if not bot_user_id:
                    try:
                        bot_user_id = self.app.client.auth_test()["user_id"]
                        self._bot_user_id = bot_user_id
                    except Exception:
                        return
                
                # Check if bot is mentioned in the message
                if f"<@{bot_user_id}>" in text or any(keyword in text_lower for keyword in ['help', 'policy', 'policies', 'handbook', 'onboarding']):
                    logger.info(f"🏢 Processing channel message: {event}")
                    
                    try:
                        # Remove bot mention from text
                        clean_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
                        
                        if 'help' in text_lower:
                            response = f"<@{user_id}> Here's how I can help you! Send me a direct message by clicking my name for personalized onboarding assistance, or ask me about company policies here in the channel. 🤖"
                        elif 'policy' in text_lower or 'policies' in text_lower or 'handbook' in text_lower:
                            response = knowledge_processor.query_policies(clean_text or text)
                            response = f"📚 <@{user_id}> {response}"
                        else:
                            response = knowledge_processor.general_query(clean_text or text)
                            response = f"🤖 <@{user_id}> {response}"
                        
                        say(response)
                        
                    except Exception as e:
                        logger.error(f"❌ Error handling channel message: {e}")
                        say(f"<@{user_id}> Sorry, I encountered an error processing your message. Please try again or send me a direct message.")
        
        # Handle direct messages with "hello" - Enhanced 3-phase onboarding
        @self.app.message("hello")
        def handle_hello_message(message, say, logger):
            logger.info(f"📨 Received hello message: {message}")
            user_id = message['user']
            channel_id = message['channel']
            
            try:
                # Check if this is a channel message and handle appropriately
                if message.get('channel_type') == 'channel':
                    # In channels, direct users to DM for personalized onboarding
                    welcome_message = f"""👋 Hello <@{user_id}>! I'm your Employee Onboarding Agent!

📱 **For personalized onboarding assistance:**
1️⃣ Click my name: **@Employee Onboarding Agent**
2️⃣ Select **"Message"** 
3️⃣ Say **"Hello"** in our direct conversation

🤖 **Or ask me questions here about:**
• 📚 Company policies and procedures
• 🕐 Working hours and guidelines  
• 👔 Dress code information
• ❓ General company questions

💡 **Send me a DM for your complete onboarding checklist and progress tracking!**"""
                    say(welcome_message)
                    return
                
                # Continue with DM processing for personalized onboarding
                # Get or create user in database
                user = self.get_or_create_user(user_id)
                if not user:
                    say("👋 Hello! I'm having trouble accessing your information right now. Please try again in a moment.")
                    return
                
                # Check if user has completed onboarding
                if user.onboarding_completed:
                    response = f"👋 Welcome back, {user.name or 'there'}! Your onboarding is already complete. How can I help you today?"
                    say(response)
                    return
                
                # Phase 1: Profile Completeness Check
                profile_analysis = self._analyze_user_profile(user_id)
                
                if not profile_analysis.get("is_complete", False):
                    # Store profile analysis and send completion message
                    completion_message = self._create_profile_completion_message(profile_analysis)
                    say(completion_message)
                    return
                
                # Phase 2: Role-based Task Assignment
                try:
                    # Get user profile to determine role
                    user_info = self.app.client.users_info(user=user_id)
                    profile = user_info.get("user", {}).get("profile", {})
                    job_title = profile.get("title", "")
                    
                    if not job_title:
                        say("🎯 Great! Your profile looks complete. However, I need your job title to assign the right onboarding tasks. Please update your Slack profile with your job title and say 'profile updated'.")
                        return
                    
                    # Assign role-based tasks
                    if self._assign_role_based_tasks(user_id, job_title):
                        # Phase 3: Present task list and start progress monitoring
                        task_message = self._format_task_list_message(user_id)
                        
                        welcome_intro = f"""🎉 **Welcome to the team, {user.name or 'there'}!**

I'm your AI onboarding assistant. I've analyzed your profile and created a personalized onboarding plan based on your role: **{job_title}**

"""
                        
                        full_message = welcome_intro + task_message
                        say(full_message)
                        
                        # Start background monitoring for this user
                        self._initialize_task_monitoring(user_id)
                        
                    else:
                        say("❌ I encountered an issue setting up your onboarding tasks. Please contact HR or try again later.")
                    
                except Exception as e:
                    logger.error(f"Error in task assignment phase: {e}")
                    say("🤖 I encountered an issue accessing your profile. Please ensure your Slack profile is complete and try again.")
            
            except Exception as e:
                logger.error(f"Error in enhanced hello handler: {e}")
                # Fallback to simple greeting
                if message.get('channel_type') == 'im':
                    say(f"👋 Hello! I'm your Employee Onboarding Agent. How can I help you with your onboarding today?")
                else:
                    say(f"👋 Hello <@{user_id}>! I'm your Employee Onboarding Agent. How can I help you with your onboarding today?")

        # Handle "profile updated" messages
        @self.app.message("profile updated")
        def handle_profile_updated(message, say, logger):
            logger.info(f"📝 Profile updated message: {message}")
            user_id = message['user']
            
            try:
                # Re-run profile analysis
                profile_analysis = self._analyze_user_profile(user_id)
                
                if profile_analysis.get("is_complete", False):
                    say("✅ Great! Your profile is now complete. Let me set up your onboarding tasks...")
                    
                    # Get user profile to determine role
                    user_info = self.app.client.users_info(user=user_id)
                    profile = user_info.get("user", {}).get("profile", {})
                    job_title = profile.get("title", "")
                    
                    if job_title:
                        user = self.get_or_create_user(user_id)
                        if self._assign_role_based_tasks(user_id, job_title):
                            task_message = self._format_task_list_message(user_id)
                            welcome_intro = f"""🎉 **Perfect! Your onboarding is now ready.**

I've created a personalized plan based on your role: **{job_title}**

"""
                            say(welcome_intro + task_message)
                            self._initialize_task_monitoring(user_id)
                        else:
                            say("❌ I encountered an issue setting up your tasks. Please contact HR.")
                    else:
                        say("🎯 I still need your job title to assign the right tasks. Please update your Slack profile with your job title and say 'profile updated' again.")
                else:
                    # Update stored analysis and send new completion message
                    completion_message = self._create_profile_completion_message(profile_analysis)
                    completion_score = profile_analysis.get("completion_score", 0)
                    say(f"📈 Thanks for the update! Your profile is now {completion_score}% complete.\n\n{completion_message}")
                    
            except Exception as e:
                logger.error(f"Error handling profile updated: {e}")
                say("❌ I encountered an error checking your profile. Please try again.")

        # Handle app mentions in channels
        @self.app.event("app_mention")
        def handle_app_mention(body, event, say, logger):
            try:
                logger.info(f"📢 Bot mentioned: {event}")
                logger.info(f"📢 Full body: {body}")
                
                user_id = event.get('user')
                text = event.get('text', '').lower()
                
                if not user_id:
                    logger.error("No user_id in app_mention event")
                    return
                
                # Enhanced greeting for mentions
                if 'hello' in text or 'hi' in text:
                    response = f"""👋 Hi <@{user_id}>! I'm your Employee Onboarding Agent!
                    
📱 **For the best experience, please send me a direct message:**
1️⃣ Click my name: **@Employee Onboarding Agent**
2️⃣ Select **"Message"**
3️⃣ Say **"Hello"**

I'll then provide your personalized onboarding experience! 🚀"""
                    say(response)
                    
                elif 'help' in text:
                    help_response = f"""<@{user_id}> Here's how I can help:

🤖 **Employee Onboarding Agent Help**
• 📚 Company policies and procedures
• 🕐 Working hours and guidelines  
• 👔 Dress code information
• 🤝 Onboarding guidance
• ❓ General company questions

💡 **For personalized onboarding, send me a DM and say "Hello"!**"""
                    say(help_response)
                    
                elif 'polic' in text or 'handbook' in text:
                    response = knowledge_processor.query_policies(event.get('text', ''))
                    say(f"📚 <@{user_id}> {response}")
                    
                else:
                    response = knowledge_processor.general_query(event.get('text', ''))
                    say(f"🤖 <@{user_id}> {response}")
                    
            except Exception as e:
                logger.error(f"Error in app_mention handler: {e}")
                try:
                    say(f"Sorry, I encountered an error processing your mention. Please try again or send me a direct message.")
                except Exception as say_error:
                    logger.error(f"Error sending error message: {say_error}")
        
        # Handle when any member (including bot) is added to a channel
        @self.app.event("member_joined_channel")
        def handle_member_or_bot_joined(event, say, logger):
            logger.info(f"🔍 [DEBUG] member_joined_channel event received: {event}")
            user_id = event.get("user")
            channel_id = event.get("channel")
            
            if not user_id:
                logger.error("No user_id in member_joined_channel event")
                return
            
            if not channel_id:
                logger.error("No channel_id in member_joined_channel event")
                return
            
            # Check if the bot itself was added to the channel
            try:
                bot_user_id = self.app.client.auth_test()["user_id"]
                if user_id == bot_user_id:
                    logger.info(f"🤖 Bot added to channel: {event}")
                    
                    bot_intro_message = f"""🤖 **Hello everyone!** 

I'm your **Employee Onboarding Agent** - an AI-powered assistant here to help with all things onboarding! 

🎯 **I'm here to help with:**
• 📚 Company policies and procedures
• 🕐 Working hours and leave guidelines
• 👔 Dress code information
• 🤝 Onboarding guidance and support
• 💻 Answer questions about company info
• ❓ General onboarding assistance

💡 **How to interact with me:**
• Mention me with `@Employee Onboarding Agent` followed by your question
• Send me a direct message for private conversations
• Type `help` to see all available commands

Ready to make onboarding seamless for everyone! 🚀"""
                    
                    say(
                        channel=channel_id,
                        text=bot_intro_message
                    )
                else:
                    # New user joined the channel - send welcome and DM instruction
                    logger.info(f"🎉 New member joined channel: {event}")
                    
                    # Get user info from Slack
                    try:
                        user_info = self.app.client.users_info(user=user_id)
                        user_name = user_info["user"]["real_name"] or user_info["user"]["display_name"] or f"<@{user_id}>"
                    except Exception as e:
                        logger.error(f"Error getting user info: {e}")
                        user_name = f"<@{user_id}>"
                    
                    # Send public welcome message with clear DM instructions
                    welcome_message = f"""🎉 **Welcome to the team, {user_name}!** 

👋 I'm your **Employee Onboarding Agent** - your AI-powered guide for getting started!

🚀 **To begin your personalized onboarding:**

📱 **Send me a direct message:**
1️⃣ Click on my name: **@Employee Onboarding Agent**
2️⃣ Select **"Message"**
3️⃣ Say **"Hello"** 

🎯 **I'll then provide you with:**
• Profile completeness check
• Role-specific onboarding tasks
• Company policies and procedures
• Progress tracking and support

**Ready to make your onboarding smooth and efficient!** 🌟

*Note: Please message me directly to start your personalized onboarding journey.*"""
                    
                    say(
                        channel=channel_id,
                        text=welcome_message
                    )
                    
                    # Try to create user in database for tracking
                    try:
                        user = self.get_or_create_user(user_id)
                        if user:
                            logger.info(f"✅ User record created/updated for {user_id}")
                        else:
                            logger.warning(f"⚠️ Could not create user record for {user_id}")
                    except Exception as db_error:
                        logger.warning(f"⚠️ Database error creating user {user_id}: {db_error}")
                    
                    logger.info(f"✅ Welcome message sent to channel for new user {user_id}")
            except Exception as e:
                logger.error(f"Error in member_joined_channel handler: {e}")
        
        # Handle channel join messages (backup handler)
        @self.app.message(lambda message: message.get("subtype") == "channel_join")
        def handle_channel_join_message(message, say, logger):
            try:
                user_id = message.get('user')
                channel_id = message.get('channel')
                
                logger.info(f"🎉 User joined channel via message event: {user_id}")
                
                # Check if the bot itself was added to the channel
                try:
                    bot_user_id = self.app.client.auth_test()["user_id"]
                    if user_id == bot_user_id:
                        logger.info(f"🤖 Bot added to channel, skipping welcome message")
                        return  # Don't process bot's own join
                except Exception as e:
                    logger.error(f"Error checking bot user ID: {e}")
                
                # Get user info
                try:
                    user_info = self.app.client.users_info(user=user_id)
                    user_name = user_info["user"]["real_name"] or user_info["user"]["display_name"] or f"<@{user_id}>"
                except Exception as e:
                    logger.error(f"Error getting user info: {e}")
                    user_name = f"<@{user_id}>"
                
                # Send welcome message directing to DM (simpler approach)
                welcome_message = f"""🎉 **Welcome to the team, {user_name}!** 

👋 I'm your **Employee Onboarding Agent** - ready to help you get started!

📱 **To begin your personalized onboarding:**
1️⃣ Click my name: **@Employee Onboarding Agent**
2️⃣ Select **"Message"**
3️⃣ Say **"Hello"**

I'll guide you through your complete onboarding process! 🚀"""
                
                say(welcome_message)
                
                # Try to create user record for tracking
                try:
                    user = self.get_or_create_user(user_id)
                    if user:
                        logger.info(f"✅ User record ready for {user_id}")
                    else:
                        logger.warning(f"⚠️ Could not create user record for {user_id}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Database error: {db_error}")
                    
            except Exception as e:
                logger.error(f"Error in channel_join message handler: {e}")

        # Task status update handlers
        @self.app.message(re.compile(r"completed task (\d+)", re.IGNORECASE))
        def handle_task_completion(message, say, logger):
            logger.info(f"📝 Task completion message: {message}")
            user_id = message['user']
            match = re.search(r"completed task (\d+)", message['text'], re.IGNORECASE)
            
            if match:
                task_number = int(match.group(1))
                success = self._update_task_status(user_id, task_number, TaskStatus.COMPLETED)
                
                if success:
                    say(f"✅ Excellent! Task {task_number} marked as completed. Great progress!")
                    # Check if all tasks are completed
                    if self._check_onboarding_completion(user_id):
                        completion_message = self._create_onboarding_completion_message(user_id)
                        say(completion_message)
                else:
                    say(f"❌ I couldn't find task {task_number} or there was an error updating it. Please try again.")

        @self.app.message(re.compile(r"started task (\d+)", re.IGNORECASE))
        def handle_task_start(message, say, logger):
            logger.info(f"📝 Task start message: {message}")
            user_id = message['user']
            match = re.search(r"started task (\d+)", message['text'], re.IGNORECASE)
            
            if match:
                task_number = int(match.group(1))
                success = self._update_task_status(user_id, task_number, TaskStatus.IN_PROGRESS)
                
                if success:
                    say(f"🚀 Great! Task {task_number} is now in progress. You've got this!")
                else:
                    say(f"❌ I couldn't find task {task_number} or there was an error updating it. Please try again.")

        @self.app.message(re.compile(r"help with task (\d+)", re.IGNORECASE))
        def handle_task_help_request(message, say, logger):
            logger.info(f"❓ Task help request: {message}")
            user_id = message['user']
            match = re.search(r"help with task (\d+)", message['text'], re.IGNORECASE)
            
            if match:
                task_number = int(match.group(1))
                help_message = self._get_task_help_details(user_id, task_number)
                say(help_message)

        @self.app.message(re.compile(r"show.*(task|progress)", re.IGNORECASE))
        def handle_show_tasks(message, say, logger):
            logger.info(f"📋 Show tasks request: {message}")
            user_id = message['user']
            task_message = self._format_task_list_message(user_id)
            say(task_message)

        # Handle when a new user joins the workspace/team
        @self.app.event("team_join")
        def handle_team_join(event, client, logger):
            """Handle when a new user joins the Slack workspace"""
            logger.info(f"🔍 [DEBUG] team_join event received: {event}")
            try:
                user_data = event.get("user", {})
                user_id = user_data.get("id")
                if not user_id:
                    logger.error("No user ID in team_join event")
                    return

                logger.info(f"🎉 New user joined the workspace: {user_id}")
                
                # Get user info
                try:
                    user_info = client.users_info(user=user_id)
                    user_name = user_info["user"]["real_name"] or user_info["user"]["display_name"] or f"<@{user_id}>"
                except Exception as e:
                    logger.error(f"Error getting user info for team_join: {e}")
                    user_name = f"<@{user_id}>"

                # Try to send a welcome DM first
                welcome_dm = f"""🎉 **Welcome to the team, {user_name}!** 

👋 I'm your **Employee Onboarding Agent** - your AI-powered guide for getting started!

🚀 **I'm here to help make your onboarding smooth and efficient:**

• 📋 Create your personalized onboarding checklist
• 📚 Answer questions about company policies  
• 🕐 Help with work schedules and procedures
• 👔 Provide dress code and workplace guidelines
• 🤝 Guide you through your role-specific tasks
• ❓ Be your 24/7 onboarding companion!

💡 **To get started, just say "Hello" to begin your personalized onboarding journey!**

**Ready to make onboarding easy? Let's get started!** ✨"""

                # Try to send a direct message
                success = self._send_dm_with_fallback(user_id, welcome_dm)
                if success:
                    logger.info(f"✅ Welcome DM sent to new user {user_id}")
                else:
                    logger.warning(f"⚠️ Could not send welcome DM to {user_id}")

                # Create user record for tracking
                try:
                    user = self.get_or_create_user(user_id)
                    if user:
                        logger.info(f"✅ User record created for new team member {user_id}")
                    else:
                        logger.warning(f"⚠️ Could not create user record for {user_id}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Database error creating user {user_id}: {db_error}")

            except Exception as e:
                logger.error(f"Error in team_join handler: {e}")
    
    def _open_dm_conversation(self, user_id: str) -> str:
        """
        Open a DM conversation with a user and return the conversation ID
        This is required before sending messages to users who haven't messaged the bot first
        """
        try:
            response = self.app.client.conversations_open(users=[user_id])
            if response["ok"]:
                conversation_id = response["channel"]["id"]
                logger.info(f"✅ Opened DM conversation with user {user_id}: {conversation_id}")
                return conversation_id
            else:
                logger.error(f"❌ Failed to open DM conversation: {response.get('error', 'Unknown error')}")
                return None
        except Exception as e:
            logger.error(f"❌ Exception opening DM conversation with {user_id}: {e}")
            return None

    def _send_dm_with_fallback(self, user_id: str, message: str, channel_id: str = None) -> bool:
        """
        Send a DM to a user with fallback to channel message if DM fails
        Returns True if message was sent successfully (either DM or fallback)
        """
        try:
            # First, try to open a DM conversation
            dm_channel = self._open_dm_conversation(user_id)
            
            if dm_channel:
                # Try to send the DM
                try:
                    self.app.client.chat_postMessage(
                        channel=dm_channel,
                        text=message
                    )
                    logger.info(f"✅ Successfully sent DM to user {user_id}")
                    return True
                except Exception as dm_error:
                    logger.warning(f"⚠️ Failed to send DM even with conversation open: {dm_error}")
            
            # DM failed, use fallback to channel if available
            if channel_id:
                fallback_message = f"""🎉 **Welcome to the team, <@{user_id}>!** 

I'm your **Employee Onboarding Agent** and I'm here to help make your first days amazing! 🌟

🤖 **I'd love to send you a personalized onboarding guide, but I need your permission first!**

📱 **To get started with your onboarding journey:**
1️⃣ Click on my name: **@Employee Onboarding Agent**
2️⃣ Select **"Message"** 
3️⃣ Say **"Hello"** or **"Start onboarding"**

🚀 **Once you message me, I can:**
• 📋 Create your personalized onboarding checklist
• 📚 Answer questions about company policies  
• 🕐 Help with work schedules and procedures
• 👔 Provide dress code and workplace guidelines
• 🤝 Guide you through your role-specific tasks
• ❓ Be your 24/7 onboarding companion!

💡 **Quick tip:** Slack requires you to message bots first for privacy - it's just one click away!

**Ready to make onboarding easy? Just send me a message to get started!** ✨"""
                
                try:
                    self.app.client.chat_postMessage(
                        channel=channel_id,
                        text=fallback_message
                    )
                    logger.info(f"✅ Sent fallback message in channel for user {user_id}")
                    return True
                except Exception as fallback_error:
                    logger.error(f"❌ Failed to send fallback message: {fallback_error}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in _send_dm_with_fallback: {e}")
            return False

    def _create_basic_user_record(self, slack_user_id: str):
        """Create a basic user record with minimal information for tracking"""
        try:
            # Use existing get_or_create_user method
            user = self.get_or_create_user(slack_user_id)
            return user is not None
            
        except Exception as e:
            logger.error(f"Error creating basic user record: {e}")
            return False

    def _initialize_task_monitoring(self, slack_user_id: str):
        """Initialize background task monitoring for user"""
        try:
            # This will be handled by the background scheduler
            # The background job will check for overdue tasks and send reminders
            logger.info(f"Task monitoring initialized for user {slack_user_id}")
            
        except Exception as e:
            logger.error(f"Error initializing task monitoring: {e}")

    def _analyze_user_profile(self, slack_user_id: str) -> dict:
        """
        Comprehensive analysis of user's Slack profile completeness
        Returns profile analysis with missing fields and completion score
        """
        try:
            # Get detailed user profile from Slack
            user_info = self.app.client.users_info(user=slack_user_id)
            user_data = user_info["user"]
            profile_data = user_data.get("profile", {})
            
            # Profile completeness check
            analysis = {
                "has_real_name": bool(user_data.get("real_name", "").strip()),
                "has_display_name": bool(user_data.get("display_name", "").strip()),
                "has_profile_image": not user_data.get("is_bot", False) and bool(profile_data.get("image_original")),
                "has_job_title": bool(profile_data.get("title", "").strip()),
                "has_department": bool(profile_data.get("fields", {}).get("department", {}).get("value", "").strip()),
                "has_phone": bool(profile_data.get("phone", "").strip()),
                "has_manager_info": bool(profile_data.get("fields", {}).get("manager", {}).get("value", "").strip()),
                "has_start_date": bool(profile_data.get("fields", {}).get("start_date", {}).get("value", "").strip()),
                "raw_profile": profile_data,
                "user_data": user_data
            }
            
            # Calculate completion score
            required_fields = ["has_real_name", "has_job_title", "has_profile_image"]
            optional_fields = ["has_display_name", "has_department", "has_phone", "has_manager_info", "has_start_date"]
            
            required_complete = sum(1 for field in required_fields if analysis[field])
            optional_complete = sum(1 for field in optional_fields if analysis[field])
            
            # Required fields count for 70%, optional for 30%
            completion_score = int((required_complete / len(required_fields)) * 70 + (optional_complete / len(optional_fields)) * 30)
            analysis["completion_score"] = completion_score
            
            # Identify missing fields
            missing_fields = []
            if not analysis["has_real_name"]:
                missing_fields.append("Real Name")
            if not analysis["has_job_title"]:
                missing_fields.append("Job Title")
            if not analysis["has_profile_image"]:
                missing_fields.append("Profile Picture")
            if not analysis["has_department"]:
                missing_fields.append("Department")
            if not analysis["has_manager_info"]:
                missing_fields.append("Manager Information")
            
            analysis["missing_fields"] = missing_fields
            analysis["is_complete"] = completion_score >= 80 and len(missing_fields) == 0
            
            # Store in database
            self._store_profile_analysis(slack_user_id, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user profile: {e}")
            return {"error": str(e), "completion_score": 0, "missing_fields": ["Unable to analyze profile"]}

    def _store_profile_analysis(self, slack_user_id: str, analysis: dict):
        """Store profile analysis results in database"""
        try:
            with next(get_db()) as db:
                # Get user ID
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                if not user:
                    return
                
                # Check if profile check record exists
                profile_check = db.query(models.UserProfileCheck).filter(
                    models.UserProfileCheck.user_id == user.id
                ).first()
                
                if not profile_check:
                    profile_check = models.UserProfileCheck(
                        user_id=user.id,
                        slack_user_id=slack_user_id
                    )
                    db.add(profile_check)
                
                # Update profile check data
                profile_check.has_real_name = analysis.get("has_real_name", False)
                profile_check.has_display_name = analysis.get("has_display_name", False)
                profile_check.has_profile_image = analysis.get("has_profile_image", False)
                profile_check.has_job_title = analysis.get("has_job_title", False)
                profile_check.has_department = analysis.get("has_department", False)
                profile_check.has_phone = analysis.get("has_phone", False)
                profile_check.has_manager_info = analysis.get("has_manager_info", False)
                profile_check.has_start_date = analysis.get("has_start_date", False)
                profile_check.profile_completion_score = analysis.get("completion_score", 0)
                profile_check.missing_fields = str(analysis.get("missing_fields", []))
                
                # Set status based on completion
                if analysis.get("is_complete", False):
                    profile_check.status = ProfileCompletionStatus.COMPLETE
                    profile_check.profile_completed_date = func.now()
                else:
                    profile_check.status = ProfileCompletionStatus.INCOMPLETE
                
                profile_check.last_checked = func.now()
                db.commit()
                
        except Exception as e:
            logger.error(f"Error storing profile analysis: {e}")

    def _create_profile_completion_message(self, analysis: dict) -> str:
        """Create user-friendly message about profile completion status"""
        missing_fields = analysis.get("missing_fields", [])
        completion_score = analysis.get("completion_score", 0)
        
        if analysis.get("is_complete", False):
            return """✅ **Great! Your profile looks complete!**

🎯 Profile completion: 100%

Now I can assign you role-specific onboarding tasks. Let me analyze your job title and get your personalized task list ready! 🚀"""
        
        else:
            missing_list = "\n".join([f"   • {field}" for field in missing_fields])
            
            return f"""📋 **Let's complete your profile first!**

🎯 Profile completion: {completion_score}%

**Missing information:**
{missing_list}

📱 **To update your profile:**
1️⃣ Click your profile picture in Slack
2️⃣ Select "Edit Profile"
3️⃣ Fill in the missing fields above
4️⃣ Save changes

⏰ **Why this matters:**
Complete profiles help me assign the right onboarding tasks for your role and ensure you get connected with the right people!

💬 **Once updated, just say "profile updated" and I'll check again!**"""

    def _assign_role_based_tasks(self, slack_user_id: str, job_title: str) -> bool:
        """
        Assign role-specific onboarding tasks based on job title
        """
        try:
            with next(get_db()) as db:
                # Get user
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                if not user:
                    logger.error(f"User not found: {slack_user_id}")
                    return False
                
                # Determine role from job title
                role = self._determine_role_from_title(job_title)
                
                # Get role-specific tasks
                tasks = self._get_role_specific_tasks(role)
                
                # Clear existing tasks for this user
                db.query(models.OnboardingTask).filter(models.OnboardingTask.user_id == user.id).delete()
                
                # Create new tasks
                for task_data in tasks:
                    task = models.OnboardingTask(
                        user_id=user.id,
                        task_name=task_data["name"],
                        task_description=task_data["description"],
                        task_category=task_data["category"],
                        role_specific=role,
                        priority=task_data["priority"],
                        due_date=func.now() + timedelta(days=task_data["due_days"]),
                        instructions=task_data["instructions"],
                        resources=str(task_data["resources"]),
                        is_mandatory=task_data["mandatory"],
                        estimated_minutes=task_data["estimated_minutes"]
                    )
                    db.add(task)
                
                db.commit()
                logger.info(f"Assigned {len(tasks)} tasks to user {slack_user_id} for role {role}")
                
                # Create reminder entries for each task
                self._create_task_reminders(user.id, db)
                
                return True
                
        except Exception as e:
            logger.error(f"Error assigning role-based tasks: {e}")
            return False

    def _determine_role_from_title(self, job_title: str) -> models.UserRole:
        """Determine user role from job title"""
        title_lower = job_title.lower()
        
        # Check AI roles first (more specific)
        if any(keyword in title_lower for keyword in ["ai engineer", "machine learning", "ml engineer", "nlp", "artificial intelligence"]):
            return models.UserRole.AI_ENGINEER
        elif any(keyword in title_lower for keyword in ["data scientist", "data analyst", "analytics"]):
            return models.UserRole.DATA_SCIENTIST
        elif any(keyword in title_lower for keyword in ["software", "developer", "engineer", "programmer", "backend", "frontend", "fullstack"]):
            return models.UserRole.SOFTWARE_DEVELOPER
        elif any(keyword in title_lower for keyword in ["hr", "human resources", "recruiter", "people"]):
            return models.UserRole.HR_ASSOCIATE
        elif any(keyword in title_lower for keyword in ["product manager", "pm", "product owner"]):
            return models.UserRole.PRODUCT_MANAGER
        elif any(keyword in title_lower for keyword in ["designer", "ux", "ui", "design"]):
            return models.UserRole.DESIGNER
        elif any(keyword in title_lower for keyword in ["marketing", "marketer", "brand", "content"]):
            return models.UserRole.MARKETING
        elif any(keyword in title_lower for keyword in ["sales", "account", "business development", "bd"]):
            return models.UserRole.SALES
        else:
            return models.UserRole.OTHER

    def _get_role_specific_tasks(self, role: models.UserRole) -> list:
        """Get list of tasks specific to a role"""
        
        base_tasks = [
            {
                "name": "Complete Profile Setup", 
                "description": "Ensure all profile information is complete and accurate",
                "category": "profile",
                "priority": 1,
                "due_days": 1,
                "instructions": "Update your Slack profile with photo, job title, department, and contact info",
                "resources": ["Slack Profile Guide"],
                "mandatory": True,
                "estimated_minutes": 15
            },
            {
                "name": "Read Employee Handbook",
                "description": "Review company policies, procedures, and guidelines", 
                "category": "training",
                "priority": 1,
                "due_days": 3,
                "instructions": "Read through the complete employee handbook and acknowledge understanding",
                "resources": ["Employee Handbook PDF", "Policy Portal"],
                "mandatory": True,
                "estimated_minutes": 60
            },
            {
                "name": "Complete Security Training",
                "description": "Complete mandatory cybersecurity awareness training",
                "category": "training", 
                "priority": 1,
                "due_days": 5,
                "instructions": "Complete online security training modules and pass the assessment",
                "resources": ["Security Training Portal"],
                "mandatory": True,
                "estimated_minutes": 45
            }
        ]
        
        if role == models.UserRole.SOFTWARE_DEVELOPER:
            base_tasks.extend([
                {
                    "name": "Development Environment Setup",
                    "description": "Set up your development environment and tools",
                    "category": "setup",
                    "priority": 1,
                    "due_days": 2,
                    "instructions": "Install IDE, Git, connect to VPN, clone repositories",
                    "resources": ["Dev Setup Guide", "GitHub Access", "VPN Instructions"],
                    "mandatory": True,
                    "estimated_minutes": 120
                },
                {
                    "name": "Code Review Guidelines",
                    "description": "Learn about our code review process and standards",
                    "category": "training",
                    "priority": 2,
                    "due_days": 5,
                    "instructions": "Read coding standards and participate in first code review",
                    "resources": ["Coding Standards Doc", "PR Template"],
                    "mandatory": True,
                    "estimated_minutes": 30
                },
                {
                    "name": "Meet with Tech Lead",
                    "description": "Schedule and complete onboarding meeting with technical lead",
                    "category": "meeting",
                    "priority": 1,
                    "due_days": 3,
                    "instructions": "Schedule 1-hour meeting to discuss projects and expectations",
                    "resources": ["Tech Lead Contact"],
                    "mandatory": True,
                    "estimated_minutes": 60
                }
            ])
            
        elif role == models.UserRole.HR_ASSOCIATE:
            base_tasks.extend([
                {
                    "name": "HRIS System Training",
                    "description": "Complete training on HR Information System",
                    "category": "training",
                    "priority": 1,
                    "due_days": 3,
                    "instructions": "Complete HRIS modules and practice common workflows",
                    "resources": ["HRIS Training Portal", "HR System Guide"],
                    "mandatory": True,
                    "estimated_minutes": 90
                },
                {
                    "name": "Compliance Training",
                    "description": "Complete HR compliance and legal requirements training",
                    "category": "training",
                    "priority": 1,
                    "due_days": 5,
                    "instructions": "Review employment law basics and company compliance procedures",
                    "resources": ["Compliance Training", "Legal Guidelines"],
                    "mandatory": True,
                    "estimated_minutes": 75
                }
            ])
            
        elif role == models.UserRole.SALES:
            base_tasks.extend([
                {
                    "name": "CRM Setup and Training",
                    "description": "Set up CRM access and complete basic training",
                    "category": "setup",
                    "priority": 1,
                    "due_days": 2,
                    "instructions": "Get CRM credentials, complete setup, and finish training modules",
                    "resources": ["CRM Guide", "Sales Training Portal"],
                    "mandatory": True,
                    "estimated_minutes": 90
                },
                {
                    "name": "Product Knowledge Quiz",
                    "description": "Complete product knowledge assessment",
                    "category": "training",
                    "priority": 1,
                    "due_days": 7,
                    "instructions": "Study product materials and pass knowledge quiz with 80% or higher",
                    "resources": ["Product Guide", "Feature Demos"],
                    "mandatory": True,
                    "estimated_minutes": 120
                }
            ])
            
        return base_tasks

    def _create_task_reminders(self, user_id: int, db):
        """Create reminder entries for user's tasks"""
        try:
            tasks = db.query(models.OnboardingTask).filter(models.OnboardingTask.user_id == user_id).all()
            
            for task in tasks:
                reminder = models.TaskReminder(
                    task_id=task.id,
                    user_id=user_id,
                    next_reminder_due=task.due_date - timedelta(days=1),  # Remind 1 day before due
                    max_reminders=2
                )
                db.add(reminder)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error creating task reminders: {e}")

    def _format_task_list_message(self, slack_user_id: str) -> str:
        """Create formatted message with user's assigned tasks"""
        try:
            with next(get_db()) as db:
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                if not user:
                    return "❌ Error: User not found"
                
                tasks = db.query(models.OnboardingTask).filter(
                    models.OnboardingTask.user_id == user.id
                ).order_by(models.OnboardingTask.priority, models.OnboardingTask.due_date).all()
                
                if not tasks:
                    return "✅ No tasks assigned yet. Let me set up your onboarding tasks!"
                
                task_message = f"""🎯 **Your Onboarding Tasks ({user.role.value.replace('_', ' ').title()})**

📋 I've created a personalized onboarding checklist for your role:

"""
                
                for i, task in enumerate(tasks, 1):
                    priority_emoji = "🔴" if task.priority == 1 else "🟡" if task.priority == 2 else "🟢"
                    due_date = task.due_date.strftime("%b %d") if task.due_date else "TBD"
                    status_emoji = "✅" if task.status == TaskStatus.COMPLETED else "⏳" if task.status == TaskStatus.IN_PROGRESS else "📝"
                    
                    task_message += f"""**{i}. {task.task_name}** {priority_emoji} {status_emoji}
   📝 {task.task_description}
   ⏰ Due: {due_date} | 🕐 Est: {task.estimated_minutes} min
   
"""
                
                task_message += """💡 **How to update task status:**
• Say "completed task 1" when you finish a task
• Say "started task 2" when you begin working
• Say "help with task 3" if you need assistance

🚀 **Let's get started! Which task would you like to begin with?**"""
                
                return task_message
                
        except Exception as e:
            logger.error(f"Error formatting task list: {e}")
            return "❌ Error loading your tasks. Please try again."
    
    def update_user_role(self, slack_user_id: str, role: str, department: str = "", manager_email: str = ""):
        """Update user role and information"""
        try:
            with next(get_db()) as db:
                user = db.query(models.User).filter(
                    models.User.slack_user_id == slack_user_id
                ).first()
                
                if not user:
                    logger.error(f"User {slack_user_id} not found for role update")
                    return False
                
                # Update user information
                try:
                    user.role = models.UserRole(role)
                except ValueError:
                    logger.warning(f"Invalid role {role}, using OTHER")
                    user.role = models.UserRole.OTHER
                    
                user.department = department
                user.manager_email = manager_email
                user.onboarding_status = models.OnboardingStatus.IN_PROGRESS
                
                db.commit()
                logger.info(f"Updated user {user.full_name} with role {role}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating user role: {str(e)}")
            return False
    
    def _handle_role_selection(self, text: str, user_id: str, say) -> bool:
        """Handle user role selection without task assignment"""
        text_lower = text.lower()
        
        # Check if user is providing role information
        role_patterns = {
            "ai_engineer": ["i'm an ai engineer", "i am an ai engineer", "ai engineer"],
            "software_developer": ["i'm a software developer", "i am a software developer", "software developer", "developer"],
            "data_scientist": ["i'm a data scientist", "i am a data scientist", "data scientist"],
            "product_manager": ["i'm a product manager", "i am a product manager", "product manager"],
            "designer": ["i'm a designer", "i am a designer", "designer"],
            "hr_associate": ["i'm an hr associate", "i am an hr associate", "hr associate", "hr"],
            "marketing": ["i'm in marketing", "i am in marketing", "marketing"],
            "sales": ["i'm in sales", "i am in sales", "sales"]
        }
        
        detected_role = None
        for role, patterns in role_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                detected_role = role
                break
        
        # Check for custom role specification
        if not detected_role and ("my role is" in text_lower):
            detected_role = "other"
        
        if detected_role:
            # Extract additional information
            department = ""
            manager_email = ""
            
            # Try to extract department
            if " in the " in text_lower:
                dept_match = re.search(r'in the (\w+)', text_lower)
                if dept_match:
                    department = dept_match.group(1)
            elif " team" in text_lower:
                dept_match = re.search(r'(\w+) team', text_lower)
                if dept_match:
                    department = dept_match.group(1)
            
            # Try to extract manager email
            email_match = re.search(r'manager[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text_lower)
            if email_match:
                manager_email = email_match.group(1)
            
            # Update user role without task assignment
            success = self.update_user_role(user_id, detected_role, department, manager_email)
            
            if success:
                # Get role display name
                role_display = {
                    "ai_engineer": "AI Engineer",
                    "software_developer": "Software Developer", 
                    "data_scientist": "Data Scientist",
                    "product_manager": "Product Manager",
                    "designer": "Designer",
                    "hr_associate": "HR Associate",
                    "marketing": "Marketing",
                    "sales": "Sales",
                    "other": "Other"
                }.get(detected_role, detected_role.title())
                
                dept_text = f" in the {department} team" if department else ""
                manager_text = f"\n👨‍💼 Manager: {manager_email}" if manager_email else ""
                
                response_message = f"""✅ **Perfect! Role confirmed as {role_display}**{dept_text}{manager_text}

� **Welcome to the team!**

� **What I can help you with:**
• 📚 Answer questions about company policies
• 🕐 Provide information about working hours  
• 👔 Help with dress code questions
• 🤝 Guide you through onboarding information
• ❓ General company questions

**Need help?** Just ask me any questions naturally, or type `help` to see what I can do! 🚀"""
                
                say(response_message)
                logger.info(f"✅ Updated role for {user_id} to {detected_role}")
                return True
            else:
                say(f"✅ Thanks! I understand your role as **{role_display}**{dept_text}. Welcome to the team!")
                return True
        
        return False
    
    def _show_user_tasks(self, slack_user_id: str, say):
        """Task management is no longer available"""
        say("📋 Task management has been simplified. I can help you with company policies, onboarding questions, and general guidance instead!")
    
    def _show_user_progress(self, slack_user_id: str, say):
        """Progress tracking is no longer available"""
        say("📊 Progress tracking has been simplified. I can help you with company policies, onboarding questions, and general guidance instead!")
    
    def _mark_task_completed(self, slack_user_id: str, task_id: int, say):
        """Task completion is no longer available"""
        say("✅ Task management has been simplified. I can help you with company policies, onboarding questions, and general guidance instead!")
    
    def _mark_task_in_progress(self, slack_user_id: str, task_id: int, say):
        """Task progress is no longer available"""
        say("🔄 Task management has been simplified. I can help you with company policies, onboarding questions, and general guidance instead!")
    
    def _get_task_help(self, slack_user_id: str, task_id: int, say):
        """Task help is no longer available"""
        say("❓ Task help has been simplified. I can help you with company policies, onboarding questions, and general guidance instead!")

    def _update_task_status(self, slack_user_id: str, task_number: int, status: TaskStatus) -> bool:
        """Update the status of a specific task"""
        try:
            with next(get_db()) as db:
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                if not user:
                    return False
                
                # Get tasks ordered by priority and due date (same as displayed)
                tasks = db.query(models.OnboardingTask).filter(
                    models.OnboardingTask.user_id == user.id
                ).order_by(models.OnboardingTask.priority, models.OnboardingTask.due_date).all()
                
                if not tasks or task_number < 1 or task_number > len(tasks):
                    return False
                
                # Update the specific task (task_number is 1-indexed)
                target_task = tasks[task_number - 1]
                target_task.status = status
                
                if status == TaskStatus.COMPLETED:
                    target_task.completed_at = func.now()
                elif status == TaskStatus.IN_PROGRESS:
                    target_task.started_at = func.now()
                
                db.commit()
                logger.info(f"Updated task {task_number} for user {slack_user_id} to status {status}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return False

    def _check_onboarding_completion(self, slack_user_id: str) -> bool:
        """Check if all mandatory tasks are completed"""
        try:
            with next(get_db()) as db:
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                if not user:
                    return False
                
                incomplete_mandatory = db.query(models.OnboardingTask).filter(
                    models.OnboardingTask.user_id == user.id,
                    models.OnboardingTask.is_mandatory == True,
                    models.OnboardingTask.status != TaskStatus.COMPLETED
                ).count()
                
                if incomplete_mandatory == 0:
                    # Mark user as onboarding completed
                    user.onboarding_completed = True
                    user.onboarding_completed_at = func.now()
                    db.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking onboarding completion: {e}")
            return False

    def _create_onboarding_completion_message(self, slack_user_id: str) -> str:
        """Create congratulatory message for completed onboarding"""
        try:
            with next(get_db()) as db:
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                if not user:
                    return "🎉 Congratulations on completing your onboarding!"
                
                return f"""🎉🎊 **CONGRATULATIONS {user.name or 'there'}!** 🎊🎉

✅ **You've successfully completed your onboarding!** 

🌟 **What you've accomplished:**
• ✅ All mandatory tasks completed
• 🎯 Role-specific training finished  
• 📚 Company policies reviewed
• 🔧 Systems and tools set up

🚀 **You're now fully onboarded and ready to make an impact!**

💫 **Next steps:**
• Start working on your first projects
• Connect with your team members
• Continue learning and growing with us

🤖 **I'm still here if you need help!** You can always ask me about:
• Company policies and procedures
• Team information and contacts
• Any questions about your role

**Welcome to the team! We're excited to have you aboard!** 🚢⚓"""
                
        except Exception as e:
            logger.error(f"Error creating completion message: {e}")
            return "🎉 Congratulations on completing your onboarding!"

    def _get_task_help_details(self, slack_user_id: str, task_number: int) -> str:
        """Get detailed help for a specific task"""
        try:
            with next(get_db()) as db:
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                if not user:
                    return "❌ Error: User not found"
                
                tasks = db.query(models.OnboardingTask).filter(
                    models.OnboardingTask.user_id == user.id
                ).order_by(models.OnboardingTask.priority, models.OnboardingTask.due_date).all()
                
                if not tasks or task_number < 1 or task_number > len(tasks):
                    return f"❌ Task {task_number} not found. Please check your task list."
                
                task = tasks[task_number - 1]
                
                due_date = task.due_date.strftime("%B %d, %Y") if task.due_date else "No due date"
                
                help_message = f"""❓ **Help for Task {task_number}: {task.task_name}**

📝 **Description:** {task.task_description}

📋 **Instructions:**
{task.instructions}

⏰ **Due Date:** {due_date}
🕐 **Estimated Time:** {task.estimated_minutes} minutes
🔥 **Priority:** {"High" if task.priority == 1 else "Medium" if task.priority == 2 else "Low"}

📚 **Resources:**"""
                
                if task.resources:
                    try:
                        resources = eval(task.resources) if isinstance(task.resources, str) else task.resources
                        for resource in resources:
                            help_message += f"\n• {resource}"
                    except:
                        help_message += f"\n• {task.resources}"
                else:
                    help_message += "\n• Contact your manager or HR for specific resources"
                
                help_message += f"""

💡 **Need more help?**
• Contact your manager or HR team
• Ask me other questions about company policies
• Say "show my tasks" to see your full task list

🚀 **When ready, say "started task {task_number}" or "completed task {task_number}"**"""
                
                return help_message
                
        except Exception as e:
            logger.error(f"Error getting task help: {e}")
            return f"❌ Error retrieving help for task {task_number}. Please try again."

    def get_or_create_user(self, slack_user_id: str):
        """Get existing user or create new user in database"""
        try:
            with next(get_db()) as db:
                # Try to get existing user
                user = db.query(models.User).filter(models.User.slack_user_id == slack_user_id).first()
                
                if user:
                    return user
                
                # Create new user if not exists
                try:
                    # Get user info from Slack
                    user_info = self.app.client.users_info(user=slack_user_id)
                    profile = user_info.get("user", {}).get("profile", {})
                    
                    user = models.User(
                        slack_user_id=slack_user_id,
                        name=profile.get("real_name", ""),
                        email=profile.get("email", ""),
                        role=models.UserRole.OTHER,  # Default role
                        department="",
                        manager_email="",
                        onboarding_completed=False
                    )
                    
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    
                    logger.info(f"Created new user: {slack_user_id}")
                    return user
                    
                except Exception as slack_error:
                    logger.warning(f"Could not get Slack profile for {slack_user_id}: {slack_error}")
                    # Create minimal user record
                    user = models.User(
                        slack_user_id=slack_user_id,
                        name="",
                        email="",
                        role=models.UserRole.OTHER,
                        department="",
                        manager_email="",
                        onboarding_completed=False
                    )
                    
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    
                    logger.info(f"Created minimal user record: {slack_user_id}")
                    return user
                    
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return None
    
    def get_help_message(self, user_id):
        """Generate help message"""
        return f"""
🤖 **Employee Onboarding Agent Help** <@{user_id}>

I'm powered by **GROQ AI** and can intelligently answer your questions!

I can help you with:
•  **Policies** - Get specific answers about company policies and handbook
• 👥 **Team** - Information about your team and onboarding
• ❓ **Questions** - Ask me anything about the company in natural language
• 🤝 **Guidance** - Get help with onboarding processes and company info

**Try asking me naturally:**
• "How do I submit my ID documents?"
• "What's the company's leave policy?"
• "What are the work hours?"
• "I'm a software developer"
• "What's the dress code?"
• "Tell me about the orientation"

🧠 **AI-Powered Features:**
• Intelligent responses using GROQ LLM
• Content sourced from knowledge base
• Context-aware answers and guidance
• Reminder system for overdue tasks
• Manager escalation for incomplete tasks

🔄 **Automatic Task Management:**
• Tasks assigned automatically when you join
• Personal reminders sent for overdue tasks
• Manager notified if tasks remain incomplete
• Progress tracking with completion metrics

Just mention me in a channel or send me a direct message!
"""
    
    def _user_exists_in_database(self, slack_user_id: str) -> bool:
        """Check if user already exists in our database"""
        try:
            with next(get_db()) as db:
                existing_user = db.query(models.User).filter(
                    models.User.slack_user_id == slack_user_id
                ).first()
                return existing_user is not None
        except Exception as e:
            logger.error(f"Error checking if user exists: {e}")
            return False
    
    def _setup_new_employee_onboarding(self, user_id: str, say):
        """Set up onboarding for a new employee who messaged the bot"""
        try:
            # Get user info from Slack
            try:
                user_info = self.app.client.users_info(user=user_id)
                user_name = user_info["user"]["real_name"] or user_info["user"]["display_name"] or f"User_{user_id}"
                user_email = user_info["user"]["profile"].get("email", "")
            except Exception as e:
                logger.error(f"Error getting user info: {e}")
                user_name = f"User_{user_id}"
                user_email = ""
            
            # Create user in database
            user = self.get_or_create_user(user_id)
            user_created = user is not None
            
            # Send welcome message with role selection
            welcome_message = f"""🎉 **Welcome to the team, {user_name}!**

I'm your onboarding assistant! I'll help you get settled in and complete all the necessary tasks for your first few weeks.

📝 **To get started, I need to know your role so I can assign the right tasks for you.**

Please reply with your job role by typing one of these options:

� **AI Engineer** - `I'm an AI Engineer`
🔹 **Software Developer** - `I'm a Software Developer`  
� **Data Scientist** - `I'm a Data Scientist`
🔹 **Product Manager** - `I'm a Product Manager`
🔹 **Designer** - `I'm a Designer`
� **HR Associate** - `I'm an HR Associate`
� **Marketing** - `I'm in Marketing`
� **Sales** - `I'm in Sales`
🔹 **Other** - `My role is [specify your role]`

**Optional:** You can also include your department and manager's email like this:
`I'm a Software Developer in the Backend team, manager: manager@company.com`

Once you tell me your role, I'll create your personalized onboarding checklist! 🚀"""
            
            say(welcome_message)
            logger.info(f"✅ Set up initial onboarding for new employee: {user_name}")
                
        except Exception as e:
            logger.error(f"Error setting up new employee onboarding: {e}")
            say("👋 Welcome! I'm having trouble setting up your onboarding. Please try again or contact support.")

    def start(self):
        """Start the Slack bot"""
        if self.test_mode:
            logger.info("🧪 Slack bot running in TEST MODE (no real Slack connection)")
            logger.info("📋 Task management features are still available via API endpoints")
            return
            
        if not self.handler:
            logger.error("❌ Cannot start Slack bot - handler not initialized")
            return
            
        try:
            logger.info("🚀 Starting Slack bot...")
            logger.info(f"🔑 Bot Token: {os.getenv('SLACK_BOT_TOKEN', 'Not set')[:20]}...")
            logger.info(f"🔑 App Token: {os.getenv('SLACK_APP_TOKEN', 'Not set')[:20]}...")
            
            # Start in a separate thread to not block the main application
            self.handler.start()
            
        except Exception as e:
            logger.error(f"❌ Failed to start Slack bot: {e}")
            logger.warning("🔄 Continuing in TEST MODE")
            self.test_mode = True
    
    def start_async(self):
        """Start the bot in a separate thread"""
        def run():
            self.start()
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        logger.info("🚀 Slack bot started in background thread")

# Test the bot independently
if __name__ == "__main__":
    print("🧪 Testing Slack Bot...")
    bot = SlackBotHandler()
    print("✅ Bot initialized")
    bot.start()