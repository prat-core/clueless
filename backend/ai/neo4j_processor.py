import os
import sys
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any

# Add parent directory to path to import from graph_redo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph_redo.neo4j_manager import Neo4jManager

# Load environment variables from .env file
load_dotenv()

class neo4j_processor:
    def __init__(self):
        # Neo4j connection
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        
        # Initialize Neo4jManager instead of direct driver
        self.neo4j_manager = Neo4jManager(self.uri, (self.user, self.password))

    def find_shortest_path(self, start_id: str, end_id: str, max_depth: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Find the shortest path between two nodes using Neo4jManager.
        
        Args:
            start_id: Starting node ID (can be URL for Page or ID for Element)
            end_id: Ending node ID (can be URL for Page or ID for Element)
            max_depth: Maximum depth to search (default: 10)
            
        Returns:
            List of nodes in the path, or None if no path found
        """
        try:
            # Use Neo4jManager's find_shortest_path method
            # Note: Neo4jManager expects URLs for pages, so we pass the IDs directly
            result = self.neo4j_manager.find_shortest_path(start_id, end_id, max_depth)
            
            if result and result.get('path_found'):
                # Extract nodes from the result
                path_nodes = result.get('nodes', [])
                return path_nodes
            else:
                # If no path found or if there was an error
                error_msg = result.get('error', 'No path found') if result else 'No path found'
                print(f"Path finding failed: {error_msg}")
                return None
                
        except Exception as e:
            print(f"Error finding shortest path: {str(e)}")
            # Fallback to custom query if Neo4jManager method doesn't work for mixed node types
            return self._find_shortest_path_fallback(start_id, end_id, max_depth)
    
    def _find_shortest_path_fallback(self, start_id: str, end_id: str, max_depth: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Fallback method for finding shortest path with support for both Page and Element nodes.
        """
        query = f"""
        MATCH (start)
        WHERE (start:Page AND start.url = $start_id) OR (start:Element AND start.id = $start_id)
        MATCH (end)
        WHERE ((end:Page AND end.url = $end_id) OR (end:Element AND end.id = $end_id))
        AND start <> end
        MATCH p = shortestPath((start)-[:HAS_ELEMENT|LINKS_TO|LINKS_TO_EXTERNAL|NAVIGATES_TO*1..{max_depth}]-(end))
        RETURN nodes(p) as path_nodes, relationships(p) as path_relationships
        """
        
        try:
            # Use Neo4jManager's execute_query method for custom queries
            result = self.neo4j_manager.execute_query(query, {
                'start_id': start_id,
                'end_id': end_id
            })
            
            if result and len(result) > 0:
                # Extract path nodes from the first result
                path_nodes = result[0].get('path_nodes', [])
                # Convert nodes to dictionaries if needed
                path_info = []
                for node in path_nodes:
                    if isinstance(node, dict):
                        path_info.append(node)
                    else:
                        # If node is not a dict, try to convert it
                        path_info.append(dict(node) if hasattr(node, '__dict__') else {'id': str(node)})
                return path_info
            else:
                return None
                
        except Exception as e:
            print(f"Fallback path finding also failed: {str(e)}")
            return None
    
    def close(self):
        """Close the Neo4j connection."""
        if hasattr(self, 'neo4j_manager'):
            self.neo4j_manager.close()


if __name__ == '__main__':
    kg = neo4j_processor()

    start_id = "http://shop.com/homepage"
    end_id = "btn-buy-p001"

    print(f"Searching for shortest path from '{start_id}' to '{end_id}'...")
    path_nodes = kg.find_shortest_path(start_id, end_id)

    if path_nodes:
        print("Shortest path found!")
        for i, node in enumerate(path_nodes):
            labels = list(node.labels) if hasattr(node, 'labels') else ['No Label']
            node_id = node.get('url') or node.get('id') or node.get('name') or 'N/A'
            print(f"  Step {i+1}: {node_id} ({labels[0]})")
    else:
        print("No path was found between the specified nodes.")

    kg.close()
