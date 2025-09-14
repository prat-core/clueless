#!/usr/bin/env python3
"""
Test script to crawl CVS website and build knowledge graph at depth 3.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Import our crawler components
from crawler import WebCrawler
from neo4j_manager import Neo4jManager
from content_processor import ContentProcessor


def test_cvs_crawler():
    """
    Test the web crawler on CVS website with depth 3.
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'cvs_crawl_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    # Get configuration from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    # CVS website URL
    cvs_url = "https://www.cvs.com"

    # Validate API key
    if not openai_api_key:
        logger.warning("No OpenAI API key found. Embeddings and summaries will be mocked.")
        logger.warning("Set OPENAI_API_KEY in .env file for full functionality.")

    logger.info("="*60)
    logger.info("CVS Website Crawler Test")
    logger.info("="*60)
    logger.info(f"Target URL: {cvs_url}")
    logger.info(f"Neo4j URI: {neo4j_uri}")
    logger.info(f"Max Depth: 3")
    logger.info(f"Max Pages: 100")
    logger.info("="*60)

    try:
        # Ask for confirmation before starting
        print("\nThis will crawl the CVS website and store data in Neo4j.")
        print("Make sure Neo4j is running and accessible.")
        response = input("\nProceed with crawling? (y/n): ")

        if response.lower() != 'y':
            logger.info("Crawl cancelled by user")
            return

        # Optional: Clear database before crawling
        print("\nDo you want to clear the existing database first?")
        response = input("Clear database? (y/n): ")

        if response.lower() == 'y':
            logger.info("Clearing existing database...")
            neo4j_manager = Neo4jManager(neo4j_uri, (neo4j_user, neo4j_password))

            # Clear all nodes and relationships
            with neo4j_manager.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")

            neo4j_manager.close()
            logger.info("Database cleared")

        # Initialize the crawler
        logger.info("Initializing web crawler...")

        with WebCrawler(
            neo4j_uri=neo4j_uri,
            neo4j_auth=(neo4j_user, neo4j_password),
            openai_api_key=openai_api_key,
            base_url=cvs_url,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            delay=1.5,  # Be respectful with delay between requests
            timeout=30.0,
            max_retries=3
        ) as crawler:

            logger.info("Starting crawl...")
            start_time = datetime.now()

            # Crawl with depth 3 and max 100 pages
            stats = crawler.crawl(
                max_pages=100,  # Limit pages to be respectful
                max_depth=3     # Depth 3 as requested
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Print crawl statistics
            logger.info("="*60)
            logger.info("Crawl Complete!")
            logger.info("="*60)
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Pages crawled: {stats['pages_crawled']}")
            logger.info(f"Pages failed: {stats['pages_failed']}")
            logger.info(f"Unique URLs found: {stats['unique_urls_found']}")
            logger.info(f"Pages per second: {stats['pages_per_second']:.2f}")

            if stats['failed_urls']:
                logger.info("\nFailed URLs:")
                for url, reason in stats['failed_urls'].items():
                    logger.info(f"  - {url}: {reason}")

            # Save statistics to file
            stats_file = f"cvs_crawl_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"\nStatistics saved to: {stats_file}")

            # Query the graph for some insights
            logger.info("\n" + "="*60)
            logger.info("Graph Analysis")
            logger.info("="*60)

            neo4j_manager = Neo4jManager(neo4j_uri, (neo4j_user, neo4j_password))

            # Count total nodes and relationships
            with neo4j_manager.driver.session() as session:
                # Total pages
                result = session.run("MATCH (p:Page) RETURN count(p) as count")
                page_count = result.single()["count"]
                logger.info(f"Total pages in graph: {page_count}")

                # Total relationships
                result = session.run("MATCH ()-[r:LINKS_TO]->() RETURN count(r) as count")
                link_count = result.single()["count"]
                logger.info(f"Total internal links: {link_count}")

                # External links
                result = session.run("MATCH (e:ExternalLink) RETURN count(e) as count")
                external_count = result.single()["count"]
                logger.info(f"Total external links: {external_count}")

                # Most linked pages
                result = session.run("""
                    MATCH (p:Page)<-[:LINKS_TO]-()
                    RETURN p.url as url, p.title as title, count(*) as inbound_links
                    ORDER BY inbound_links DESC
                    LIMIT 10
                """)

                logger.info("\nTop 10 most linked pages:")
                for record in result:
                    logger.info(f"  - {record['title'][:50] if record['title'] else 'No title'}: {record['inbound_links']} links")
                    logger.info(f"    URL: {record['url']}")

                # Pages by depth
                logger.info("\nPages by depth from homepage:")
                for depth in range(4):
                    result = session.run("""
                        MATCH path = shortestPath((home:Page {url: $home_url})-[:LINKS_TO*0..%d]->(p:Page))
                        WHERE length(path) = %d
                        RETURN count(DISTINCT p) as count
                    """ % (depth, depth), home_url=cvs_url)

                    record = result.single()
                    if record:
                        logger.info(f"  Depth {depth}: {record['count']} pages")

            neo4j_manager.close()

            logger.info("\n" + "="*60)
            logger.info("Test completed successfully!")
            logger.info("You can now explore the graph in Neo4j Browser")
            logger.info("Example Cypher queries:")
            logger.info("  - MATCH (n) RETURN n LIMIT 100")
            logger.info("  - MATCH (p:Page) WHERE p.url CONTAINS 'pharmacy' RETURN p")
            logger.info("  - MATCH path = (p1:Page)-[:LINKS_TO*1..2]->(p2:Page) RETURN path LIMIT 50")
            logger.info("="*60)

    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error during crawl: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    test_cvs_crawler()