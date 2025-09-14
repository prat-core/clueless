import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv

# Import our existing components
from .neo4j_processor import neo4j_processor
from .rag_tool import create_rag_tool
from .semantic_search import SemanticSearch

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NavigationTool:
    """
    Navigation tool that processes user queries to extract intent,
    performs vector similarity search, and returns navigation paths.
    
    Pipeline:
    1. User input → LLM (extract intent/destination)
    2. Vector cosine similarity search → find matching node
    3. Neo4j graph traversal → get navigation path
    4. Return structured navigation steps
    """
    
    def __init__(self):
        """Initialize the navigation tool with required components"""
        try:
            # Initialize LLM processor for intent extraction
            self.llm_processor = create_rag_tool()
            
            # Initialize Neo4j processor for graph operations
            self.neo4j_processor = neo4j_processor()
            
            # Initialize semantic search for vector operations
            self.semantic_search = SemanticSearch()
            
            logger.info("✅ Navigation tool initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize navigation tool: {e}")
            raise
    
    def extract_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Extract user intent and destination from the query using LLM directly
        
        Args:
            user_query: Raw user input
            
        Returns:
            Dictionary containing extracted intent information
        """
        try:
            intent_prompt = f"""
            Analyze the following user query and extract their navigation intent and destination.
            
            User Query: "{user_query}"
            
            Please extract:
            1. Intent: What does the user want to do? (e.g., "find", "navigate to", "locate", "buy", "search for")
            2. Destination: What specific page, element, or content are they looking for?
            3. Keywords: Key terms that describe the destination
            4. Context: Any additional context that might help with navigation
            
            Respond in this exact JSON format:
            {{
                "intent": "the main action the user wants to perform",
                "destination": "the specific target they want to reach",
                "keywords": ["keyword1", "keyword2", "keyword3"],
                "context": "additional helpful context",
                "confidence": 0.85
            }}
            
            Only respond with the JSON, no additional text.
            """
            
            logger.info(f"🧠 Extracting intent from query: {user_query[:100]}...")
            
            # Use the LLM directly for intent extraction
            response = self.llm_processor.get_relevant_info(intent_prompt)
            
            if response:
                # Try to parse JSON response
                import json
                try:
                    intent_data = json.loads(response)
                    logger.info(f"✅ Intent extracted: {intent_data.get('intent', 'unknown')}")
                    return intent_data
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    logger.warning("⚠️ Failed to parse JSON, using fallback intent extraction")
                    return self._fallback_intent_extraction(user_query)
            else:
                logger.warning("⚠️ LLM intent extraction failed, using fallback")
                return self._fallback_intent_extraction(user_query)
                
        except Exception as e:
            logger.error(f"❌ Error in intent extraction: {e}")
            return self._fallback_intent_extraction(user_query)
    
    def _fallback_intent_extraction(self, user_query: str) -> Dict[str, Any]:
        """
        Fallback method for intent extraction using simple keyword matching
        
        Args:
            user_query: User input
            
        Returns:
            Basic intent information
        """
        query_lower = user_query.lower()
        
        # Simple intent detection
        if any(word in query_lower for word in ['buy', 'purchase', 'order', 'cart']):
            intent = 'purchase'
        elif any(word in query_lower for word in ['find', 'search', 'look for', 'locate']):
            intent = 'find'
        elif any(word in query_lower for word in ['go to', 'navigate', 'take me to']):
            intent = 'navigate'
        else:
            intent = 'general'
        
        # Extract keywords (simple approach)
        keywords = [word for word in query_lower.split() if len(word) > 3][:5]
        
        return {
            'intent': intent,
            'destination': user_query,
            'keywords': keywords,
            'context': 'fallback extraction',
            'confidence': 0.6
        }
    
    def find_similar_nodes(self, intent_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find nodes similar to the user's intent using consolidated semantic search
        
        Args:
            intent_data: Extracted intent information
            limit: Maximum number of similar nodes to return
            
        Returns:
            List of similar nodes with similarity scores
        """
        try:
            # Create search query from intent data
            search_query = f"{intent_data.get('destination', '')} {' '.join(intent_data.get('keywords', []))}"
            
            logger.info(f"🔍 Searching for nodes similar to: {search_query[:100]}...")
            
            # Use consolidated semantic search functionality
            similar_nodes = self.semantic_search.find_similar_nodes(search_query, limit)
            
            logger.info(f"✅ Found {len(similar_nodes)} similar nodes using semantic search")
            
            return similar_nodes
            
        except Exception as e:
            logger.error(f"❌ Error finding similar nodes: {e}")
            return []
    
    
    def get_navigation_path(self, start_node_id: str, target_node_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get navigation path between two nodes using Neo4j graph traversal
        
        Args:
            start_node_id: Starting node ID
            target_node_id: Target node ID
            
        Returns:
            List of navigation steps or None if no path found
        """
        try:
            logger.info(f"🗺️ Finding path from '{start_node_id}' to '{target_node_id}'...")
            
            # Use neo4j_processor to find shortest path
            path_nodes = self.neo4j_processor.find_shortest_path(start_node_id, target_node_id)
            
            if not path_nodes:
                logger.warning(f"⚠️ No path found between '{start_node_id}' and '{target_node_id}'")
                return None
            
            # Format path for frontend consumption
            navigation_steps = []
            
            for i, node in enumerate(path_nodes):
                # Extract node information
                node_id = node.get('url') or node.get('id') or f'step_{i}'
                node_type = 'Page' if 'url' in node else 'Element'
                
                step = {
                    'step_number': i + 1,
                    'node_id': node_id,
                    'node_type': node_type,
                    'description': self._generate_step_description(node, i, len(path_nodes)),
                    'action': self._determine_action(node, i, len(path_nodes)),
                    'node_data': node
                }
                
                navigation_steps.append(step)
            
            logger.info(f"✅ Navigation path found with {len(navigation_steps)} steps")
            return navigation_steps
            
        except Exception as e:
            logger.error(f"❌ Error getting navigation path: {e}")
            return None
    
    def _generate_step_description(self, node: Dict[str, Any], step_index: int, total_steps: int) -> str:
        """
        Generate human-readable description for a navigation step
        
        Args:
            node: Node data
            step_index: Current step index
            total_steps: Total number of steps
            
        Returns:
            Step description
        """
        if step_index == 0:
            return f"Start at: {node.get('url', node.get('id', 'current page'))}"
        elif step_index == total_steps - 1:
            return f"Destination reached: {node.get('url', node.get('id', 'target'))}"
        else:
            if 'url' in node:
                return f"Navigate to page: {node['url']}"
            elif 'text' in node:
                return f"Click on: {node.get('text', 'element')}"
            else:
                return f"Interact with: {node.get('id', 'element')}"
    
    def _determine_action(self, node: Dict[str, Any], step_index: int, total_steps: int) -> str:
        """
        Determine the action type for a navigation step
        
        Args:
            node: Node data
            step_index: Current step index
            total_steps: Total number of steps
            
        Returns:
            Action type
        """
        if step_index == 0:
            return 'start'
        elif step_index == total_steps - 1:
            return 'destination'
        elif 'url' in node:
            return 'navigate'
        else:
            return 'click'
    
    def process_navigation_query(self, user_query: str, start_location: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method to process navigation queries through the complete pipeline
        
        Args:
            user_query: User's navigation request
            start_location: Optional starting location (defaults to current page)
            
        Returns:
            Complete navigation response with path and metadata
        """
        logger.info(f"🚀 Processing navigation query: {user_query[:100]}...")
        
        try:
            # Step 1: Extract intent from user query
            intent_data = self.extract_intent(user_query)
            
            # Step 2: Find similar nodes using vector search
            similar_nodes = self.find_similar_nodes(intent_data, limit=3)
            
            if not similar_nodes:
                return {
                    'status': 'error',
                    'message': 'No matching destinations found',
                    'user_query': user_query,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Step 3: Get the best matching target node
            best_match = similar_nodes[0]
            target_node_id = best_match['node_id']
            
            # Step 4: Determine starting location
            if not start_location:
                # Try to get current page from context or use a default
                start_location = self._get_current_location()
            
            # Step 5: Get navigation path
            navigation_path = self.get_navigation_path(start_location, target_node_id)
            
            if not navigation_path:
                return {
                    'status': 'error',
                    'message': f'No navigation path found from {start_location} to {target_node_id}',
                    'intent': intent_data,
                    'target_found': best_match,
                    'user_query': user_query,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Step 6: Return complete navigation response
            response = {
                'status': 'success',
                'navigation_path': navigation_path,
                'intent': intent_data,
                'target_match': {
                    'node_id': best_match['node_id'],
                    'similarity_score': best_match['similarity_score'],
                    'content_preview': best_match['content'][:200]
                },
                'alternative_targets': similar_nodes[1:],  # Other potential matches
                'metadata': {
                    'total_steps': len(navigation_path),
                    'start_location': start_location,
                    'target_location': target_node_id,
                    'processing_time': datetime.now().isoformat()
                },
                'user_query': user_query,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Navigation query processed successfully ({len(navigation_path)} steps)")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing navigation query: {e}")
            return {
                'status': 'error',
                'message': f'Error processing navigation query: {str(e)}',
                'user_query': user_query,
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_current_location(self) -> str:
        """
        Get current location (placeholder for future implementation)
        
        Returns:
            Current location identifier
        """
        # TODO: Implement logic to get actual current location
        # This could come from browser extension, session data, etc.
        return "homepage"  # Default starting point
    
    def close(self):
        """Close connections and cleanup resources"""
        try:
            if hasattr(self, 'neo4j_processor'):
                self.neo4j_processor.close()
            if hasattr(self, 'semantic_search'):
                self.semantic_search.close()
            logger.info("✅ Navigation tool closed successfully")
        except Exception as e:
            logger.error(f"❌ Error closing navigation tool: {e}")


# Factory function to create navigation tool instance
def create_navigation_tool() -> Optional[NavigationTool]:
    """
    Create navigation tool instance
    
    Returns:
        NavigationTool instance or None if initialization fails
    """
    try:
        return NavigationTool()
    except Exception as e:
        logger.error(f"Failed to create navigation tool: {e}")
        return None


# Global instance for use in Flask app
navigation_tool = create_navigation_tool()


# Example usage and testing
if __name__ == "__main__":
    nav_tool = create_navigation_tool()
    
    if nav_tool:
        # Test the navigation pipeline
        test_queries = [
            "I want to buy a product",
            "Take me to the login page",
            "Find the contact information",
            "Navigate to the shopping cart"
        ]
        
        for query in test_queries:
            print(f"\n🧪 Testing query: {query}")
            result = nav_tool.process_navigation_query(query)
            
            if result['status'] == 'success':
                print(f"✅ Success! Found path with {result['metadata']['total_steps']} steps")
                for step in result['navigation_path'][:3]:  # Show first 3 steps
                    print(f"  Step {step['step_number']}: {step['description']}")
            else:
                print(f"❌ Failed: {result['message']}")
        
        nav_tool.close()
    else:
        print("Failed to initialize navigation tool")
