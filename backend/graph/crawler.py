import httpx
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from collections import deque
from typing import Dict, List, Set, Optional, Tuple
import hashlib
import logging
from datetime import datetime
import time
import random

class WebCrawler:
    def __init__(
        self,
        neo4j_uri: str,
        neo4j_auth: Tuple[str, str],
        openai_api_key: str,
        base_url: str,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        delay: float = 1.0,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize the WebCrawler with necessary configurations.

        Args:
            neo4j_uri: URI for Neo4j database connection
            neo4j_auth: Tuple of (username, password) for Neo4j
            openai_api_key: API key for OpenAI embeddings
            base_url: Starting URL for crawling
            user_agent: User agent string for HTTP requests
            delay: Delay between requests in seconds
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        from neo4j_manager import Neo4jManager
        from content_processor import ContentProcessor

        self.base_url = self._normalize_url(base_url)
        self.base_domain = urlparse(self.base_url).netloc
        self.user_agent = user_agent
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries

        self.neo4j_manager = Neo4jManager(neo4j_uri, neo4j_auth)
        self.content_processor = ContentProcessor(openai_api_key)

        self.client = httpx.Client(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            timeout=timeout,
            follow_redirects=True
        )

        self.url_queue = deque([self.base_url])
        self.visited_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"WebCrawler initialized for {self.base_url}")
        self.logger.info(f"Base domain: {self.base_domain}")

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments and trailing slashes.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL string
        """
        parsed = urlparse(url)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/') if parsed.path != '/' else '/',
            parsed.params,
            parsed.query,
            ''
        ))
        return normalized

    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid for crawling (same domain as base_url).

        Args:
            url: URL to validate

        Returns:
            True if URL should be crawled, False otherwise
        """
        try:
            parsed = urlparse(url)

            # Check if URL has a valid scheme
            if parsed.scheme not in ('http', 'https'):
                return False

            # Check if URL belongs to the same domain
            if parsed.netloc != self.base_domain:
                self.logger.debug(f"URL {url} is external (domain: {parsed.netloc})")
                return False

            # Avoid common non-HTML resources
            excluded_extensions = (
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
                '.pdf', '.zip', '.tar', '.gz', '.rar',
                '.mp3', '.mp4', '.avi', '.mov', '.wmv',
                '.css', '.js', '.json', '.xml',
                '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
            )

            if any(parsed.path.lower().endswith(ext) for ext in excluded_extensions):
                self.logger.debug(f"URL {url} has excluded extension")
                return False

            return True

        except Exception as e:
            self.logger.warning(f"Error validating URL {url}: {e}")
            return False

    def fetch_page(self, url: str) -> Optional[Dict]:
        """
        Fetch a web page and return its metadata and content.

        Args:
            url: URL to fetch

        Returns:
            Dictionary containing page data or None if fetch failed
        """
        try:
            start_time = time.time()

            self.logger.info(f"Fetching URL: {url}")

            # Add small random delay before each request to look more human
            pre_request_delay = random.uniform(0.5, 2.0)
            self.logger.debug(f"Pre-request delay: {pre_request_delay:.2f}s")
            time.sleep(pre_request_delay)

            # Make the HTTP request with retries
            response = None
            last_error = None

            for attempt in range(self.max_retries):
                try:
                    response = self.client.get(url)
                    response.raise_for_status()
                    break
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code == 404:
                        self.logger.warning(f"404 Not Found: {url}")
                        self.failed_urls[url] = "404 Not Found"
                        return None
                    elif e.response.status_code in (500, 502, 503, 504):
                        self.logger.warning(f"Server error {e.response.status_code} for {url}, attempt {attempt + 1}/{self.max_retries}")
                        if attempt < self.max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        self.logger.warning(f"HTTP error {e.response.status_code} for {url}")
                        self.failed_urls[url] = f"HTTP {e.response.status_code}"
                        return None
                except httpx.TimeoutException as e:
                    last_error = e
                    self.logger.warning(f"Timeout fetching {url}, attempt {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                except Exception as e:
                    last_error = e
                    self.logger.error(f"Unexpected error fetching {url}: {e}")
                    self.failed_urls[url] = str(e)
                    return None

            if response is None:
                self.logger.error(f"Failed to fetch {url} after {self.max_retries} retries: {last_error}")
                self.failed_urls[url] = str(last_error)
                return None

            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                self.logger.info(f"Skipping non-HTML content: {content_type} for {url}")
                return None

            # Get final URL after redirects
            final_url = str(response.url)

            # Create page data dictionary
            page_data = {
                'url': self._normalize_url(final_url),
                'original_url': self._normalize_url(url),
                'html_content': response.text,
                'http_status': response.status_code,
                'response_time_ms': response_time,
                'content_type': content_type,
                'headers': dict(response.headers),
                'fetched_at': datetime.now().isoformat(),
                'content_length': len(response.content)
            }

            self.logger.info(f"Successfully fetched {url} - Status: {response.status_code}, Size: {page_data['content_length']} bytes, Time: {response_time:.2f}ms")

            return page_data

        except Exception as e:
            self.logger.error(f"Unexpected error in fetch_page for {url}: {e}")
            self.failed_urls[url] = str(e)
            return None

    def parse_page(self, html_content: str, base_url: str) -> Dict:
        """
        Parse HTML content and extract structured data.

        Args:
            html_content: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            Dictionary containing parsed page data
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract all links
        links = self.extract_links(soup, base_url)

        # Extract content and metadata
        content_data = self.extract_content(soup)

        # Extract clickable elements
        elements = self._extract_elements(soup, base_url)

        return {
            'links': links,
            'content': content_data,
            'elements': elements
        }

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Extract all links from the page.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of link dictionaries with URL and metadata
        """
        links = []

        # Find all anchor tags
        for anchor in soup.find_all('a', href=True):
            href = anchor['href'].strip()

            # Skip empty hrefs, fragments only, and special protocols
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue

            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            normalized_url = self._normalize_url(absolute_url)

            # Determine if link is internal or external
            is_external = not self.is_valid_url(normalized_url)

            link_data = {
                'url': normalized_url,
                'text': anchor.get_text(strip=True)[:200],  # Limit text length
                'title': anchor.get('title', ''),
                'is_external': is_external,
                'original_href': href
            }

            links.append(link_data)

        # Also extract form action URLs
        for form in soup.find_all('form', action=True):
            action = form['action'].strip()
            if action and not action.startswith('#'):
                absolute_url = urljoin(base_url, action)
                normalized_url = self._normalize_url(absolute_url)
                is_external = not self.is_valid_url(normalized_url)

                links.append({
                    'url': normalized_url,
                    'text': 'Form submission',
                    'title': form.get('name', ''),
                    'is_external': is_external,
                    'original_href': action,
                    'type': 'form'
                })

        return links

    def extract_content(self, soup: BeautifulSoup) -> Dict:
        """
        Extract main content and metadata from the page.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Dictionary containing extracted content
        """
        # Remove script and style elements
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()

        # Extract title
        title = ''
        if soup.title:
            title = soup.title.get_text(strip=True)

        # Extract meta description
        meta_description = ''
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag:
            meta_description = meta_tag.get('content', '')

        # Extract meta keywords
        meta_keywords = ''
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag:
            meta_keywords = keywords_tag.get('content', '')

        # Extract all text content
        text_content = soup.get_text(separator=' ', strip=True)
        # Clean up excessive whitespace
        text_content = ' '.join(text_content.split())

        # Extract headers hierarchy
        headers = {
            'h1': [h.get_text(strip=True) for h in soup.find_all('h1')],
            'h2': [h.get_text(strip=True) for h in soup.find_all('h2')],
            'h3': [h.get_text(strip=True) for h in soup.find_all('h3')]
        }

        # Extract image alt texts
        alt_texts = [img.get('alt', '') for img in soup.find_all('img', alt=True)]

        # Extract structured data (JSON-LD)
        structured_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                structured_data.append(data)
            except:
                pass

        return {
            'title': title[:500],  # Limit title length
            'meta_description': meta_description[:1000],
            'meta_keywords': meta_keywords[:500],
            'text_content': text_content[:50000],  # Limit content for embedding
            'headers': headers,
            'alt_texts': alt_texts,
            'structured_data': structured_data,
            'content_hash': hashlib.sha256(text_content.encode()).hexdigest()
        }

    def _extract_elements(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Extract interactive elements (buttons, links, forms).

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of element dictionaries
        """
        elements = []

        # Extract buttons
        for button in soup.find_all(['button', 'input']):
            if button.name == 'input' and button.get('type') not in ['button', 'submit']:
                continue

            element = {
                'type': 'button',
                'text': button.get_text(strip=True) if button.name == 'button' else button.get('value', ''),
                'id': button.get('id', ''),
                'class': ' '.join(button.get('class', [])),
                'onclick': button.get('onclick', ''),
                'attributes': dict(button.attrs)
            }
            elements.append(element)

        return elements

    def should_crawl(self, url: str) -> bool:
        """
        Determine if a URL should be crawled.

        Args:
            url: URL to check

        Returns:
            True if URL should be crawled, False otherwise
        """
        normalized_url = self._normalize_url(url)

        # Check if already visited
        if normalized_url in self.visited_urls:
            return False

        # Check if already in queue
        if normalized_url in self.url_queue:
            return False

        # Check if URL is valid for crawling
        if not self.is_valid_url(normalized_url):
            return False

        # Check if URL failed previously
        if normalized_url in self.failed_urls:
            return False

        return True

    def update_queue(self, new_urls: List[str]):
        """
        Update the URL queue with new URLs to crawl.

        Args:
            new_urls: List of URLs to add to queue
        """
        for url in new_urls:
            normalized_url = self._normalize_url(url)
            if self.should_crawl(normalized_url):
                self.url_queue.append(normalized_url)
                self.logger.debug(f"Added to queue: {normalized_url}")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text content using OpenAI.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            return None

        try:
            return self.content_processor.create_embedding(text)
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return None

    def store_to_neo4j(self, page_data: Dict, links_data: List[Dict]):
        """
        Store page data and relationships in Neo4j.

        Args:
            page_data: Dictionary containing page information
            links_data: List of dictionaries containing link information
        """
        try:
            # Create or update page node
            node_id = self.neo4j_manager.create_page_node(page_data)

            # Create relationships to linked pages
            for link in links_data:
                if link['is_external']:
                    # Create external link node and relationship
                    self.neo4j_manager.create_external_link(page_data['url'], link['url'])
                else:
                    # Create relationship to internal page (will be created when crawled)
                    self.neo4j_manager.create_relationship(
                        page_data['url'],
                        link['url'],
                        'LINKS_TO'
                    )

            # Store elements as related nodes
            if 'elements' in page_data:
                for element in page_data['elements']:
                    self.neo4j_manager.create_element_node(page_data['url'], element)

            self.logger.info(f"Stored page data for {page_data['url']} with {len(links_data)} links")

        except Exception as e:
            self.logger.error(f"Failed to store data in Neo4j: {e}")

    def crawl(self, max_pages: int = 1000, max_depth: int = 10) -> Dict:
        """
        Main crawling method that orchestrates the entire process.

        Args:
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum depth to crawl from base URL

        Returns:
            Dictionary containing crawl statistics
        """
        start_time = time.time()
        pages_crawled = 0

        # Track depth of URLs
        url_depths = {self.base_url: 0}

        self.logger.info(f"Starting crawl from {self.base_url} with max_pages={max_pages}, max_depth={max_depth}")

        while self.url_queue and pages_crawled < max_pages:
            current_url = self.url_queue.popleft()

            # Check depth limit
            current_depth = url_depths.get(current_url, 0)
            if current_depth > max_depth:
                self.logger.debug(f"Skipping {current_url} - exceeds max depth {max_depth}")
                continue

            # Skip if already visited
            if current_url in self.visited_urls:
                continue

            # Mark as visited
            self.visited_urls.add(current_url)

            # Fetch the page
            page_data = self.fetch_page(current_url)
            if not page_data:
                continue

            # Parse the page
            parsed_data = self.parse_page(page_data['html_content'], current_url)

            # Combine page data with parsed data
            page_data.update(parsed_data['content'])
            page_data['elements'] = parsed_data['elements']

            # Generate embedding for content
            embedding_text = f"{page_data.get('title', '')} {page_data.get('meta_description', '')} {page_data.get('text_content', '')}"
            embedding = self.generate_embedding(embedding_text[:8000])  # Limit text for embedding
            if embedding:
                page_data['content_vector'] = embedding

            # Extract domain and path
            parsed_url = urlparse(current_url)
            page_data['domain'] = parsed_url.netloc
            page_data['path'] = parsed_url.path

            # Store in Neo4j
            self.store_to_neo4j(page_data, parsed_data['links'])

            # Add new URLs to queue
            new_urls = []
            for link in parsed_data['links']:
                if not link['is_external'] and link['url'] not in self.visited_urls:
                    new_urls.append(link['url'])
                    # Track depth for new URLs
                    url_depths[link['url']] = current_depth + 1

            self.update_queue(new_urls)

            pages_crawled += 1
            self.logger.info(f"Progress: {pages_crawled}/{max_pages} pages crawled, {len(self.url_queue)} in queue")

            # Respect crawl delay with random variation to look more human
            if self.delay > 0 and self.url_queue:
                # Add random delay between 1-4 seconds to mimic human behavior
                random_delay = random.uniform(1.0, 4.0)
                self.logger.debug(f"Sleeping for {random_delay:.2f} seconds (human-like delay)")
                time.sleep(random_delay)

        # Calculate statistics
        elapsed_time = time.time() - start_time
        stats = {
            'pages_crawled': pages_crawled,
            'pages_failed': len(self.failed_urls),
            'unique_urls_found': len(self.visited_urls),
            'elapsed_time_seconds': elapsed_time,
            'pages_per_second': pages_crawled / elapsed_time if elapsed_time > 0 else 0,
            'failed_urls': self.failed_urls
        }

        self.logger.info(f"Crawl completed: {stats}")
        return stats

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.client.close()
        self.neo4j_manager.close()
        self.logger.info("WebCrawler resources cleaned up")