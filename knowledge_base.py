import os
import json
import logging
from langchain_components.groq_llm import GroqLLMWrapper
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class KnowledgeBaseProcessor:
    """
    Intelligent knowledge base processor using GROQ API
    Processes queries against config/policies_config.json file
    """
    
    def __init__(self):
        self.llm = GroqLLMWrapper(temperature=0.2)  # Lower temperature for focused responses
        self.hr_data = self._load_hr_data()
        
        logger.info("✅ Knowledge Base Processor initialized with policies config")
    
    def _load_hr_data(self):
        """Load and return HR data from config files"""
        try:
            from config.config_manager import ConfigurationManager
            config_manager = ConfigurationManager()
            
            # Load policies from config
            policies_data = config_manager.policies_config
            logger.info("📄 Loaded HR data from config/policies_config.json")
            return policies_data
        except Exception as e:
            logger.error(f"❌ Error loading HR policies config: {e}")
            return {}
    
    def _preprocess_query(self, user_query):
        """Preprocess user query to determine the type of information needed"""
        query_lower = user_query.lower()
        
        # Map queries to HR data categories
        if any(term in query_lower for term in ['work hours', 'working hours', 'office hours', 'schedule', 'time']):
            return "working_hours"
        elif any(term in query_lower for term in ['leave policy', 'leave', 'vacation', 'time off', 'sick leave', 'casual leave']):
            return "attendance_leave"
        elif any(term in query_lower for term in ['dress code', 'dress', 'attire', 'clothing']):
            return "dress_code"
        elif any(term in query_lower for term in ['harassment', 'anti-harassment', 'complaint']):
            return "anti_harassment"
        elif any(term in query_lower for term in ['travel', 'travel policy', 'reimbursement', 'expenses']):
            return "travel_policy"
        elif any(term in query_lower for term in ['technology', 'laptop', 'device', 'asset', 'computer']):
            return "technology_asset"
        elif any(term in query_lower for term in ['separation', 'notice period', 'resignation', 'termination']):
            return "separation_policy"
        elif any(term in query_lower for term in ['form', 'employee form', 'hr form', 'information form']):
            return "hr_forms"
        elif any(term in query_lower for term in ['documents', 'id documents', 'submit documents', 'mail']):
            return "sample_mails"
        elif any(term in query_lower for term in ['orientation', 'onboarding', 'welcome']):
            return "orientation"
        else:
            return "general"
    
    def _extract_relevant_data(self, query_type):
        """Extract relevant data based on query type"""
        if not self.hr_data:
            return "No HR policy data available."
        
        # Get company policies from new config structure
        policies = self.hr_data.get("company_policies", {})
        faqs = self.hr_data.get("common_faqs", {})
        
        # Map old query types to new policy keys
        policy_mapping = {
            "working_hours": "working_hours",
            "attendance_leave": "leave_policy", 
            "dress_code": "dress_code",
            "anti_harassment": "anti_harassment",
            "travel_policy": "benefits",  # Travel info might be in benefits
            "technology_asset": "technology_use",
            "separation_policy": "benefits",  # Separation info might be in benefits
            "hr_forms": "general",
            "sample_mails": "general",
            "orientation": "general"
        }
        
        # Get the mapped policy key
        policy_key = policy_mapping.get(query_type, query_type)
        
        # Return the specific policy data
        if policy_key in policies:
            return policies[policy_key]
        elif query_type == "general":
            # Return all policies for general queries
            return {"policies": policies, "faqs": faqs}
        else:
            # If specific policy not found, return general info
            return {"content": "I can help you with company policies, procedures, and general HR information. Please ask about specific topics like working hours, leave policy, dress code, etc."}
    
    def _format_data_for_response(self, data):
        """Format JSON data into readable text"""
        if isinstance(data, dict):
            formatted_text = []
            for key, value in data.items():
                # Clean up key formatting
                clean_key = key.replace("_", " ").title()
                if isinstance(value, dict):
                    formatted_text.append(f"**{clean_key}:**")
                    for sub_key, sub_value in value.items():
                        clean_sub_key = sub_key.replace("_", " ").title()
                        formatted_text.append(f"  • {clean_sub_key}: {sub_value}")
                else:
                    formatted_text.append(f"**{clean_key}:** {value}")
            return "\n".join(formatted_text)
        else:
            return str(data)
    
    def query_policies(self, user_query):
        """
        Process user query against company policies using GROQ
        """
        # Preprocess the query
        query_type = self._preprocess_query(user_query)
        
        # Extract relevant data
        relevant_data = self._extract_relevant_data(query_type)
        
        if not relevant_data:
            return "I couldn't find specific information about that policy. Please contact HR for assistance."
        
        # Format data for the prompt
        formatted_data = self._format_data_for_response(relevant_data)
        
        system_prompt = """You are a helpful HR assistant. Answer the user's question based ONLY on the provided HR policy data. 
        Be concise and direct. Provide specific information from the data."""
        
        user_prompt = f"""
        Question: {user_query}
        
        Relevant HR Policy Data:
        {formatted_data}
        
        Provide a brief, direct answer based only on the data above.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            logger.info(f"📚 Generated policy response for query: {user_query[:50]}...")
            return response.content
            
        except Exception as e:
            logger.error(f"❌ Error processing policy query: {e}")
            return "I'm sorry, I couldn't process your policy question right now. Please contact HR for assistance."
    
    def query_forms(self, user_query):
        """
        Process user query against HR forms and orientation info using GROQ
        """
        # Preprocess the query
        query_type = self._preprocess_query(user_query)
        
        # Extract relevant data
        if query_type in ["hr_forms", "sample_mails", "orientation"]:
            relevant_data = self._extract_relevant_data(query_type)
        else:
            # Default to forms and mails for form-related queries
            relevant_data = {
                "forms": self.hr_data.get("HR_Forms", {}),
                "mails": self.hr_data.get("Sample_Mails", {})
            }
        
        if not relevant_data:
            return "I couldn't find specific form information. Please contact HR for assistance."
        
        # Format data for the prompt
        formatted_data = self._format_data_for_response(relevant_data)
        
        system_prompt = """You are an onboarding assistant. Help employees with their forms and documents based ONLY on the provided data.
        Be clear and actionable. Provide specific information about forms, documents, or procedures."""
        
        user_prompt = f"""
        Question: {user_query}
        
        Relevant Form/Document Data:
        {formatted_data}
        
        Provide a helpful, concise answer based only on the data above.
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            logger.info(f"📋 Generated form response for query: {user_query[:50]}...")
            return response.content
            
        except Exception as e:
            logger.error(f"❌ Error processing form query: {e}")
            return "I'm sorry, I couldn't process your form question right now. Please contact HR for assistance."
    
    def general_query(self, user_query):
        """
        Process general onboarding queries using HR data
        """
        # Preprocess the query
        query_type = self._preprocess_query(user_query)
        query_lower = user_query.lower()
        
        # Determine if query is more about policies or forms
        if any(word in query_lower for word in ['policy', 'policies', 'rule', 'regulation', 'handbook', 'leave', 'hours', 'dress', 'travel', 'harassment']):
            return self.query_policies(user_query)
        elif any(word in query_lower for word in ['form', 'forms', 'documents', 'orientation', 'onboarding', 'mail', 'submit']):
            return self.query_forms(user_query)
        else:
            # General welcome message
            return """Hi! I'm your Employee Onboarding Assistant. I can help you with:

**HR Policies**: Working hours, leave policy, dress code, travel policy, etc.
**Forms & Documents**: Employee information forms, document submission, orientation details
**Sample Emails**: Templates for document submission and orientation confirmations

Ask me specific questions like:
• "What are the working hours?"
• "Tell me about the leave policy"
• "How do I submit my documents?"
• "Show me the employee form"

What would you like to know?"""
    
    def refresh_content(self):
        """Reload content from config/policies_config.json file"""
        self.hr_data = self._load_hr_data()
        logger.info("🔄 HR knowledge base content refreshed from config")

# Global instance
knowledge_processor = KnowledgeBaseProcessor()