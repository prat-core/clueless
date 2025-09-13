#!/usr/bin/env python3
"""
Script to clear all data from the Neo4j database.
Use with caution - this will delete ALL nodes and relationships!
"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import logging
import sys

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_database(uri: str, auth: tuple, confirm: bool = True):
    """
    Clear all nodes and relationships from the Neo4j database.

    Args:
        uri: Neo4j connection URI
        auth: Tuple of (username, password)
        confirm: Whether to ask for confirmation before clearing
    """
    if confirm:
        print("\n" + "="*60)
        print("WARNING: This will DELETE ALL DATA from the Neo4j database!")
        print("="*60)
        print(f"Database URI: {uri}")
        print("="*60)

        response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
        if response != "YES":
            print("Operation cancelled.")
            return

    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(uri, auth=auth)

        with driver.session() as session:
            # First, get counts of existing data
            result = session.run("""
                MATCH (n)
                WITH count(n) as nodeCount
                MATCH ()-[r]->()
                WITH nodeCount, count(r) as relCount
                RETURN nodeCount, relCount
            """)

            record = result.single()
            if record:
                node_count = record["nodeCount"]
                rel_count = record["relCount"]
                logger.info(f"Found {node_count} nodes and {rel_count} relationships to delete")
            else:
                # If no relationships exist, just count nodes
                result = session.run("MATCH (n) RETURN count(n) as nodeCount")
                record = result.single()
                node_count = record["nodeCount"] if record else 0
                rel_count = 0
                logger.info(f"Found {node_count} nodes to delete")

            if node_count == 0 and rel_count == 0:
                logger.info("Database is already empty")
                return

            # Delete all relationships first
            if rel_count > 0:
                logger.info("Deleting all relationships...")
                session.run("MATCH ()-[r]->() DELETE r")
                logger.info(f"Deleted {rel_count} relationships")

            # Then delete all nodes
            if node_count > 0:
                logger.info("Deleting all nodes...")
                # Delete in batches to avoid memory issues with large databases
                batch_size = 10000
                deleted_count = 0

                while True:
                    result = session.run(f"""
                        MATCH (n)
                        WITH n LIMIT {batch_size}
                        DELETE n
                        RETURN count(n) as deleted
                    """)

                    record = result.single()
                    batch_deleted = record["deleted"] if record else 0

                    if batch_deleted == 0:
                        break

                    deleted_count += batch_deleted
                    logger.info(f"Deleted {deleted_count}/{node_count} nodes...")

                logger.info(f"Deleted {deleted_count} nodes")

            # Verify database is empty
            result = session.run("MATCH (n) RETURN count(n) as count")
            record = result.single()
            final_count = record["count"] if record else 0

            if final_count == 0:
                logger.info("✓ Database successfully cleared!")
            else:
                logger.warning(f"Database still contains {final_count} nodes")

        driver.close()

    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        sys.exit(1)


def main():
    """Main function to clear the Neo4j database."""

    # Get Neo4j connection details from environment or use defaults
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    if not neo4j_password or neo4j_password == "password":
        logger.warning("Using default password. Consider setting NEO4J_PASSWORD in .env file")

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Clear all data from Neo4j database")
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)"
    )
    parser.add_argument(
        "--uri",
        default=neo4j_uri,
        help=f"Neo4j URI (default: {neo4j_uri})"
    )
    parser.add_argument(
        "--user",
        default=neo4j_user,
        help=f"Neo4j username (default: {neo4j_user})"
    )
    parser.add_argument(
        "--password",
        default=neo4j_password,
        help="Neo4j password"
    )

    args = parser.parse_args()

    # Clear the database
    clear_database(
        uri=args.uri,
        auth=(args.user, args.password),
        confirm=not args.no_confirm
    )


if __name__ == "__main__":
    main()