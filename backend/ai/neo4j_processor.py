import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class neo4j_processor:
    def __init__(self):
        # Neo4j connection
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def find_shortest_path(self, start_id, end_id):
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
