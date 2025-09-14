import os
import logging
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from dotenv import load_dotenv
from .smart_navigation_agent import SmartNavigationAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryRouter:
    """
    Query router that uses Claude LLM to determine intent and route to appropriate tools
    """
    
    def __init__(self):
        """Initialize the query router with Claude client and navigation agent"""
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
        
        # Initialize navigation agent for consolidated classification
        try:
            self.navigation_agent = SmartNavigationAgent()
            logger.info("✅ Smart Navigation Agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Smart Navigation Agent: {e}")
            self.navigation_agent = None
        
        # System prompt for tool routing
        self.system_prompt = """You are a query router that determines which tool to use based on user intent.

Available tools:
1. NAVIGATION_TOOL - Use when user wants to navigate somewhere on the website (e.g., "take me to checkout", "find product page", "how to buy", "navigate to login")
2. RAG_TOOL - Use when user wants information about the website itself (e.g., "what are your policies", "how to use API", "tell me about SDK", "privacy policy")

Respond with ONLY the tool name: either "NAVIGATION_TOOL" or "RAG_TOOL"."""
    
    def classify_query(self, user_query: str) -> str:
        """
        Use consolidated navigation agent to classify the query and determine which tool to use
        
        Args:
            user_query: User's input query
            
        Returns:
            Tool name: "NAVIGATION_TOOL" or "RAG_TOOL"
        """
        # Use consolidated navigation agent for classification
        if self.navigation_agent:
            try:
                logger.info(f"🧠 Classifying query using Smart Navigation Agent: {user_query[:100]}...")
                tool_name = self.navigation_agent.classify_query_type(user_query)
                logger.info(f"✅ Query classified as: {tool_name}")
                return tool_name
            except Exception as e:
                logger.error(f"❌ Error in navigation agent classification: {e}")
                # Fallback to keyword-based classification
                return self._classify_by_keywords(user_query)
        else:
            logger.warning("⚠️ Navigation agent not available, using keyword-based classification")
            return self._classify_by_keywords(user_query)
    
    def _classify_by_keywords(self, user_query: str) -> str:
        """
        Fallback classification using keyword matching (consolidated keywords)
        
        Args:
            user_query: User's input query
            
        Returns:
            Tool name: "NAVIGATION_TOOL" or "RAG_TOOL"
        """
        query_lower = user_query.lower()
        
        # Use consolidated navigation keywords from smart_navigation_agent
        navigation_keywords = [
            'go to', 'find', 'navigate', 'get to', 'reach', 'locate',
            'where is', 'how do i', 'show me', 'take me', 'direct me',
            'path to', 'way to', 'route to', 'get to', 'access',
            'login', 'sign in', 'register', 'sign up', 'checkout', 'buy',
            'purchase', 'add to cart', 'search for', 'browse', 'explore',
            'click', 'button', 'link', 'page', 'section', 'how to',
            'help me', 'navigate to', 'take me to'
        ]
        
        # Check if query contains navigation keywords
        for keyword in navigation_keywords:
            if keyword in query_lower:
                logger.info(f"🔀 Query classified as NAVIGATION_TOOL (keyword: {keyword})")
                return "NAVIGATION_TOOL"
        
        # Default to RAG for general information queries
        logger.info("🔀 Query classified as RAG_TOOL (default)")
        return "RAG_TOOL"
    
    def route_query(self, user_query: str, start_location: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method to route user queries to appropriate tools
        
        Args:
            user_query: The user's input text
            start_location: Optional starting location for navigation queries
            
        Returns:
            Dictionary containing the tool response and metadata
        """
        logger.info(f"🚀 Routing user query: {user_query[:100]}...")
        
        try:
            # Step 1: Classify the query
            tool_name = self.classify_query(user_query)
            
            # Step 2: Route to appropriate tool
            if tool_name == "NAVIGATION_TOOL":
                return self._call_navigation_tool(user_query, start_location)
            else:  # RAG_TOOL
                return self._call_rag_tool(user_query)
                
        except Exception as e:
            logger.error(f"❌ Error in query routing: {e}")
            return {
                "response": f"Sorry, I encountered an error while processing your request: {str(e)}",
                "status": "error",
                "error": str(e),
                "user_query": user_query,
                "timestamp": self._get_timestamp()
            }
    
    def _call_navigation_tool(self, user_query: str, start_location: Optional[str] = None) -> Dict[str, Any]:
        """
        Call the navigation tool
        
        Args:
            user_query: User's navigation request
            start_location: Optional starting location
            
        Returns:
            Navigation tool response
        """
        try:
            from .navigation_tool import create_navigation_tool
            
            nav_tool = create_navigation_tool()
            if not nav_tool:
                return {
                    'response': 'Navigation tool is not available. Please check the configuration.',
                    'status': 'error',
                    'error': 'Navigation tool initialization failed'
                }
            
            # Process the navigation query
            result = nav_tool.process_navigation_query(user_query, start_location)
            
            # Close the navigation tool
            nav_tool.close()
            
            # Add routing metadata
            result['tool_used'] = 'navigation_tool'
            result['routing_timestamp'] = self._get_timestamp()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calling navigation tool: {e}")
            return {
                'response': f'Error with navigation tool: {str(e)}',
                'status': 'error',
                'error': str(e),
                'tool_used': 'navigation_tool'
            }
    
    def _call_rag_tool(self, user_query: str) -> Dict[str, Any]:
        """
        Call the RAG tool (temporary implementation)
        
        Args:
            user_query: User's informational request
            
        Returns:
            RAG tool response
        """
        try:
            from .rag_tool import create_rag_tool
            
            # Call the RAG tool
            rag_tool = create_rag_tool()
            if rag_tool is None:
                return {
                    'response': 'RAG tool could not be initialized. Please check your API keys.',
                    'status': 'error',
                    'error': 'RAG tool initialization failed',
                    'tool_used': 'rag_tool'
                }
            response = rag_tool.process_query(user_query)
            
            return {
                'response': response,
                'status': 'success',
                'tool_used': 'rag_tool',
                'user_query': user_query,
                'routing_timestamp': self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"❌ Error calling RAG tool: {e}")
            return {
                'response': f'Error with RAG tool: {str(e)}',
                'status': 'error',
                'error': str(e),
                'tool_used': 'rag_tool'
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()

# Create a global instance for use in Flask app
query_router = QueryRouter()
