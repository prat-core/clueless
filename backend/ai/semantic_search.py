import os
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from neo4j import GraphDatabase
from dotenv import load_dotenv
import numpy as np

load_dotenv()

class SemanticSearch:
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def find_end_node(self, user_input):
        """Find the most relevant end node based on user input."""
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
        
        return {
            "end_node": {
                "id": best_node.get('id') or best_node.get('url') or best_node.get('name'),
                "data": best_node,
                "similarity_score": float(best_similarity)
            },
            "confidence": float(best_similarity),
            "message": f"Found end node with {best_similarity:.2%} confidence"
        }
    
    def close(self):
        if self.driver:
            self.driver.close()
