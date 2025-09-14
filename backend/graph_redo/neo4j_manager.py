from neo4j import GraphDatabase
from typing import Dict, List, Optional, Tuple, Any, Set
import logging
from datetime import datetime
from urllib.parse import urlparse, urljoin, urlunparse
import hashlib
import openai
import requests
from bs4 import BeautifulSoup
import time
from collections import deque
import re


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

    def create_page_node(self, page_data: Dict[str, Any]) -> str:
        """
        Create or update a Page node in Neo4j with the provided page data.

        Args:
            page_data (dict): Dictionary containing page information with keys:
                - url: string, the page URL (required)
                - title: string, page title
                - meta_description: string, page meta description
                - content_text: string, cleaned text content
                - content_vector: list of floats, embedding vector
                - http_status: integer, HTTP response status
                - response_time_ms: float, response time in milliseconds
                - clickable_elements: list of dicts with element info
                - content_hash: string, hash of content for change detection

        Returns:
            str: The URL of the created/updated node

        Raises:
            Exception: If node creation fails
        """
        required_fields = ['url']
        for field in required_fields:
            if field not in page_data:
                raise ValueError(f"Required field '{field}' missing from page_data")

        # Parse URL for domain and path extraction
        parsed_url = urlparse(page_data['url'])
        domain = parsed_url.netloc
        path = parsed_url.path

        # Generate content hash if not provided
        content_hash = page_data.get('content_hash')
        if not content_hash and page_data.get('content_text'):
            content_hash = hashlib.md5(page_data['content_text'].encode()).hexdigest()

        # Prepare node properties
        current_time = datetime.utcnow()
        node_properties = {
            'url': page_data['url'],
            'domain': domain,
            'path': path,
            'title': page_data.get('title', ''),
            'meta_description': page_data.get('meta_description', ''),
            'content_text': page_data.get('content_text', ''),
            'content_vector': page_data.get('content_vector', []),
            'http_status': page_data.get('http_status', 200),
            'response_time_ms': page_data.get('response_time_ms', 0.0),
            'content_hash': content_hash or '',
            'clickable_elements': page_data.get('clickable_elements', []),
            'last_crawled': current_time.isoformat()
        }

        # Cypher query to create or update the page node
        cypher_query = """
        MERGE (p:Page {url: $url})
        ON CREATE SET
            p.domain = $domain,
            p.path = $path,
            p.title = $title,
            p.meta_description = $meta_description,
            p.content_text = $content_text,
            p.content_vector = $content_vector,
            p.http_status = $http_status,
            p.response_time_ms = $response_time_ms,
            p.content_hash = $content_hash,
            p.clickable_elements = $clickable_elements,
            p.first_crawled = $last_crawled,
            p.last_crawled = $last_crawled
        ON MATCH SET
            p.title = $title,
            p.meta_description = $meta_description,
            p.content_text = $content_text,
            p.content_vector = $content_vector,
            p.http_status = $http_status,
            p.response_time_ms = $response_time_ms,
            p.content_hash = $content_hash,
            p.clickable_elements = $clickable_elements,
            p.last_crawled = $last_crawled
        RETURN p.url as url
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, node_properties)
                record = result.single()
                if record:
                    created_url = record['url']
                    logging.info(f"Page node created/updated successfully: {created_url}")
                    return created_url
                else:
                    raise Exception("Failed to create/update page node - no result returned")

        except Exception as e:
            logging.error(f"Failed to create page node for {page_data.get('url', 'unknown')}: {str(e)}")
            raise

    def create_relationship(self, from_url: str, to_url: str, rel_type: str, properties: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a relationship between two nodes in the Neo4j graph.

        Args:
            from_url (str): URL of the source node
            to_url (str): URL of the target node
            rel_type (str): Type of relationship (LINKS_TO, LINKS_TO_EXTERNAL, HAS_ELEMENT, NAVIGATES_TO, SIMILAR_TO)
            properties (dict, optional): Additional properties for the relationship

        Returns:
            bool: True if relationship was created successfully, False otherwise

        Raises:
            ValueError: If invalid relationship type or missing required parameters
            Exception: If relationship creation fails
        """
        # Validate relationship type
        valid_rel_types = ['LINKS_TO', 'LINKS_TO_EXTERNAL', 'HAS_ELEMENT', 'NAVIGATES_TO', 'SIMILAR_TO']
        if rel_type not in valid_rel_types:
            raise ValueError(f"Invalid relationship type '{rel_type}'. Must be one of: {valid_rel_types}")

        # Validate required parameters
        if not from_url or not to_url:
            raise ValueError("Both from_url and to_url are required")

        # Prepare relationship properties
        rel_properties = properties or {}
        rel_properties['created_at'] = datetime.utcnow().isoformat()

        # Build property string for Cypher query
        prop_string = ""
        if rel_properties:
            prop_items = []
            for key, value in rel_properties.items():
                if isinstance(value, str):
                    prop_items.append(f"{key}: '{value}'")
                elif isinstance(value, (int, float)):
                    prop_items.append(f"{key}: {value}")
                else:
                    prop_items.append(f"{key}: $props.{key}")
            if prop_items:
                prop_string = f" {{{', '.join(prop_items)}}}"

        # Different Cypher queries based on relationship type
        if rel_type == 'LINKS_TO':
            # Internal page to page relationship
            cypher_query = f"""
            MATCH (from:Page {{url: $from_url}})
            MATCH (to:Page {{url: $to_url}})
            MERGE (from)-[r:{rel_type}{prop_string}]->(to)
            RETURN r
            """

        elif rel_type == 'LINKS_TO_EXTERNAL':
            # Page to external link relationship
            cypher_query = f"""
            MATCH (from:Page {{url: $from_url}})
            MERGE (to:ExternalLink {{url: $to_url}})
            ON CREATE SET to.domain = $to_domain, to.first_seen = $created_at, to.reference_count = 1
            ON MATCH SET to.reference_count = to.reference_count + 1
            MERGE (from)-[r:{rel_type}{prop_string}]->(to)
            RETURN r
            """
            # Parse domain for external link
            parsed_to_url = urlparse(to_url)
            rel_properties['to_domain'] = parsed_to_url.netloc

        elif rel_type == 'HAS_ELEMENT':
            # Page to element relationship
            cypher_query = f"""
            MATCH (from:Page {{url: $from_url}})
            MERGE (to:Element {{id: $to_url}})
            MERGE (from)-[r:{rel_type}{prop_string}]->(to)
            RETURN r
            """

        elif rel_type == 'NAVIGATES_TO':
            # Element to page relationship
            cypher_query = f"""
            MATCH (from:Element {{id: $from_url}})
            MATCH (to:Page {{url: $to_url}})
            MERGE (from)-[r:{rel_type}{prop_string}]->(to)
            RETURN r
            """

        elif rel_type == 'SIMILAR_TO':
            # Page to page similarity relationship
            cypher_query = f"""
            MATCH (from:Page {{url: $from_url}})
            MATCH (to:Page {{url: $to_url}})
            MERGE (from)-[r:{rel_type}{prop_string}]->(to)
            RETURN r
            """

        try:
            with self.driver.session() as session:
                # Prepare parameters
                params = {
                    'from_url': from_url,
                    'to_url': to_url,
                    'created_at': rel_properties['created_at']
                }

                # Add additional properties if needed
                if rel_type == 'LINKS_TO_EXTERNAL':
                    params['to_domain'] = rel_properties.get('to_domain', '')

                # Add complex properties that need parameter passing
                complex_props = {}
                for key, value in rel_properties.items():
                    if not isinstance(value, (str, int, float)) and key != 'created_at':
                        complex_props[key] = value

                if complex_props:
                    params['props'] = complex_props

                result = session.run(cypher_query, params)
                record = result.single()

                if record:
                    logging.info(f"Relationship {rel_type} created successfully: {from_url} -> {to_url}")
                    return True
                else:
                    logging.warning(f"No relationship created for {rel_type}: {from_url} -> {to_url}")
                    return False

        except Exception as e:
            logging.error(f"Failed to create relationship {rel_type} from {from_url} to {to_url}: {str(e)}")
            raise

    def find_similar_pages(self, vector: List[float], threshold: float = 0.8, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find pages similar to the given vector using cosine similarity.

        Args:
            vector (list): Query vector to compare against stored page vectors
            threshold (float): Minimum cosine similarity threshold (0.0 to 1.0)
            limit (int): Maximum number of results to return

        Returns:
            list: List of dictionaries containing similar pages with their similarity scores
                Each dict contains: url, title, similarity_score, domain, content_text

        Raises:
            ValueError: If vector is empty or threshold is invalid
            Exception: If similarity search fails
        """
        if not vector:
            raise ValueError("Query vector cannot be empty")

        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        # Calculate vector magnitude for normalization
        vector_magnitude = sum(x * x for x in vector) ** 0.5
        if vector_magnitude == 0:
            raise ValueError("Query vector cannot be zero vector")

        # Cypher query to find pages with content vectors and calculate cosine similarity
        cypher_query = """
        MATCH (p:Page)
        WHERE p.content_vector IS NOT NULL AND size(p.content_vector) > 0
        WITH p,
             p.content_vector as stored_vector,
             $query_vector as query_vector,
             $query_magnitude as query_magnitude
        WHERE size(stored_vector) = size(query_vector)
        WITH p, stored_vector, query_vector, query_magnitude,
             // Calculate dot product
             reduce(dot_product = 0.0, i in range(0, size(query_vector)-1) |
                dot_product + query_vector[i] * stored_vector[i]
             ) as dot_product,
             // Calculate stored vector magnitude
             sqrt(reduce(magnitude_sq = 0.0, val in stored_vector |
                magnitude_sq + val * val
             )) as stored_magnitude
        WITH p, dot_product, stored_magnitude, query_magnitude,
             // Calculate cosine similarity
             CASE
                WHEN stored_magnitude > 0 AND query_magnitude > 0
                THEN dot_product / (stored_magnitude * query_magnitude)
                ELSE 0.0
             END as similarity_score
        WHERE similarity_score >= $threshold
        RETURN p.url as url,
               p.title as title,
               p.domain as domain,
               p.content_text as content_text,
               p.last_crawled as last_crawled,
               similarity_score
        ORDER BY similarity_score DESC
        LIMIT $limit
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {
                    'query_vector': vector,
                    'query_magnitude': vector_magnitude,
                    'threshold': threshold,
                    'limit': limit
                })

                similar_pages = []
                for record in result:
                    similar_pages.append({
                        'url': record['url'],
                        'title': record['title'] or '',
                        'domain': record['domain'],
                        'content_text': record['content_text'],
                        'last_crawled': record['last_crawled'],
                        'similarity_score': round(float(record['similarity_score']), 4)
                    })

                logging.info(f"Found {len(similar_pages)} similar pages with threshold {threshold}")
                return similar_pages

        except Exception as e:
            logging.error(f"Failed to find similar pages: {str(e)}")
            raise

    def execute_query(self, cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom Cypher query against the Neo4j database.

        Args:
            cypher_query (str): The Cypher query to execute
            parameters (dict, optional): Parameters for the query

        Returns:
            list: List of dictionaries containing query results

        Raises:
            ValueError: If query is empty
            Exception: If query execution fails
        """
        if not cypher_query or not cypher_query.strip():
            raise ValueError("Cypher query cannot be empty")

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, parameters or {})

                # Convert result to list of dictionaries
                records = []
                for record in result:
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        # Handle Neo4j specific types
                        if hasattr(value, '__dict__'):
                            # Convert Node/Relationship objects to dictionaries
                            if hasattr(value, 'items'):
                                record_dict[key] = dict(value.items())
                            else:
                                record_dict[key] = str(value)
                        else:
                            record_dict[key] = value
                    records.append(record_dict)

                logging.info(f"Executed query successfully, returned {len(records)} records")
                return records

        except Exception as e:
            logging.error(f"Failed to execute query: {str(e)}")
            logging.error(f"Query: {cypher_query}")
            if parameters:
                logging.error(f"Parameters: {parameters}")
            raise

    def get_page_graph(self, url: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get the graph structure around a specific page including connected nodes and relationships.

        Args:
            url (str): The URL of the central page
            depth (int): Maximum depth to traverse from the central page (default: 2)

        Returns:
            dict: Dictionary containing nodes and relationships in the subgraph
                {
                    'center_page': {...},
                    'nodes': [...],
                    'relationships': [...],
                    'stats': {...}
                }

        Raises:
            ValueError: If URL is empty or depth is invalid
            Exception: If graph retrieval fails
        """
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        if depth < 1 or depth > 5:
            raise ValueError("Depth must be between 1 and 5")

        cypher_query = f"""
        MATCH (center:Page {{url: $url}})
        OPTIONAL MATCH path = (center)-[*1..{depth}]-(connected)
        WHERE connected:Page OR connected:ExternalLink OR connected:Element
        WITH center,
             collect(DISTINCT connected) as connected_nodes,
             collect(DISTINCT relationships(path)) as path_relationships
        WITH center, connected_nodes,
             reduce(flat_rels = [], rel_list in path_relationships |
                CASE WHEN rel_list IS NOT NULL
                THEN flat_rels + rel_list
                ELSE flat_rels END
             ) as all_relationships
        RETURN center, connected_nodes, all_relationships as relationships
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {'url': url})
                record = result.single()

                if not record:
                    # Try to find the page without connections
                    simple_query = "MATCH (p:Page {url: $url}) RETURN p"
                    simple_result = session.run(simple_query, {'url': url})
                    simple_record = simple_result.single()

                    if not simple_record:
                        raise ValueError(f"Page not found: {url}")

                    # Return minimal graph with just the center page
                    center_page = dict(simple_record['p'].items())
                    return {
                        'center_page': center_page,
                        'nodes': [center_page],
                        'relationships': [],
                        'stats': {
                            'total_nodes': 1,
                            'total_relationships': 0,
                            'page_nodes': 1,
                            'external_link_nodes': 0,
                            'element_nodes': 0
                        }
                    }

                # Process the full graph result
                center_page = dict(record['center'].items()) if record['center'] else {}
                connected_nodes = record['connected_nodes'] or []
                relationships = record['relationships'] or []

                # Convert nodes to dictionaries and categorize
                nodes = [center_page]  # Start with center page
                page_count = 1
                external_link_count = 0
                element_count = 0

                for node in connected_nodes:
                    node_dict = dict(node.items())
                    node_dict['labels'] = list(node.labels)
                    nodes.append(node_dict)

                    # Count node types
                    if 'Page' in node.labels:
                        page_count += 1
                    elif 'ExternalLink' in node.labels:
                        external_link_count += 1
                    elif 'Element' in node.labels:
                        element_count += 1

                # Convert relationships to dictionaries
                rel_list = []
                for rel in relationships:
                    if rel:  # Check if relationship exists
                        rel_dict = {
                            'type': rel.type,
                            'start_node': rel.start_node.get('url', rel.start_node.get('id', 'unknown')),
                            'end_node': rel.end_node.get('url', rel.end_node.get('id', 'unknown')),
                            'properties': dict(rel.items()) if hasattr(rel, 'items') else {}
                        }
                        rel_list.append(rel_dict)

                result_graph = {
                    'center_page': center_page,
                    'nodes': nodes,
                    'relationships': rel_list,
                    'stats': {
                        'total_nodes': len(nodes),
                        'total_relationships': len(rel_list),
                        'page_nodes': page_count,
                        'external_link_nodes': external_link_count,
                        'element_nodes': element_count,
                        'depth': depth
                    }
                }

                logging.info(f"Retrieved graph for {url}: {len(nodes)} nodes, {len(rel_list)} relationships")
                return result_graph

        except Exception as e:
            logging.error(f"Failed to get page graph for {url}: {str(e)}")
            raise

    def find_shortest_path(self, start_url: str, end_url: str, max_depth: int = 10) -> Dict[str, Any]:
        """
        Find the shortest path between two pages in the graph.

        Args:
            start_url (str): URL of the starting page
            end_url (str): URL of the destination page
            max_depth (int): Maximum depth to search (default: 10)

        Returns:
            dict: Dictionary containing path information
                {
                    'path_found': bool,
                    'path_length': int,
                    'nodes': [...],
                    'relationships': [...],
                    'total_distance': int
                }

        Raises:
            ValueError: If URLs are empty or invalid
            Exception: If path finding fails
        """
        if not start_url or not start_url.strip():
            raise ValueError("Start URL cannot be empty")

        if not end_url or not end_url.strip():
            raise ValueError("End URL cannot be empty")

        if start_url == end_url:
            # Same node - return single node path
            try:
                with self.driver.session() as session:
                    result = session.run("MATCH (p:Page {url: $url}) RETURN p", {'url': start_url})
                    record = result.single()
                    if record:
                        node_data = dict(record['p'].items())
                        return {
                            'path_found': True,
                            'path_length': 0,
                            'nodes': [node_data],
                            'relationships': [],
                            'total_distance': 0
                        }
                    else:
                        return {
                            'path_found': False,
                            'path_length': 0,
                            'nodes': [],
                            'relationships': [],
                            'total_distance': 0,
                            'error': 'Start node not found'
                        }
            except Exception as e:
                logging.error(f"Failed to find single node: {str(e)}")
                raise

        if max_depth < 1 or max_depth > 20:
            raise ValueError("Max depth must be between 1 and 20")

        cypher_query = f"""
        MATCH (start:Page {{url: $start_url}})
        MATCH (end:Page {{url: $end_url}})
        MATCH path = shortestPath((start)-[*1..{max_depth}]-(end))
        RETURN
            path,
            length(path) as path_length,
            nodes(path) as path_nodes,
            relationships(path) as path_relationships
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, {
                    'start_url': start_url,
                    'end_url': end_url
                })
                record = result.single()

                if not record:
                    # No path found - verify both nodes exist
                    start_exists = session.run("MATCH (p:Page {url: $url}) RETURN count(p) as count",
                                             {'url': start_url}).single()['count'] > 0
                    end_exists = session.run("MATCH (p:Page {url: $url}) RETURN count(p) as count",
                                           {'url': end_url}).single()['count'] > 0

                    error_msg = []
                    if not start_exists:
                        error_msg.append(f"Start node not found: {start_url}")
                    if not end_exists:
                        error_msg.append(f"End node not found: {end_url}")

                    if not error_msg:
                        error_msg.append("No path exists between the specified nodes")

                    return {
                        'path_found': False,
                        'path_length': 0,
                        'nodes': [],
                        'relationships': [],
                        'total_distance': 0,
                        'error': '; '.join(error_msg)
                    }

                # Process the path result
                path_length = record['path_length']
                path_nodes = record['path_nodes'] or []
                path_relationships = record['path_relationships'] or []

                # Convert nodes to dictionaries
                nodes_data = []
                for node in path_nodes:
                    node_dict = dict(node.items())
                    node_dict['labels'] = list(node.labels)
                    nodes_data.append(node_dict)

                # Convert relationships to dictionaries
                relationships_data = []
                for rel in path_relationships:
                    rel_dict = {
                        'type': rel.type,
                        'start_node': rel.start_node.get('url', rel.start_node.get('id', 'unknown')),
                        'end_node': rel.end_node.get('url', rel.end_node.get('id', 'unknown')),
                        'properties': dict(rel.items()) if hasattr(rel, 'items') else {}
                    }
                    relationships_data.append(rel_dict)

                result_data = {
                    'path_found': True,
                    'path_length': path_length,
                    'nodes': nodes_data,
                    'relationships': relationships_data,
                    'total_distance': path_length,
                    'start_url': start_url,
                    'end_url': end_url
                }

                logging.info(f"Found shortest path from {start_url} to {end_url}: {path_length} hops")
                return result_data

        except Exception as e:
            logging.error(f"Failed to find shortest path from {start_url} to {end_url}: {str(e)}")
            raise


