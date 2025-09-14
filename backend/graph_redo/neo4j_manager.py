from neo4j import GraphDatabase
from typing import Dict, List, Optional, Tuple, Any
import logging


class Neo4jManager:
    def __init__(self, uri: str, auth: Tuple[str, str]):
        """
        Initialize the Neo4jManager with database connection.

        Args:
            uri (str): Neo4j database URI (e.g., "bolt://localhost:7687")
            auth (tuple): Neo4j authentication (username, password)
        """
        self.uri = uri
        self.auth = auth
        self.driver = None

        try:
            self.driver = GraphDatabase.driver(uri, auth=auth)
            # Test the connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logging.info(f"Successfully connected to Neo4j at {uri}")
        except Exception as e:
            logging.error(f"Failed to connect to Neo4j at {uri}: {str(e)}")
            raise

    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            logging.info("Neo4j connection closed")