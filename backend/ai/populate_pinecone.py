#!/usr/bin/env python3
"""
Standalone script to populate Pinecone vector database with web content.
This script crawls websites and directly populates Pinecone without requiring Neo4j.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time

from dotenv import load_dotenv
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

import httpx
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from collections import deque

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'pinecone_populate_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimplePineconePopulator:
    """
    Simple web crawler that populates Pinecone vector database directly.
    """
    
    def __init__(self, openai_api_key: str, pinecone_api_key: str, 
                 index_name: str, base_url: str):
        """
        Initialize the populator.
        
        Args:
            openai_api_key: OpenAI API key
            pinecone_api_key: Pinecone API key  
            index_name: Pinecone index name
            base_url: Starting URL for crawling
        """
        self.base_url = self._normalize_url(base_url)
        self.base_domain = urlparse(self.base_url).netloc
        
        # Initialize LangChain components
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key
        )
        
        # Initialize Pinecone vector store
        self.vectorstore = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=self.embeddings
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # HTTP client for web requests
        self.client = httpx.Client(
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-WebCrawler/1.0; Educational)"},
            timeout=30.0,
            follow_redirects=True
        )
        
        # Crawling state
        self.url_queue = deque([self.base_url])
        self.visited_urls = set()
        self.failed_urls = {}
        
        logger.info(f"SimplePineconePopulator initialized for {self.base_url}")
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
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
        """Check if URL should be crawled (same domain, valid format)."""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Check domain
            if parsed.netloc != self.base_domain:
                return False
            
            # Avoid non-HTML resources
            excluded_extensions = (
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
                '.pdf', '.zip', '.tar', '.gz', '.rar',
                '.mp3', '.mp4', '.avi', '.mov', '.wmv',
                '.css', '.js', '.json', '.xml'
            )
            
            if any(parsed.path.lower().endswith(ext) for ext in excluded_extensions):
                return False
            
            return True
            
        except Exception:
            return False
    
    def fetch_page(self, url: str) -> Optional[Dict]:
        """Fetch a web page and return its content."""
        try:
            logger.info(f"Fetching: {url}")
            
            response = self.client.get(url)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.info(f"Skipping non-HTML content: {content_type}")
                return None
            
            return {
                'url': self._normalize_url(str(response.url)),
                'html_content': response.text,
                'status_code': response.status_code,
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            self.failed_urls[url] = str(e)
            return None
    
    def extract_content(self, html_content: str) -> Dict:
        """Extract text content and metadata from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
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
        
        # Extract all text content
        text_content = soup.get_text(separator=' ', strip=True)
        text_content = ' '.join(text_content.split())  # Clean whitespace
        
        return {
            'title': title[:500],
            'meta_description': meta_description[:1000], 
            'text_content': text_content[:50000]  # Limit for processing
        }
    
    def extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract internal links from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        for anchor in soup.find_all('a', href=True):
            href = anchor['href'].strip()
            
            # Skip fragments, javascript, mailto
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            # Resolve to absolute URL
            absolute_url = urljoin(base_url, href)
            normalized_url = self._normalize_url(absolute_url)
            
            # Only include valid internal URLs
            if self.is_valid_url(normalized_url):
                links.append(normalized_url)
        
        return list(set(links))  # Remove duplicates
    
    def add_to_pinecone(self, url: str, content_data: Dict) -> bool:
        """Add page content to Pinecone vector store."""
        try:
            # Combine title, description, and content for embedding
            full_text = f"{content_data.get('title', '')} {content_data.get('meta_description', '')} {content_data.get('text_content', '')}"
            
            if not full_text.strip():
                logger.warning(f"No content to add for {url}")
                return False
            
            # Create document with metadata
            metadata = {
                'url': url,
                'title': content_data.get('title', ''),
                'domain': urlparse(url).netloc,
                'meta_description': content_data.get('meta_description', ''),
                'crawled_at': datetime.now().isoformat(),
                'content_length': len(full_text)
            }
            
            # Split into chunks
            chunks = self.text_splitter.create_documents([full_text])
            
            # Add metadata to each chunk
            for i, chunk in enumerate(chunks):
                chunk.metadata.update(metadata)
                chunk.metadata['chunk_id'] = f"{url}#chunk_{i}"
            
            # Add to Pinecone
            self.vectorstore.add_documents(chunks)
            
            logger.info(f"✅ Added to Pinecone: {url} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add to Pinecone {url}: {e}")
            return False
    
    def crawl_and_populate(self, max_pages: int = 50, max_depth: int = 2) -> Dict:
        """
        Crawl website and populate Pinecone.
        
        Args:
            max_pages: Maximum pages to crawl
            max_depth: Maximum depth from starting URL
            
        Returns:
            Dictionary with crawl statistics
        """
        start_time = time.time()
        pages_crawled = 0
        pages_added_to_pinecone = 0
        
        # Track depth
        url_depths = {self.base_url: 0}
        
        logger.info(f"Starting crawl from {self.base_url}")
        logger.info(f"Max pages: {max_pages}, Max depth: {max_depth}")
        
        while self.url_queue and pages_crawled < max_pages:
            current_url = self.url_queue.popleft()
            
            # Check depth limit
            current_depth = url_depths.get(current_url, 0)
            if current_depth > max_depth:
                continue
            
            # Skip if already visited
            if current_url in self.visited_urls:
                continue
            
            self.visited_urls.add(current_url)
            
            # Fetch page
            page_data = self.fetch_page(current_url)
            if not page_data:
                continue
            
            # Extract content
            content_data = self.extract_content(page_data['html_content'])
            
            # Add to Pinecone
            if self.add_to_pinecone(current_url, content_data):
                pages_added_to_pinecone += 1
            
            # Extract new links for crawling
            new_links = self.extract_links(page_data['html_content'], current_url)
            
            # Add new URLs to queue
            for link in new_links:
                if link not in self.visited_urls and link not in self.url_queue:
                    self.url_queue.append(link)
                    url_depths[link] = current_depth + 1
            
            pages_crawled += 1
            logger.info(f"Progress: {pages_crawled}/{max_pages} pages crawled, {pages_added_to_pinecone} added to Pinecone, {len(self.url_queue)} in queue")
            
            # Be respectful with delay
            time.sleep(1.5)
        
        # Calculate statistics
        elapsed_time = time.time() - start_time
        stats = {
            'pages_crawled': pages_crawled,
            'pages_added_to_pinecone': pages_added_to_pinecone,
            'pages_failed': len(self.failed_urls),
            'unique_urls_found': len(self.visited_urls),
            'elapsed_time_seconds': elapsed_time,
            'pages_per_second': pages_crawled / elapsed_time if elapsed_time > 0 else 0
        }
        
        logger.info(f"Crawl completed: {stats}")
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()


