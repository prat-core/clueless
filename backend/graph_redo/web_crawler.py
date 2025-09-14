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
    def __init__(self, neo4j_uri, neo4j_auth, openai_api_key, base_url):
        """
        Initialize the WebCrawler with necessary configurations.

        Args:
            neo4j_uri (str): Neo4j database URI
            neo4j_auth (tuple): Neo4j authentication (username, password)
            openai_api_key (str): OpenAI API key for embeddings
            base_url (str): Starting URL to crawl
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

    def _get_selenium_driver(self):
        """Initialize and return Selenium Firefox driver with profile."""
        if self.selenium_driver is None:
            options = Options()

            # Use specific Firefox profile to preserve cookies and sessions
            profile_path = os.path.expanduser("~/.mozilla/firefox")
            specific_profile = os.path.join(profile_path, "708iiqgx.Prat")

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