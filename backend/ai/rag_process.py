import os
import logging
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGProcessor:
    """
    RAG (Retrieval-Augmented Generation) processor using Claude LLM
    This class handles user queries by retrieving relevant context and generating responses
    """
    
    def __init__(self):
        """Initialize the RAG processor with Claude client"""
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.anthropic_api_key:
            logger.warning("⚠️  ANTHROPIC_API_KEY not found in environment variables")
            self.client = None
        else:
            try:
                self.client = Anthropic(api_key=self.anthropic_api_key)
                logger.info("✅ Claude client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Claude client: {e}")
                self.client = None
        
        # Default system prompt for the assistant
        self.system_prompt = """You are a helpful AI assistant that provides clear, accurate, and contextual responses. 
        You should be concise but thorough, and always aim to be helpful and informative."""
    
    def retrieve_context(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for the user query
        This is a placeholder for future implementation with vector search, knowledge base, etc.
        """
        # TODO: Implement actual retrieval logic
        # This could involve:
        # - Vector similarity search
        # - Database queries
        # - Web scraping
        # - Knowledge base lookup
        
        logger.info(f"🔍 Retrieving context for query: {query[:100]}...")
        
        # Placeholder context - replace with actual retrieval logic
        context = [
            {
                "source": "placeholder",
                "content": "This is placeholder context that would be retrieved based on the user query.",
                "relevance_score": 0.8
            }
        ]
        
        return context
    
    def generate_response(self, query: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a response using Claude LLM with optional context
        
        Args:
            query: User's input query
            context: Retrieved context information (optional)
            
        Returns:
            Dictionary containing the response and metadata
        """
        if not self.client:
            return {
                "response": "Sorry, Claude LLM is not available. Please check your API configuration.",
                "status": "error",
                "error": "Claude client not initialized"
            }
        
        try:
            # Prepare the prompt with context if available
            if context:
                context_text = "\n".join([
                    f"Context from {ctx.get('source', 'unknown')}: {ctx.get('content', '')}"
                    for ctx in context[:3]  # Limit to top 3 contexts
                ])
                
                prompt = f"""Based on the following context information, please answer the user's question:

CONTEXT:
{context_text}

USER QUESTION: {query}

Please provide a helpful and accurate response based on the context provided. If the context doesn't contain relevant information, you can still provide a general response."""
            else:
                prompt = query
            
            logger.info("🤖 Generating response with Claude...")
            
            # Call Claude API
            message = self.client.messages.create(
                model="claude-3-7-sonnet-20250219", 
                max_tokens=1000,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text
            
            logger.info("✅ Response generated successfully")
            
            return {
                "response": response_text,
                "status": "success",
                "model": "claude-3-7-sonnet-20250219",
                "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
                "context_used": len(context) if context else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            return {
                "response": f"Sorry, I encountered an error while processing your request: {str(e)}",
                "status": "error",
                "error": str(e)
            }
    
    def process_query(self, user_input: str, use_retrieval: bool = True) -> Dict[str, Any]:
        """
        Main method to process user queries with RAG pipeline
        
        Args:
            user_input: The user's input text
            use_retrieval: Whether to use retrieval for context (default: True)
            
        Returns:
            Dictionary containing the complete response with metadata
        """
        logger.info(f"📝 Processing user query: {user_input[:100]}...")
        
        try:
            context = None
            if use_retrieval:
                context = self.retrieve_context(user_input)
            
            response = self.generate_response(user_input, context)
            
            # Add query metadata
            response.update({
                "user_query": user_input,
                "retrieval_used": use_retrieval,
                "timestamp": self._get_timestamp()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in process_query: {e}")
            return {
                "response": "I'm sorry, I encountered an error while processing your request.",
                "status": "error",
                "error": str(e),
                "user_query": user_input,
                "timestamp": self._get_timestamp()
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()

# Create a global instance for use in Flask app
rag_processor = RAGProcessor()
