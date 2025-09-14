from collections import deque
from urllib.parse import urlparse, urlunparse, urljoin
import openai
from neo4j import GraphDatabase
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
import os
import re


class WebCrawler:
    def __init__(self, neo4j_uri, neo4j_auth, openai_api_key, base_url, blacklist=None):
        """
        Initialize the WebCrawler with necessary configurations.

        Args:
            neo4j_uri (str): Neo4j database URI
            neo4j_auth (tuple): Neo4j authentication (username, password)
            openai_api_key (str): OpenAI API key for embeddings
            base_url (str): Starting URL to crawl
            blacklist (list): List of URL patterns or paths to exclude from crawling
        """
        # Database and API configuration
        self.neo4j_uri = neo4j_uri
        self.neo4j_auth = neo4j_auth
        self.openai_api_key = openai_api_key

        # Initialize Neo4j driver
        self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)

        # Initialize OpenAI client
        openai.api_key = openai_api_key
        self.openai_client = openai

        # Crawling configuration
        self.base_url = base_url
        self.base_domain = self.extract_domain(base_url)
        self.blacklist = blacklist or []

        # URL management
        self.url_queue = deque([(base_url, 0)])  # (url, depth)
        self.visited_urls = set()
        self.failed_urls = set()

        # Crawl statistics
        self.pages_crawled = 0

        # Selenium driver (initialized lazily)
        self.selenium_driver = None

    def extract_domain(self, url):
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def is_blacklisted(self, url):
        """
        Check if URL matches any blacklist pattern.

        Args:
            url (str): URL to check against blacklist

        Returns:
            bool: True if URL should be blacklisted, False otherwise
        """
        if not self.blacklist:
            return False

        parsed_url = urlparse(url.lower())
        url_path = parsed_url.path
        full_url_lower = url.lower()

        for pattern in self.blacklist:
            pattern_lower = pattern.lower()

            # Check if pattern matches the path
            if url_path.startswith(pattern_lower):
                return True

            # Check if pattern is contained in the full URL
            if pattern_lower in full_url_lower:
                return True

            # Check if pattern matches with regex (if it looks like a regex)
            if any(char in pattern for char in ['*', '?', '[', ']', '^', '$']):
                try:
                    if re.search(pattern_lower, full_url_lower):
                        return True
                except re.error:
                    # If regex is invalid, treat as literal string
                    continue

        return False

    def _get_selenium_driver(self):
        """Initialize and return Selenium Firefox driver with profile."""
        if self.selenium_driver is None:
            options = Options()

            # Use specific Firefox profile to preserve cookies and sessions
            profile_path = os.path.expanduser("/Users/ritesh/Library/Application Support/Firefox/Profiles/")
            specific_profile = os.path.join(profile_path, "ra0lmepf.default-release")

            if os.path.exists(specific_profile):
                options.add_argument("-profile")
                options.add_argument(specific_profile)

           # Create Firefox driver with profile
            self.selenium_driver = webdriver.Firefox(options=options)

        return self.selenium_driver

    def fetch_page(self, url):
        """
        Fetch page content using Selenium to handle JavaScript rendering.

        Args:
            url (str): URL to fetch

        Returns:
            dict: Page data including content, status, response time, etc.
        """
        start_time = time.time()

        try:
            driver = self._get_selenium_driver()

            # Navigate to URL
            driver.get(url)

            # Wait for page to load (wait for body element)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Get page source after JavaScript execution
            html_content = driver.page_source

            # Get final URL (after redirects)
            final_url = driver.current_url

            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            return {
                'url': final_url,
                'original_url': url,
                'html_content': html_content,
                'http_status': 200,  # Selenium doesn't provide HTTP status, assume success
                'response_time_ms': response_time,
                'error': None
            }

        except TimeoutException:
            response_time = (time.time() - start_time) * 1000
            return {
                'url': url,
                'original_url': url,
                'html_content': None,
                'http_status': 408,  # Request timeout
                'response_time_ms': response_time,
                'error': 'Page load timeout'
            }

        except WebDriverException as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'url': url,
                'original_url': url,
                'html_content': None,
                'http_status': 500,  # Server error
                'response_time_ms': response_time,
                'error': f'WebDriver error: {str(e)}'
            }

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'url': url,
                'original_url': url,
                'html_content': None,
                'http_status': 500,  # Server error
                'response_time_ms': response_time,
                'error': f'Unexpected error: {str(e)}'
            }

    def parse_page(self, html_content, base_url):
        """
        Parse HTML content using BeautifulSoup and extract structured data.

        Args:
            html_content (str): Raw HTML content from the page
            base_url (str): Base URL for resolving relative links

        Returns:
            dict: Parsed page data including links, content, metadata
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Extract page title
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else ''

            # Extract meta description
            meta_description = ''
            meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_desc_tag:
                meta_description = meta_desc_tag.get('content', '').strip()

            # Extract meta keywords
            meta_keywords = ''
            meta_keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords_tag:
                meta_keywords = meta_keywords_tag.get('content', '').strip()

            # Extract all text content
            text_content = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content_text = ' '.join(chunk for chunk in chunks if chunk)

            # Extract header hierarchy
            headers = {}
            for i in range(1, 7):
                header_tags = soup.find_all(f'h{i}')
                headers[f'h{i}'] = [h.get_text().strip() for h in header_tags]

            # Extract all links
            links = self.extract_links(soup, base_url)

            # Extract clickable elements (buttons, forms)
            clickable_elements = self.extract_clickable_elements(soup, base_url)

            # Extract images with alt text
            images = []
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src')
                if src:
                    # Resolve relative URLs
                    absolute_src = urljoin(base_url, src)
                    images.append({
                        'src': absolute_src,
                        'alt': img.get('alt', '').strip(),
                        'title': img.get('title', '').strip()
                    })

            # Extract structured data (JSON-LD)
            structured_data = []
            json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    structured_data.append(data)
                except (json.JSONDecodeError, TypeError):
                    continue

            return {
                'title': title,
                'meta_description': meta_description,
                'meta_keywords': meta_keywords,
                'content_text': content_text,
                'headers': headers,
                'links': links,
                'clickable_elements': clickable_elements,
                'images': images,
                'structured_data': structured_data,
                'content_length': len(content_text),
                'link_count': len(links),
                'image_count': len(images)
            }

        except Exception as e:
            return {
                'title': '',
                'meta_description': '',
                'meta_keywords': '',
                'content_text': '',
                'headers': {},
                'links': [],
                'clickable_elements': [],
                'images': [],
                'structured_data': [],
                'content_length': 0,
                'link_count': 0,
                'image_count': 0,
                'parse_error': f'Parse error: {str(e)}'
            }

    def extract_links(self, soup, base_url):
        """Extract all links from the page with detailed attributes."""
        links = []

        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if not href or href.startswith('#'):
                continue

            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)

            # Get link text
            link_text = link.get_text().strip()

            # Extract JavaScript event handlers
            js_events = {}
            for attr in ['onclick', 'onmousedown', 'onmouseup', 'ondblclick']:
                if link.get(attr):
                    js_events[attr] = link.get(attr)

            # Extract data attributes
            data_attrs = {k: v for k, v in link.attrs.items() if k.startswith('data-')}

            links.append({
                'url': absolute_url,
                'text': link_text,
                'title': link.get('title', '').strip(),
                'is_external': self.extract_domain(absolute_url) != self.extract_domain(base_url),
                'class': link.get('class', []),
                'id': link.get('id', ''),
                'rel': link.get('rel', []),
                'target': link.get('target', ''),
                'tabindex': link.get('tabindex', ''),
                'aria_label': link.get('aria-label', ''),
                'role': link.get('role', ''),
                'js_events': js_events,
                'data_attributes': data_attrs,
                'download': link.get('download', ''),
                'type': link.get('type', ''),
                'raw_html': str(link)
            })

        return links

    def extract_clickable_elements(self, soup, base_url):
        """Extract clickable elements like buttons, forms, and JavaScript-enabled elements."""
        elements = []

        # Extract buttons
        for button in soup.find_all('button'):
            onclick = button.get('onclick', '')
            data_attrs = {k: v for k, v in button.attrs.items() if k.startswith('data-')}

            # Look for JavaScript event handlers
            js_events = {}
            for attr in ['onclick', 'onmousedown', 'onmouseup', 'ondblclick']:
                if button.get(attr):
                    js_events[attr] = button.get(attr)

            elements.append({
                'type': 'button',
                'text': button.get_text().strip(),
                'onclick': onclick,
                'js_events': js_events,
                'data_attributes': data_attrs,
                'id': button.get('id', ''),
                'class': button.get('class', []),
                'aria_label': button.get('aria-label', ''),
                'role': button.get('role', ''),
                'disabled': button.has_attr('disabled')
            })

        # Extract elements with click event handlers (div, span, etc.)
        clickable_selectors = ['[onclick]', '[data-action]', '[data-click]', '[data-toggle]',
                              '[role="button"]', '[tabindex]', '.btn', '.button', '.clickable']

        for selector in clickable_selectors:
            for element in soup.select(selector):
                if element.name in ['button', 'input', 'a', 'form']:  # Skip already processed elements
                    continue

                onclick = element.get('onclick', '')
                data_attrs = {k: v for k, v in element.attrs.items() if k.startswith('data-')}

                # Look for JavaScript event handlers
                js_events = {}
                for attr in ['onclick', 'onmousedown', 'onmouseup', 'ondblclick']:
                    if element.get(attr):
                        js_events[attr] = element.get(attr)

                elements.append({
                    'type': 'clickable_element',
                    'tag': element.name,
                    'text': element.get_text().strip()[:100],  # Limit text length
                    'onclick': onclick,
                    'js_events': js_events,
                    'data_attributes': data_attrs,
                    'id': element.get('id', ''),
                    'class': element.get('class', []),
                    'role': element.get('role', ''),
                    'aria_label': element.get('aria-label', ''),
                    'tabindex': element.get('tabindex', '')
                })

        # Extract form submission elements
        for form in soup.find_all('form'):
            action = form.get('action', '')
            if action:
                absolute_action = urljoin(base_url, action)
            else:
                absolute_action = base_url

            # Look for form event handlers
            js_events = {}
            for attr in ['onsubmit', 'onreset']:
                if form.get(attr):
                    js_events[attr] = form.get(attr)

            elements.append({
                'type': 'form',
                'action': absolute_action,
                'method': form.get('method', 'get').lower(),
                'js_events': js_events,
                'id': form.get('id', ''),
                'class': form.get('class', []),
                'enctype': form.get('enctype', '')
            })

        # Extract input buttons and clickable inputs
        for input_btn in soup.find_all('input', {'type': ['submit', 'button', 'image']}):
            onclick = input_btn.get('onclick', '')

            # Look for JavaScript event handlers
            js_events = {}
            for attr in ['onclick', 'onmousedown', 'onmouseup']:
                if input_btn.get(attr):
                    js_events[attr] = input_btn.get(attr)

            elements.append({
                'type': 'input_button',
                'input_type': input_btn.get('type'),
                'value': input_btn.get('value', ''),
                'onclick': onclick,
                'js_events': js_events,
                'id': input_btn.get('id', ''),
                'class': input_btn.get('class', []),
                'disabled': input_btn.has_attr('disabled')
            })

        return elements

    def generate_embedding(self, text):
        """
        Generate text embedding using OpenAI API.

        Args:
            text (str): Text content to embed

        Returns:
            list: Embedding vector
        """
        if not text or not text.strip():
            return []

        try:
            # Clean and truncate text if needed
            cleaned_text = text.strip()
            # OpenAI has token limits, roughly 1 token = 4 chars
            max_chars = 8000 * 4  # Safe limit for text-embedding-3-small
            if len(cleaned_text) > max_chars:
                cleaned_text = cleaned_text[:max_chars]

            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=cleaned_text
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return []

    def is_valid_url(self, url):
        """Check if URL is valid and should be crawled."""
        try:
            parsed = urlparse(url)
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            # Only http/https
            if parsed.scheme not in ['http', 'https']:
                return False
            return True
        except:
            return False

    def should_crawl(self, url, current_depth, max_depth):
        """
        Determine if a URL should be crawled based on rules.

        Args:
            url (str): URL to check
            current_depth (int): Current crawl depth
            max_depth (int): Maximum allowed depth

        Returns:
            bool: True if URL should be crawled
        """
        # Check depth limit
        if current_depth >= max_depth:
            return False

        # Check if already visited or failed
        if url in self.visited_urls or url in self.failed_urls:
            return False

        # Check if valid URL
        if not self.is_valid_url(url):
            return False

        # Check domain boundary
        url_domain = self.extract_domain(url)
        if url_domain != self.base_domain:
            return False

        # Check if URL is blacklisted
        if self.is_blacklisted(url):
            return False

        # Skip common non-content URLs
        skip_patterns = [
            '#',  # Anchors
            'javascript:',  # JavaScript links
            'mailto:',  # Email links
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',  # Documents
            '.jpg', '.jpeg', '.png', '.gif', '.svg',  # Images
            '.mp4', '.avi', '.mov',  # Videos
            '.zip', '.tar', '.gz', '.rar'  # Archives
        ]

        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False

        return True

    def normalize_url(self, url):
        """Normalize URL for consistency."""
        try:
            parsed = urlparse(url.lower())
            # Remove fragment
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))
            return normalized
        except:
            return url

    def store_to_neo4j(self, page_data, links_data):
        """
        Store page data and detailed link information to Neo4j.

        Args:
            page_data (dict): Page information
            links_data (list): List of links found on the page with detailed attributes
        """
        try:
            # Create or update the page node
            with self.driver.session() as session:
                # Store the main page
                cypher_query = """
                MERGE (p:Page {url: $url})
                SET p.domain = $domain,
                    p.path = $path,
                    p.title = $title,
                    p.meta_description = $meta_description,
                    p.content_text = $content_text,
                    p.content_vector = $content_vector,
                    p.http_status = $http_status,
                    p.response_time_ms = $response_time_ms,
                    p.last_crawled = datetime(),
                    p.content_length = $content_length,
                    p.link_count = $link_count,
                    p.image_count = $image_count
                """

                parsed_url = urlparse(page_data['url'])

                session.run(cypher_query, {
                    'url': page_data['url'],
                    'domain': parsed_url.netloc,
                    'path': parsed_url.path,
                    'title': page_data.get('title', ''),
                    'meta_description': page_data.get('meta_description', ''),
                    'content_text': page_data.get('content_text', ''),
                    'content_vector': page_data.get('content_vector', []),
                    'http_status': page_data.get('http_status', 200),
                    'response_time_ms': page_data.get('response_time_ms', 0),
                    'content_length': page_data.get('content_length', 0),
                    'link_count': page_data.get('link_count', 0),
                    'image_count': page_data.get('image_count', 0)
                })

                # Store detailed link information
                for i, link in enumerate(links_data):
                    link_url = link['url']

                    # Create Link element node with all detailed attributes
                    link_element_id = f"{page_data['url']}#link_{i}"

                    cypher_link_element = """
                    MERGE (le:LinkElement {id: $link_id})
                    SET le.url = $url,
                        le.text = $text,
                        le.title = $title,
                        le.is_external = $is_external,
                        le.class = $class,
                        le.element_id = $element_id,
                        le.rel = $rel,
                        le.target = $target,
                        le.tabindex = $tabindex,
                        le.aria_label = $aria_label,
                        le.role = $role,
                        le.js_events = $js_events,
                        le.data_attributes = $data_attributes,
                        le.download = $download,
                        le.type = $type,
                        le.raw_html = $raw_html,
                        le.first_seen = CASE WHEN le.first_seen IS NULL THEN datetime() ELSE le.first_seen END,
                        le.last_seen = datetime()
                    """

                    # Convert lists and dicts to strings for Neo4j storage
                    js_events_str = str(link.get('js_events', {}))
                    data_attrs_str = str(link.get('data_attributes', {}))
                    class_str = ','.join(link.get('class', []) if isinstance(link.get('class', []), list) else [])
                    rel_str = ','.join(link.get('rel', []) if isinstance(link.get('rel', []), list) else [])

                    session.run(cypher_link_element, {
                        'link_id': link_element_id,
                        'url': link_url,
                        'text': link.get('text', '')[:500],  # Limit text length
                        'title': link.get('title', ''),
                        'is_external': link.get('is_external', False),
                        'class': class_str,
                        'element_id': link.get('id', ''),
                        'rel': rel_str,
                        'target': link.get('target', ''),
                        'tabindex': link.get('tabindex', ''),
                        'aria_label': link.get('aria_label', ''),
                        'role': link.get('role', ''),
                        'js_events': js_events_str,
                        'data_attributes': data_attrs_str,
                        'download': link.get('download', ''),
                        'type': link.get('type', ''),
                        'raw_html': link.get('raw_html', '')[:1000]  # Limit HTML length
                    })

                    # Create relationship from page to link element
                    cypher_page_to_link = """
                    MATCH (p:Page {url: $page_url})
                    MATCH (le:LinkElement {id: $link_id})
                    MERGE (p)-[:HAS_LINK_ELEMENT]->(le)
                    """

                    session.run(cypher_page_to_link, {
                        'page_url': page_data['url'],
                        'link_id': link_element_id
                    })

                    # Create relationships for target pages/external links
                    if link['is_external']:
                        # Create external link node and relationship from link element
                        cypher_external = """
                        MATCH (le:LinkElement {id: $link_id})
                        MERGE (to:ExternalLink {url: $to_url})
                        ON CREATE SET to.domain = $to_domain,
                                     to.first_seen = datetime()
                        MERGE (le)-[:TARGETS]->(to)
                        """
                        session.run(cypher_external, {
                            'link_id': link_element_id,
                            'to_url': link_url,
                            'to_domain': urlparse(link_url).netloc
                        })

                        # Also maintain the direct page-to-external relationship
                        cypher_page_external = """
                        MATCH (from:Page {url: $from_url})
                        MATCH (to:ExternalLink {url: $to_url})
                        MERGE (from)-[:LINKS_TO_EXTERNAL]->(to)
                        """
                        session.run(cypher_page_external, {
                            'from_url': page_data['url'],
                            'to_url': link_url
                        })
                    else:
                        # Create internal link relationship from link element
                        cypher_internal = """
                        MATCH (le:LinkElement {id: $link_id})
                        MERGE (to:Page {url: $to_url})
                        MERGE (le)-[:TARGETS]->(to)
                        """
                        session.run(cypher_internal, {
                            'link_id': link_element_id,
                            'to_url': link_url
                        })

                        # Also maintain the direct page-to-page relationship
                        cypher_page_internal = """
                        MATCH (from:Page {url: $from_url})
                        MATCH (to:Page {url: $to_url})
                        MERGE (from)-[:LINKS_TO]->(to)
                        """
                        session.run(cypher_page_internal, {
                            'from_url': page_data['url'],
                            'to_url': link_url
                        })

                print(f"Stored page data and {len(links_data)} detailed links for: {page_data['url']}")

        except Exception as e:
            print(f"Error storing to Neo4j: {str(e)}")

    def update_queue(self, new_urls, current_depth):
        """
        Add new URLs to the crawl queue.

        Args:
            new_urls (list): List of URLs to add
            current_depth (int): Depth of the current page
        """
        next_depth = current_depth + 1

        for url in new_urls:
            normalized_url = self.normalize_url(url)

            # Check if should add to queue
            if normalized_url not in self.visited_urls and \
               normalized_url not in self.failed_urls and \
               normalized_url not in [item[0] for item in self.url_queue]:

                self.url_queue.append((normalized_url, next_depth))

    def crawl(self, max_pages=1000, max_depth=10):
        """
        Main crawling method that orchestrates the entire crawling process.

        Args:
            max_pages (int): Maximum number of pages to crawl
            max_depth (int): Maximum depth to crawl

        Returns:
            dict: Crawl statistics
        """
        print(f"Starting crawl from: {self.base_url}")
        print(f"Max pages: {max_pages}, Max depth: {max_depth}")

        stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'total_links_found': 0,
            'external_links_found': 0,
            'start_time': time.time()
        }

        try:
            while self.url_queue and stats['pages_crawled'] < max_pages:
                # Get next URL from queue
                current_url, current_depth = self.url_queue.popleft()

                # Skip if shouldn't crawl
                if not self.should_crawl(current_url, current_depth, max_depth):
                    # Check if it was blacklisted for better logging
                    if self.is_blacklisted(current_url):
                        print(f"Skipping blacklisted URL: {current_url}")
                    continue

                # Mark as visited
                self.visited_urls.add(current_url)

                print(f"\nCrawling [{current_depth}/{max_depth}]: {current_url}")

                # Fetch the page
                page_response = self.fetch_page(current_url)

                if page_response['error']:
                    print(f"Failed to fetch: {page_response['error']}")
                    self.failed_urls.add(current_url)
                    stats['pages_failed'] += 1
                    continue

                # Parse the page
                parsed_data = self.parse_page(
                    page_response['html_content'],
                    page_response['url']
                )

                # Generate embedding for content
                embedding = []
                if parsed_data['content_text']:
                    embedding = self.generate_embedding(parsed_data['content_text'])

                # Prepare page data for storage
                page_data = {
                    'url': page_response['url'],
                    'title': parsed_data['title'],
                    'meta_description': parsed_data['meta_description'],
                    'content_text': parsed_data['content_text'][:5000],  # Limit for Neo4j
                    'content_vector': embedding,
                    'http_status': page_response['http_status'],
                    'response_time_ms': page_response['response_time_ms'],
                    'content_length': parsed_data['content_length'],
                    'link_count': parsed_data['link_count'],
                    'image_count': parsed_data['image_count']
                }

                # Store to Neo4j
                self.store_to_neo4j(page_data, parsed_data['links'])

                # Update statistics
                stats['pages_crawled'] += 1
                stats['total_links_found'] += len(parsed_data['links'])
                stats['external_links_found'] += sum(
                    1 for link in parsed_data['links'] if link['is_external']
                )

                # Add internal links to queue
                internal_links = [
                    link['url'] for link in parsed_data['links']
                    if not link['is_external']
                ]
                self.update_queue(internal_links, current_depth)

                # Progress update
                if stats['pages_crawled'] % 10 == 0:
                    elapsed = time.time() - stats['start_time']
                    rate = stats['pages_crawled'] / elapsed if elapsed > 0 else 0
                    print(f"\nProgress: {stats['pages_crawled']} pages crawled ({rate:.2f} pages/sec)")
                    print(f"Queue size: {len(self.url_queue)}")

                # Small delay to be respectful
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n\nCrawl interrupted by user")

        except Exception as e:
            print(f"\n\nCrawl error: {str(e)}")

        finally:
            # Clean up
            if self.selenium_driver:
                self.selenium_driver.quit()
                print("Selenium driver closed")

            # Final statistics
            elapsed = time.time() - stats['start_time']
            stats['elapsed_time'] = elapsed
            stats['pages_per_second'] = stats['pages_crawled'] / elapsed if elapsed > 0 else 0

            print("\n" + "="*50)
            print("CRAWL COMPLETE")
            print("="*50)
            print(f"Pages crawled: {stats['pages_crawled']}")
            print(f"Pages failed: {stats['pages_failed']}")
            print(f"Total links found: {stats['total_links_found']}")
            print(f"External links found: {stats['external_links_found']}")
            print(f"Time elapsed: {elapsed:.2f} seconds")
            print(f"Rate: {stats['pages_per_second']:.2f} pages/second")

            return stats