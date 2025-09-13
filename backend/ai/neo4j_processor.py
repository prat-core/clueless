import os
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import json

class SimpleNeo4jKG:
    def __init__(self):
        # Neo4j connection
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_data(self, url, content, elements=None):
        with self.driver.session() as session:
            # generate vector embedding
            vector = self.embedding_model.encode(content).tolist()
            
            # create page node with content and vector
            query = """
            MERGE (p:Page {url: $url})
            SET p.content = $content,
                p.vector = $vector
            RETURN p
            """
            
            session.run(query, url=url, content=content, vector=vector)
            
            # add elements if provided
            if elements:
                for element in elements:
                    element_query = """
                    MATCH (p:Page {url: $url})
                    CREATE (e:Element {
                        type: $type,
                        text: $text,
                        selector: $selector
                    })
                    CREATE (p)-[:HAS_ELEMENT]->(e)
                    """
                    
                    session.run(element_query, 
                              url=url,
                              type=element.get('type', 'unknown'),
                              text=element.get('text', ''),
                              selector=element.get('selector', ''))
    
    def search(self, query_text, limit=5):
        with self.driver.session() as session:
            # For now, use simple text search since GDS plugin isn't available
            search_query = """
            MATCH (p:Page)
            WHERE p.content CONTAINS $query_text
            RETURN p.url as url, p.content as content, 1.0 as similarity
            ORDER BY p.content
            LIMIT $limit
            """
            
            result = session.run(search_query, query_text=query_text, limit=limit)
            return [dict(record) for record in result]
    
    def close(self):
        self.driver.close()
