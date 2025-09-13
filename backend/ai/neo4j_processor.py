import os
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
                    # NOTE: Assuming 'id' is a unique property you want to use for identification
                    element_id = element.get('id')
                    if not element_id:
                        print("Warning: Skipping element without a valid 'id'.")
                        continue
                        
                    element_query = """
                    MATCH (p:Page {url: $url})
                    MERGE (e:Element {id: $element_id})
                    SET e.type = $type,
                        e.text = $text,
                        e.selector = $selector
                    MERGE (p)-[:HAS_ELEMENT]->(e)
                    """
                    
                    session.run(element_query, 
                                url=url,
                                element_id=element_id,
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

    def find_shortest_path(self, start_id, end_id):
        """
        Finds the shortest path between any two nodes given their identifying properties.
        """
        query = """
        MATCH (start)
        WHERE (start:Page AND start.url = $start_id) OR (start:Element AND start.id = $start_id)
        MATCH (end)
        WHERE (end:Page AND end.url = $end_id) OR (end:Element AND end.id = $end_id)
        AND start <> end
        MATCH p = shortestPath((start)-[:HAS_ELEMENT|NAVIGATES_TO|LINKS_TO|LINKS_TO_EXTERNAL|SIMILAR_TO*]-(end))
        RETURN nodes(p) as path_nodes, relationships(p) as path_relationships
        """
        with self.driver.session() as session:
            result = session.run(query, start_id=start_id, end_id=end_id)
            record = result.single()
            if record:
                path_info = []
                for node in record["path_nodes"]:
                    path_info.append(dict(node))
                return path_info
            else:
                return None
    
    def close(self):
        self.driver.close()

# --- Example of how to use the new method ---

if __name__ == '__main__':
    kg = SimpleNeo4jKG()

    # Start node is a Page, identified by its url
    start_id = "http://shop.com/homepage"
    # End node is an Element, identified by its id property
    end_id = "btn-buy-p001"

    print(f"Searching for shortest path from '{start_id}' to '{end_id}'...")
    path_nodes = kg.find_shortest_path(start_id, end_id)

    if path_nodes:
        print("Shortest path found! 🎉")
        for i, node in enumerate(path_nodes):
            labels = list(node.labels) if hasattr(node, 'labels') else ['No Label']
            node_id = node.get('url') or node.get('id') or node.get('name') or 'N/A'
            print(f"  Step {i+1}: {node_id} ({labels[0]})")
    else:
        print("No path was found between the specified nodes. 😢")

    kg.close()
