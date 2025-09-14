from neo4j import GraphDatabase, Session
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime
import json

class Neo4jManager:
    def __init__(self, uri: str, auth: Tuple[str, str]):
        """
        Initialize Neo4j database connection and setup.

        Args:
            uri: Neo4j database URI (e.g., "bolt://localhost:7687")
            auth: Tuple of (username, password) for authentication
        """
        self.uri = uri
        self.auth = auth
        self.driver = None

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        try:
            self.driver = GraphDatabase.driver(uri, auth=auth)
            self.driver.verify_connectivity()
            self.logger.info(f"Successfully connected to Neo4j at {uri}")

            self._create_constraints_and_indexes()

        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise

    def _create_constraints_and_indexes(self):
        """Create necessary constraints and indexes for optimal performance."""
        with self.driver.session() as session:
            constraints_and_indexes = [
                "CREATE CONSTRAINT page_url_unique IF NOT EXISTS FOR (p:Page) REQUIRE p.url IS UNIQUE",
                "CREATE CONSTRAINT external_url_unique IF NOT EXISTS FOR (e:ExternalLink) REQUIRE e.url IS UNIQUE",
                "CREATE INDEX page_domain IF NOT EXISTS FOR (p:Page) ON (p.domain)",
                "CREATE INDEX page_crawled IF NOT EXISTS FOR (p:Page) ON (p.last_crawled)",
                "CREATE INDEX element_type IF NOT EXISTS FOR (e:Element) ON (e.type)",
                "CREATE VECTOR INDEX page_content_vector IF NOT EXISTS FOR (p:Page) ON p.content_vector OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}"
            ]

            for query in constraints_and_indexes:
                try:
                    session.run(query)
                    self.logger.info(f"Created constraint/index: {query.split()[2]}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        self.logger.warning(f"Could not create constraint/index: {e}")

    def _execute_write(self, query: str, parameters: Dict[str, Any] = None) -> Any:
        """Execute a write transaction."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return result.single()

    def _execute_read(self, query: str, parameters: Dict[str, Any] = None) -> List[Any]:
        """Execute a read transaction."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return list(result)

    def create_page_node(self, page_data: Dict) -> str:
        """Create or update a page node in Neo4j."""
        # Handle vector separately if present
        if page_data.get('content_vector'):
            query = """
            MERGE (p:Page {url: $url})
            SET p.title = $title,
                p.domain = $domain,
                p.path = $path,
                p.meta_description = $meta_description,
                p.content_text = $content_text,
                p.http_status = $http_status,
                p.response_time_ms = $response_time_ms,
                p.last_crawled = datetime(),
                p.content_hash = $content_hash,
                p.content_vector = $content_vector
            RETURN p.url as url
            """
        else:
            query = """
            MERGE (p:Page {url: $url})
            SET p.title = $title,
                p.domain = $domain,
                p.path = $path,
                p.meta_description = $meta_description,
                p.content_text = $content_text,
                p.http_status = $http_status,
                p.response_time_ms = $response_time_ms,
                p.last_crawled = datetime(),
                p.content_hash = $content_hash
            RETURN p.url as url
            """

        result = self._execute_write(query, {
            'url': page_data.get('url'),
            'title': page_data.get('title', ''),
            'domain': page_data.get('domain', ''),
            'path': page_data.get('path', ''),
            'meta_description': page_data.get('meta_description', ''),
            'content_text': page_data.get('text_content', '')[:5000],  # Limit text size
            'http_status': page_data.get('http_status'),
            'response_time_ms': page_data.get('response_time_ms'),
            'content_hash': page_data.get('content_hash', ''),
            'content_vector': page_data.get('content_vector')
        })

        return result['url'] if result else page_data.get('url')

    def create_relationship(self, from_url: str, to_url: str, rel_type: str = 'LINKS_TO'):
        """Create a relationship between two pages."""
        query = """
        MERGE (from:Page {url: $from_url})
        MERGE (to:Page {url: $to_url})
        MERGE (from)-[r:%s]->(to)
        RETURN from.url, to.url
        """ % rel_type

        self._execute_write(query, {
            'from_url': from_url,
            'to_url': to_url
        })

    def create_external_link(self, from_url: str, external_url: str):
        """Create an external link node and relationship."""
        query = """
        MERGE (from:Page {url: $from_url})
        MERGE (ext:ExternalLink {url: $external_url})
        ON CREATE SET ext.first_seen = datetime(),
                      ext.reference_count = 1
        ON MATCH SET ext.reference_count = ext.reference_count + 1
        MERGE (from)-[:LINKS_TO_EXTERNAL]->(ext)
        RETURN from.url, ext.url
        """

        self._execute_write(query, {
            'from_url': from_url,
            'external_url': external_url
        })

    def create_element_node(self, page_url: str, element_data: Dict):
        """Create an element node related to a page."""
        query = """
        MATCH (p:Page {url: $page_url})
        CREATE (e:Element {
            type: $type,
            text: $text,
            id: $id,
            class: $class
        })
        CREATE (p)-[:HAS_ELEMENT]->(e)
        RETURN e
        """

        self._execute_write(query, {
            'page_url': page_url,
            'type': element_data.get('type', ''),
            'text': element_data.get('text', '')[:200],
            'id': element_data.get('id', ''),
            'class': element_data.get('class', '')
        })

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()