class ContentProcessor:
    def __init__(self, openai_api_key: str):
        """
        Initialize the ContentProcessor with OpenAI API configuration.

        Args:
            openai_api_key (str): OpenAI API key for accessing embedding and completion services

        Raises:
            ValueError: If API key is empty or invalid
            Exception: If OpenAI client initialization fails
        """
        if not openai_api_key or not openai_api_key.strip():
            raise ValueError("OpenAI API key cannot be empty")

        self.api_key = openai_api_key
        self.client = None

        try:
            # Initialize OpenAI client
            self.client = openai.OpenAI(api_key=openai_api_key)

            # Test the connection with a simple request
            # This will verify the API key is valid
            test_response = self.client.models.list()

            # Set default embedding model
            self.embedding_model = "text-embedding-3-small"
            self.completion_model = "gpt-3.5-turbo"

            # Configuration for API calls
            self.max_tokens_per_request = 8000  # Safe limit for text-embedding-3-small
            self.max_summary_tokens = 500
            self.batch_size = 100  # For batch embedding requests

            logging.info("ContentProcessor initialized successfully with OpenAI API")

        except Exception as e:
            logging.error(f"Failed to initialize ContentProcessor with OpenAI API: {str(e)}")
            raise

    def generate_summary(self, text: str) -> str:
        """
        Generate a concise summary of the provided text using OpenAI API.

        Args:
            text (str): The text content to summarize

        Returns:
            str: A concise summary of the input text

        Raises:
            ValueError: If text is empty or too long
            Exception: If summary generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text content cannot be empty")

        # Clean and preprocess the text
        cleaned_text = text.strip()

        # Check text length and truncate if necessary
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        estimated_tokens = len(cleaned_text) // 4

        if estimated_tokens > self.max_tokens_per_request:
            # Truncate text to fit within token limits
            max_chars = self.max_tokens_per_request * 4
            cleaned_text = cleaned_text[:max_chars]
            logging.warning(f"Text truncated from {len(text)} to {len(cleaned_text)} characters to fit token limits")

        # Prepare the prompt for summarization
        system_prompt = """You are an expert at creating concise, informative summaries of web page content.
