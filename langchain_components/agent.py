from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_components.tools import DatabaseQueryTool, SlackIntegrationTool
from typing import List, Dict, Any
import json

class OnboardingAgent:
    """Main LangChain agent for handling onboarding conversations"""
    
    def __init__(self, llm, db_session, slack_client):
        self.llm = llm
        self.db = db_session
        self.slack_client = slack_client
        
        # Initialize tools
        self.tools = [
            DatabaseQueryTool(db_session),
            SlackIntegrationTool(slack_client)
        ]
        
        # Initialize memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10  # Keep last 10 exchanges
        )
        
        # Initialize agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            max_iterations=3
        )
        
        # System prompt
        self.system_prompt = """You are a helpful Employee Onboarding Assistant for a technology company. 
        Your role is to guide new employees through their onboarding process in a friendly, professional, and efficient manner.

        Key responsibilities:
        - Welcome new employees and make them feel comfortable
        - Collect necessary personal and professional information
        - Share relevant company policies and guidelines
        - Provide onboarding guidance and support
        - Introduce company culture and values
        - Answer questions about company processes
        - Connect employees with mentors/buddies
        - Provide helpful onboarding information
        - Collect feedback and provide assistance

        Communication style:
        - Be warm, welcoming, and encouraging
        - Use clear, concise language
        - Include relevant emojis to make interactions friendly
        - Ask one question at a time to avoid overwhelming
        - Provide step-by-step guidance
        - Be patient and understanding

        When users ask questions:
        - First check if it's onboarding-related using available tools
        - Provide accurate, helpful information
        - If you don't know something, be honest and offer to connect them with the right person
        - Always maintain a positive, supportive tone

        Remember: You're often the first impression new employees have of the company culture!
        """
    
    def process_message(self, user_id: str, message: str, context: Dict[str, Any] = None) -> str:
        """Process incoming message and generate response"""
        
        # Add context to the conversation
        context_msg = ""
        if context:
            context_msg = f"\nContext: User ID: {user_id}"
            if context.get("current_step"):
                context_msg += f", Current Step: {context['current_step']}"
            if context.get("user_info"):
                context_msg += f", User Info: {json.dumps(context['user_info'])}"
        
        # Prepare the full message with context
        full_message = f"{self.system_prompt}\n{context_msg}\n\nUser: {message}"
        
        try:
            response = self.agent.run(full_message)
            return response
        except Exception as e:
            return f"I apologize, but I encountered an error processing your message. Please try again or contact support. Error: {str(e)}"
    
    def handle_faq(self, question: str) -> str:
        """Handle frequently asked questions"""
        
        faq_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                """You are an expert at answering employee onboarding questions. 
                Based on the question, provide a helpful, accurate response about:
                - Company policies and procedures
                - Tool access and setup
                - Benefits and perks
                - Team structure and contacts
                - Work processes and guidelines
                
                If you don't have specific information, acknowledge this and suggest who to contact."""
            ),
            HumanMessagePromptTemplate.from_template("{question}")
        ])
        
        try:
            formatted_prompt = faq_prompt.format_messages(question=question)
            response = self.llm(formatted_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return "I'm sorry, I couldn't process that question right now. Please contact HR for assistance."
    
    def generate_progress_summary(self, user_id: str) -> str:
        """Generate a progress summary for the user"""
        
        try:
            # Get user info from database
            user_info = self.tools[0]._run("user_info", user_id)
            
            summary_prompt = f"""
            Based on the following user information, create a friendly onboarding status summary:
            
            User Info: {user_info}
            
            Include:
            - Welcome message with user's name and role
            - Current onboarding status
            - General guidance and support
            - Next steps for onboarding
            - Encouragement and available help
            
            Keep it positive and motivating!
            """
            
            response = self.llm(summary_prompt)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            return "I'm having trouble generating your progress summary. Please try again later."
    
    def create_personalized_response(self, user_id: str, message_type: str, **kwargs) -> str:
        """Create personalized responses based on user data"""
        
        try:
            # Get user information
            user_info = self.tools[0]._run("user_info", user_id)
            
            prompts = {
                "welcome": f"""Create a personalized welcome message for: {user_info}
                           Include their name, role, and express excitement about them joining the team.""",
                
                "reminder": f"""Create a friendly reminder message for: {user_info}
                            About: {kwargs.get('reminder_about', 'completing pending tasks')}
                            Keep it encouraging and helpful.""",
                
                "congratulations": f"""Create a congratulatory message for: {user_info}
                                   For: {kwargs.get('achievement', 'completing onboarding')}
                                   Make it celebratory and motivating."""
            }
            
            if message_type in prompts:
                response = self.llm(prompts[message_type])
                return response.content if hasattr(response, 'content') else str(response)
            else:
                return "I'm not sure how to create that type of message."
                
        except Exception as e:
            return "I'm having trouble creating a personalized response. Please try again."