def main():
    """Main function to run the Pinecone population script."""
    logger.info("="*60)
    logger.info("Pinecone Vector Database Population Script")
    logger.info("="*60)
    
    # Get configuration from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    pinecone_api_key = os.getenv("PINECONE_API_KEY") 
    pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "clueless-rag")
    
    # Target website
    target_url = "https://www.cvs.com"
    
    # Validate API keys
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return
    
    if not pinecone_api_key:
        logger.error("PINECONE_API_KEY not found in environment variables") 
        return
    
    logger.info(f"Target URL: {target_url}")
    logger.info(f"Pinecone Index: {pinecone_index_name}")
    logger.info(f"OpenAI Key: {openai_api_key[:10]}...")
    logger.info(f"Pinecone Key: {pinecone_api_key[:10]}...")
    logger.info("="*60)
    
    try:
        print(f"\nThis will crawl {target_url} and populate Pinecone vector database.")
        print("This does NOT require Neo4j to be running.")
        response = input("\nProceed with crawling? (y/n): ")
        
        if response.lower() != 'y':
            logger.info("Crawl cancelled by user")
            return
        
        # Initialize the populator
        logger.info("Initializing Pinecone populator...")
        
        with SimplePineconePopulator(
            openai_api_key=openai_api_key,
            pinecone_api_key=pinecone_api_key,
            index_name=pinecone_index_name,
            base_url=target_url
        ) as populator:
            
            logger.info("Starting crawl and Pinecone population...")
            start_time = datetime.now()
            
            # Crawl and populate (smaller limits for testing)
            stats = populator.crawl_and_populate(
                max_pages=20,  # Start small for testing
                max_depth=2    # Shallow crawl for testing
            )
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("\n" + "="*60)
            logger.info("CRAWL COMPLETED SUCCESSFULLY!")
            logger.info("="*60)
            logger.info(f"Pages crawled: {stats['pages_crawled']}")
            logger.info(f"Pages added to Pinecone: {stats['pages_added_to_pinecone']}")
            logger.info(f"Pages failed: {stats['pages_failed']}")
            logger.info(f"Total time: {duration}")
            logger.info(f"Average time per page: {stats['elapsed_time_seconds'] / stats['pages_crawled']:.2f}s")
            logger.info("="*60)
            
            # Test the populated vector store
            logger.info("\nTesting Pinecone search...")
            test_results = populator.vectorstore.similarity_search("pharmacy", k=3)
            logger.info(f"Found {len(test_results)} results for 'pharmacy' search")
            
            for i, result in enumerate(test_results):
                logger.info(f"Result {i+1}: {result.metadata.get('title', 'No title')}")
                logger.info(f"  URL: {result.metadata.get('url', 'No URL')}")
                logger.info(f"  Content preview: {result.page_content[:100]}...")
            
    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user")
        
    except Exception as e:
        logger.error(f"Error during crawl: {e}", exc_info=True)


if __name__ == "__main__":
    main()
