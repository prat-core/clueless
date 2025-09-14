#!/usr/bin/env python3
"""
Main entry point for the AI-Powered Website Scraper & Knowledge Graph Builder.
This script orchestrates the web crawling process and builds a knowledge graph in Neo4j.
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

from web_crawler import WebCrawler
from neo4j_manager import Neo4jManager, ContentProcessor


def setup_logging(log_level='INFO'):
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('crawler.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def validate_url(url):
    """Validate that the provided URL is properly formatted."""
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
        if result.scheme not in ['http', 'https']:
            raise ValueError("URL must use http or https protocol")
        return url
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Invalid URL: {str(e)}")


def load_configuration():
    """Load configuration from environment variables."""
    load_dotenv()

    config = {
        'neo4j_uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        'neo4j_user': os.getenv('NEO4J_USER', 'neo4j'),
        'neo4j_password': os.getenv('NEO4J_PASSWORD'),
        'openai_api_key': os.getenv('OPENAI_API_KEY')
    }

    # Validate required configuration
    if not config['neo4j_password']:
        raise ValueError("NEO4J_PASSWORD environment variable is required")
    if not config['openai_api_key']:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    return config


def test_neo4j_connection(uri, auth):
    """Test the Neo4j database connection."""
    try:
        manager = Neo4jManager(uri, auth)
        # Test with a simple query
        result = manager.execute_query("RETURN 1 as test")
        if result and result[0]['test'] == 1:
            logging.info("Successfully connected to Neo4j database")
            manager.close()
            return True
    except Exception as e:
        logging.error(f"Failed to connect to Neo4j: {str(e)}")
        return False


def test_openai_connection(api_key):
    """Test the OpenAI API connection."""
    try:
        processor = ContentProcessor(api_key)
        logging.info("Successfully connected to OpenAI API")
        return True
    except Exception as e:
        logging.error(f"Failed to connect to OpenAI API: {str(e)}")
        return False


def crawl_website(url, config, max_pages=1000, max_depth=10, blacklist=None):
    """
    Main function to crawl a website and build knowledge graph.

    Args:
        url (str): Starting URL to crawl
        config (dict): Configuration dictionary
        max_pages (int): Maximum number of pages to crawl
        max_depth (int): Maximum depth to crawl
        blacklist (list): List of URL patterns or paths to exclude from crawling

    Returns:
        dict: Crawl statistics
    """
    # Initialize the crawler
    crawler = WebCrawler(
        neo4j_uri=config['neo4j_uri'],
        neo4j_auth=(config['neo4j_user'], config['neo4j_password']),
        openai_api_key=config['openai_api_key'],
        base_url=url,
        blacklist=blacklist or []
    )

    # Start crawling
    logging.info(f"Starting crawl of {url}")
    stats = crawler.crawl(max_pages=max_pages, max_depth=max_depth)

    return stats


def query_graph(config, query_type='stats'):
    """
    Query the Neo4j graph for information.

    Args:
        config (dict): Configuration dictionary
        query_type (str): Type of query to run

    Returns:
        dict: Query results
    """
    manager = Neo4jManager(
        uri=config['neo4j_uri'],
        auth=(config['neo4j_user'], config['neo4j_password'])
    )

    try:
        if query_type == 'stats':
            # Get graph statistics
            queries = {
                'total_pages': "MATCH (p:Page) RETURN count(p) as count",
                'total_links': "MATCH ()-[r:LINKS_TO]->() RETURN count(r) as count",
                'external_links': "MATCH (e:ExternalLink) RETURN count(e) as count",
                'domains': "MATCH (p:Page) RETURN DISTINCT p.domain as domain"
            }

            results = {}
            for name, query in queries.items():
                result = manager.execute_query(query)
                if name == 'domains':
                    results[name] = [r['domain'] for r in result if r.get('domain')]
                else:
                    results[name] = result[0]['count'] if result else 0

            return results

        elif query_type == 'recent':
            # Get recently crawled pages
            query = """
            MATCH (p:Page)
            RETURN p.url as url, p.title as title, p.last_crawled as last_crawled
            ORDER BY p.last_crawled DESC
            LIMIT 10
            """
            return manager.execute_query(query)

    finally:
        manager.close()


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description='AI-Powered Website Scraper & Knowledge Graph Builder'
    )

    # Add command-line arguments
    parser.add_argument(
        'url',
        type=validate_url,
        help='Starting URL to crawl'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=100,
        help='Maximum number of pages to crawl (default: 100)'
    )
    parser.add_argument(
        '--max-depth',
        type=int,
        default=3,
        help='Maximum depth to crawl (default: 3)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Only test connections without crawling'
    )
    parser.add_argument(
        '--query-stats',
        action='store_true',
        help='Query and display graph statistics'
    )
    parser.add_argument(
        '--blacklist',
        nargs='*',
        default=[],
        help='URL patterns or paths to exclude from crawling (e.g., /admin /private /blacklist)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    try:
        # Load configuration
        logging.info("Loading configuration...")
        config = load_configuration()

        # Test connections
        logging.info("Testing connections...")
        neo4j_ok = test_neo4j_connection(
            config['neo4j_uri'],
            (config['neo4j_user'], config['neo4j_password'])
        )
        openai_ok = test_openai_connection(config['openai_api_key'])

        if not neo4j_ok or not openai_ok:
            logging.error("Connection tests failed. Please check your configuration.")
            sys.exit(1)

        if args.test_only:
            logging.info("Connection tests passed. Exiting (--test-only flag set)")
            sys.exit(0)

        if args.query_stats:
            # Query and display statistics
            logging.info("Querying graph statistics...")
            stats = query_graph(config, 'stats')
            print("\n" + "="*50)
            print("GRAPH STATISTICS")
            print("="*50)
            print(f"Total pages: {stats['total_pages']}")
            print(f"Total internal links: {stats['total_links']}")
            print(f"Total external links: {stats['external_links']}")
            print(f"Domains: {', '.join(stats['domains'][:5])}")
            if len(stats['domains']) > 5:
                print(f"         ... and {len(stats['domains']) - 5} more")
            print("="*50 + "\n")

            # Also show recent pages
            recent = query_graph(config, 'recent')
            if recent:
                print("Recently crawled pages:")
                for page in recent[:5]:
                    print(f"  - {page['title'][:50] if page.get('title') else 'No title'}: {page['url'][:60]}")
        else:
            # Start crawling
            logging.info(f"Starting crawl of {args.url}")
            if args.blacklist:
                logging.info(f"Blacklisted patterns: {args.blacklist}")
            stats = crawl_website(
                args.url,
                config,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                blacklist=args.blacklist
            )

            # Display final statistics
            print("\n" + "="*50)
            print("CRAWL SUMMARY")
            print("="*50)
            print(f"Starting URL: {args.url}")
            print(f"Pages crawled: {stats['pages_crawled']}")
            print(f"Pages failed: {stats['pages_failed']}")
            print(f"Total links found: {stats['total_links_found']}")
            print(f"External links: {stats['external_links_found']}")
            print(f"Time elapsed: {stats['elapsed_time']:.2f} seconds")
            print(f"Crawl rate: {stats['pages_per_second']:.2f} pages/second")
            print("="*50 + "\n")

            # Query and show graph stats after crawl
            logging.info("Querying final graph statistics...")
            graph_stats = query_graph(config, 'stats')
            print("Graph now contains:")
            print(f"  - {graph_stats['total_pages']} pages")
            print(f"  - {graph_stats['total_links']} internal links")
            print(f"  - {graph_stats['external_links']} external links")

    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()