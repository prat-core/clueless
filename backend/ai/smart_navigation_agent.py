import os
import json
import re
from anthropic import Anthropic
from dotenv import load_dotenv
from .semantic_search import SemanticSearch

load_dotenv()

class SmartNavigationAgent:
    def __init__(self):
        # Initialize Claude
        self.claude = None
        try:
            self.claude = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        except Exception as e:
            print(f"Claude not available: {e}")
        
        # Initialize semantic search
        self.semantic_search = SemanticSearch()
        
    def is_navigation_prompt_simple(self, user_input):
        """
        Simple keyword-based navigation prompt detection (fallback method)
        
        Args:
            user_input: User's input text
            
        Returns:
            Dictionary with navigation detection results
        """
        # Comprehensive navigation keywords from both implementations
        navigation_keywords = [
            'go to', 'find', 'navigate', 'get to', 'reach', 'locate',
            'where is', 'how do i', 'show me', 'take me', 'direct me',
            'path to', 'way to', 'route to', 'get to', 'access',
            'login', 'sign in', 'register', 'sign up', 'checkout', 'buy',
            'purchase', 'add to cart', 'search for', 'browse', 'explore',
            'click', 'button', 'link', 'page', 'section', 'how to',
            'help me', 'navigate to', 'take me to'
        ]
        
        user_lower = user_input.lower()
        
        # Check for navigation keywords
        for keyword in navigation_keywords:
            if keyword in user_lower:
                return {
                    "is_navigation": True,
                    "confidence": 0.8,
                    "reasoning": f"Contains navigation keyword: '{keyword}'"
                }
        
        # Check for question patterns that suggest navigation
        question_patterns = [
            r'how\s+do\s+i\s+',
            r'where\s+is\s+',
            r'how\s+can\s+i\s+',
            r'what\s+is\s+the\s+way\s+to',
            r'how\s+to\s+get\s+to'
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, user_lower):
                return {
                    "is_navigation": True,
                    "confidence": 0.7,
                    "reasoning": f"Matches navigation question pattern"
                }
        
        return {
            "is_navigation": False,
            "confidence": 0.6,
            "reasoning": "No navigation keywords or patterns detected"
        }
        
    def is_navigation_prompt(self, user_input):
        """Use Claude to determine if the input is a navigation prompt."""
        if not self.claude:
            return self.is_navigation_prompt_simple(user_input)
            
        prompt = f"""
        Analyze the following user input and determine if it's a navigation prompt.
        
        A navigation prompt is one that:
        - Asks how to get somewhere or find something
        - Mentions going to, finding, or navigating to a specific location/person/thing
        - Uses words like "go to", "find", "navigate", "get to", "reach", "locate"
        - Asks for directions or paths
        
        Examples of navigation prompts:
        - "How do I go to Bob?"
        - "Find the checkout button"
        - "Navigate to the login page"
        - "Where is the product details section?"
        - "How do I get to the settings?"
        
        Examples of NON-navigation prompts:
        - "What is the weather?"
        - "Tell me about Python programming"
        - "What's 2+2?"
        - "Explain machine learning"
        - "Hello, how are you?"
        
        User input: "{user_input}"
        
        Respond with ONLY a JSON object in this format:
        {{
            "is_navigation": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "Brief explanation of why this is or isn't a navigation prompt"
        }}
        """
        
        try:
            response = self.claude.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            content = response.content[0].text.strip()
            
            # Try to find JSON in the response
            if '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                
                result = json.loads(json_str)
                return result
            else:
                # Fallback to simple detection
                return self.is_navigation_prompt_simple(user_input)
                
        except Exception as e:
            print(f"Error calling Claude: {e}")
            # Fallback to simple detection
            return self.is_navigation_prompt_simple(user_input)
    
    def process_user_input(self, user_input):
        # First, determine if it's a navigation prompt
        navigation_analysis = self.is_navigation_prompt(user_input)
        
        result = {
            "user_input": user_input,
            "is_navigation_prompt": navigation_analysis["is_navigation"],
            "claude_confidence": navigation_analysis["confidence"],
            "claude_reasoning": navigation_analysis["reasoning"],
            "end_node": None,
            "semantic_confidence": 0.0,
            "message": ""
        }
        
        # Only find end node if it's a navigation prompt
        if navigation_analysis["is_navigation"]:
            try:
                semantic_result = self.semantic_search.find_end_node(user_input)
                result.update({
                    "end_node": semantic_result["end_node"],
                    "semantic_confidence": semantic_result["confidence"],
                    "message": f"Navigation prompt detected. {semantic_result['message']}"
                })
            except Exception as e:
                result["message"] = f"Navigation prompt detected but error finding end node: {str(e)}"
        else:
            result["message"] = "Not a navigation prompt - no end node search performed"
        
        return result
    
    def classify_query_type(self, user_query: str) -> str:
        """
        Classify whether a query is a navigation query or informational query
        (Consolidated from general_llm.py functionality)
        
        Args:
            user_query: User's input query
            
        Returns:
            "NAVIGATION_TOOL" or "RAG_TOOL"
        """
        # First check if it's a navigation prompt
        nav_result = self.is_navigation_prompt(user_query)
        
        if nav_result["is_navigation"]:
            return "NAVIGATION_TOOL"
        else:
            return "RAG_TOOL"
    
    def close(self):
        """Close the semantic search connection."""
        if hasattr(self, 'semantic_search'):
            self.semantic_search.close()