import os
import logging
from typing import Dict, List, Optional, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from neo4j import GraphDatabase
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SemanticSearch:
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Cache for node embeddings (to avoid recomputing)
        self._node_embeddings_cache = {}
        
        logger.info("✅ SemanticSearch initialized successfully")
    
    def find_end_node(self, user_input):
        query = "MATCH (n) RETURN n, labels(n) as labels"
        
        with self.driver.session() as session:
            result = session.run(query)
            nodes = []
            for record in result:
                node_data = dict(record['n'])
                # Convert Neo4j types to JSON-serializable types
                for key, value in node_data.items():
                    if hasattr(value, 'isoformat'):
                        node_data[key] = value.isoformat()
                    elif hasattr(value, 'strftime'):
                        node_data[key] = value.strftime('%Y-%m-%d')
                node_data['labels'] = record['labels']
                nodes.append(node_data)
        
        if not nodes:
            return {"end_node": None, "confidence": 0.0, "message": "No nodes found"}
        
        # Create text representations
        node_texts = []
        for node in nodes:
            text = f"Type: {', '.join(node['labels'])} | "
            for key, value in node.items():
                if key != 'labels' and value and isinstance(value, str):
                    text += f"{key}: {value} | "
            node_texts.append(text.strip())
        
        # Find best match
        user_embedding = self.model.encode([user_input])
        node_embeddings = self.model.encode(node_texts)
        similarities = cosine_similarity(user_embedding, node_embeddings)[0]
        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]
        best_node = nodes[best_idx]
        
        # Clean best_node data to ensure JSON serialization
        clean_best_node = {}
        for key, value in best_node.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                clean_best_node[key] = value
            elif hasattr(value, 'isoformat'):  # DateTime objects
                clean_best_node[key] = value.isoformat()
            else:
                clean_best_node[key] = str(value)
        
        return {
            "end_node": {
                "id": best_node.get('id') or best_node.get('url') or best_node.get('name'),
                "data": clean_best_node,
                "similarity_score": float(best_similarity)
            },
            "confidence": float(best_similarity),
            "message": f"Found end node with {best_similarity:.2%} confidence"
        }
    
    def find_similar_nodes(self, search_query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find nodes similar to the search query using vector cosine similarity
        
        Args:
            search_query: The query to search for
            limit: Maximum number of similar nodes to return
            
        Returns:
            List of similar nodes with similarity scores
        """
        try:
            logger.info(f"🔍 Searching for nodes similar to: {search_query[:100]}...")
            
            # Get query embedding
            query_embedding = self.model.encode([search_query])
            
            # Get all nodes with their content from Neo4j
            nodes = self._get_all_nodes_with_content()
            
            if not nodes:
                logger.warning("⚠️ No nodes found in Neo4j database")
                return []
            
            # Calculate similarities
            similar_nodes = []
            
            for node in nodes:
                node_content = node.get('content', '')
                node_id = node.get('url') or node.get('id', 'unknown')
                
                if not node_content:
                    continue
                
                # Get or compute node embedding
                if node_id not in self._node_embeddings_cache:
                    self._node_embeddings_cache[node_id] = self.model.encode([node_content])
                
                node_embedding = self._node_embeddings_cache[node_id]
                
                # Calculate cosine similarity
                similarity = cosine_similarity(query_embedding, node_embedding)[0][0]
                
                # Clean node data to ensure JSON serialization
                clean_node_data = {}
                for key, value in node.items():
                    if isinstance(value, (str, int, float, bool, type(None))):
                        clean_node_data[key] = value
                    elif hasattr(value, 'isoformat'):  # DateTime objects
                        clean_node_data[key] = value.isoformat()
                    else:
                        clean_node_data[key] = str(value)
                
                similar_nodes.append({
                    'node_id': node_id,
                    'content': node_content[:500],  # Truncate for response
                    'similarity_score': float(similarity),
                    'node_data': clean_node_data
                })
            
            # Sort by similarity and return top results
            similar_nodes.sort(key=lambda x: x['similarity_score'], reverse=True)
            top_nodes = similar_nodes[:limit]
            
            logger.info(f"✅ Found {len(top_nodes)} similar nodes (best similarity: {top_nodes[0]['similarity_score']:.3f})")
            
            return top_nodes
            
        except Exception as e:
            logger.error(f"❌ Error finding similar nodes: {e}")
            return []
    
    def _get_all_nodes_with_content(self) -> List[Dict[str, Any]]:
        """
        Get all nodes with content from Neo4j database
        
        Returns:
            List of nodes with their content
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (n:Page)
                WHERE n.content_text IS NOT NULL AND n.content_text <> ''
                RETURN n.url as url, n.id as id, n.content_text as content, 
                       labels(n) as labels, properties(n) as properties
                LIMIT 1000
                """
                
                result = session.run(query)
                nodes = []
                
                for record in result:
                    node_data = {
                        'url': record.get('url'),
                        'id': record.get('id'),
                        'content': record.get('content', ''),
                        'labels': record.get('labels', []),
                        'properties': dict(record.get('properties', {}))
                    }
                    nodes.append(node_data)
                
                return nodes
                
        except Exception as e:
            logger.error(f"❌ Error getting nodes from Neo4j: {e}")
            return []
    
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
            logger.info("✅ SemanticSearch connection closed")
