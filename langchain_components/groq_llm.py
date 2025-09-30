from langchain_groq import ChatGroq
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from app_settings import settings
import logging

logger = logging.getLogger(__name__)

class GroqLLMWrapper:
    """Wrapper for Groq LLM to maintain compatibility with existing code"""
    
    def __init__(self, model_name: str = None, temperature: float = 0.7):
        self.model_name = model_name or settings.GROQ_MODEL
        self.temperature = temperature
        
        # Initialize Groq chat model
        self.llm = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=2048,
            timeout=30,
            max_retries=2
        )
        
        logger.info(f"Initialized Groq LLM with model: {self.model_name}")
    
    def __call__(self, prompt):
        """Make the wrapper callable like the original LLM"""
        try:
            if isinstance(prompt, str):
                # Simple string prompt
                response = self.llm.invoke([HumanMessage(content=prompt)])
                return response.content
            elif isinstance(prompt, list):
                # List of messages
                response = self.llm.invoke(prompt)
                return response.content
            else:
                # Assume it's a formatted prompt template
                response = self.llm.invoke([HumanMessage(content=str(prompt))])
                return response.content
                
        except Exception as e:
            logger.error(f"Error calling Groq LLM: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again later."
    
    def invoke(self, messages):
        """Direct invoke method for LangChain compatibility"""
        try:
            response = self.llm.invoke(messages)
            return response
        except Exception as e:
            logger.error(f"Error invoking Groq LLM: {e}")
            return AIMessage(content="I apologize, but I'm experiencing technical difficulties. Please try again later.")
    
    def predict(self, text: str) -> str:
        """Prediction method for backward compatibility"""
        return self(text)
    
    def generate(self, prompts):
        """Generate method for batch processing"""
        try:
            results = []
            for prompt in prompts:
                response = self(prompt)
                results.append(response)
            return results
        except Exception as e:
            logger.error(f"Error generating with Groq LLM: {e}")
            return ["Error generating response"] * len(prompts)

def create_groq_llm(temperature: float = 0.7, model: str = None, use_wrapper: bool = False):
    """Factory function to create Groq LLM instance
    
    Args:
        temperature: Model temperature
        model: Model name to use
        use_wrapper: If True, returns wrapped instance. If False, returns raw ChatGroq instance.
    """
    if use_wrapper:
        return GroqLLMWrapper(model_name=model, temperature=temperature)
    else:
        # Return raw ChatGroq instance for direct LangChain compatibility
        from app_settings import settings
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=model or settings.GROQ_MODEL,
            temperature=temperature,
            max_tokens=2048,
            timeout=30,
            max_retries=2
        )

# Available Groq models
GROQ_MODELS = {
    "llama-3.1-70b-versatile": "Meta's Llama 3.1 70B - Most capable for complex reasoning",
    "llama-3.1-8b-instant": "Meta's Llama 3.1 8B - Fast responses, good for simple tasks",
    "mixtral-8x7b-32768": "Mistral's Mixtral 8x7B - Large context window",
    "gemma-7b-it": "Google's Gemma 7B - Instruction tuned",
    "gemma2-9b-it": "Google's Gemma2 9B - Latest version"
}

def get_available_models():
    """Get list of available Groq models"""
    return GROQ_MODELS