Generate a clear and comprehensive summary that captures the main topics, key information, and purpose of the content.
Focus on the most important information and maintain the context."""

        user_prompt = f"Please provide a concise summary of the following web page content:\n\n{cleaned_text}"

        try:
            # Make API call to OpenAI
            response = self.client.chat.completions.create(
                model=self.completion_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_summary_tokens,
                temperature=0.3,  # Low temperature for consistent, factual summaries
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            # Extract the summary from the response
            if response.choices and len(response.choices) > 0:
                summary = response.choices[0].message.content.strip()

                if not summary:
                    raise Exception("Empty summary received from OpenAI API")

                # Log token usage for monitoring
                usage = response.usage
                if usage:
                    logging.info(f"Summary generated - Input tokens: {usage.prompt_tokens}, "
                               f"Output tokens: {usage.completion_tokens}, "
                               f"Total tokens: {usage.total_tokens}")

                logging.info(f"Successfully generated summary of {len(summary)} characters from {len(cleaned_text)} character input")
                return summary

            else:
                raise Exception("No response choices received from OpenAI API")

        except openai.RateLimitError as e:
            logging.error(f"OpenAI API rate limit exceeded: {str(e)}")
            raise Exception(f"Rate limit exceeded while generating summary: {str(e)}")

        except openai.APIError as e:
            logging.error(f"OpenAI API error during summary generation: {str(e)}")
            raise Exception(f"API error while generating summary: {str(e)}")

        except openai.AuthenticationError as e:
            logging.error(f"OpenAI API authentication error: {str(e)}")
            raise Exception(f"Authentication error while generating summary: {str(e)}")

        except Exception as e:
            logging.error(f"Failed to generate summary: {str(e)}")
            raise Exception(f"Summary generation failed: {str(e)}")

    def create_embedding(self, text: str) -> List[float]:
        """
        Create text embedding vector using OpenAI's embedding model.

        Args:
            text (str): The text content to create an embedding for

        Returns:
            List[float]: Vector embedding of the input text

        Raises:
            ValueError: If text is empty or too long
            Exception: If embedding creation fails
        """
        if not text or not text.strip():
            raise ValueError("Text content cannot be empty")

        # Clean and preprocess the text
        cleaned_text = text.strip()

        # Remove excessive whitespace and newlines
        import re
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

        # Check text length and truncate if necessary
        # text-embedding-3-small has a token limit of 8191 tokens
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        estimated_tokens = len(cleaned_text) // 4

        if estimated_tokens > self.max_tokens_per_request:
            # Truncate text to fit within token limits
            max_chars = self.max_tokens_per_request * 4
            cleaned_text = cleaned_text[:max_chars]
            logging.warning(f"Text truncated from {len(text)} to {len(cleaned_text)} characters for embedding")

        try:
            # Make API call to create embedding
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=cleaned_text,
                encoding_format="float"
            )

            # Extract embedding from response
            if response.data and len(response.data) > 0:
                embedding = response.data[0].embedding

                if not embedding:
                    raise Exception("Empty embedding received from OpenAI API")

                # Validate embedding format
                if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
                    raise Exception("Invalid embedding format received from OpenAI API")

                # Log token usage for monitoring
                usage = response.usage
                if usage:
                    logging.info(f"Embedding created - Input tokens: {usage.prompt_tokens}, "
                               f"Total tokens: {usage.total_tokens}")

                logging.info(f"Successfully created embedding with {len(embedding)} dimensions from {len(cleaned_text)} character input")
                return embedding

            else:
                raise Exception("No embedding data received from OpenAI API")

        except openai.RateLimitError as e:
            logging.error(f"OpenAI API rate limit exceeded during embedding creation: {str(e)}")
            raise Exception(f"Rate limit exceeded while creating embedding: {str(e)}")

        except openai.APIError as e:
            logging.error(f"OpenAI API error during embedding creation: {str(e)}")
            raise Exception(f"API error while creating embedding: {str(e)}")

        except openai.AuthenticationError as e:
            logging.error(f"OpenAI API authentication error during embedding creation: {str(e)}")
            raise Exception(f"Authentication error while creating embedding: {str(e)}")

        except Exception as e:
            logging.error(f"Failed to create embedding: {str(e)}")
            raise Exception(f"Embedding creation failed: {str(e)}")