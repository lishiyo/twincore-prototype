"""
Utilities for E2E testing with real test databases.
"""
import logging
from neo4j import AsyncGraphDatabase, AsyncDriver
from qdrant_client import AsyncQdrantClient, QdrantClient

from core.config import settings

logger = logging.getLogger(__name__)


async def get_test_neo4j_driver() -> AsyncDriver:
    """
    Initialize and return an asynchronous Neo4j driver for the test database.
    
    Returns:
        AsyncDriver: A configured async Neo4j driver instance for test database
    """
    try:
        logger.info(f"Initializing test async Neo4j driver at {settings.neo4j_test_uri}")
        # Use AsyncGraphDatabase to explicitly get an async driver
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_test_uri,
            auth=(settings.neo4j_test_user, settings.neo4j_test_password),
        )
        # Verify connection asynchronously
        async with driver.session() as session:
            await session.run("RETURN 1")
        logger.info("Test async Neo4j driver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to test Neo4j database: {e}")
        raise


def get_test_qdrant_client() -> QdrantClient:
    """
    Initialize and return a synchronous Qdrant client for the test database.
    
    Returns:
        QdrantClient: A configured Qdrant client instance for test database
    """
    try:
        logger.info(f"Initializing test Qdrant client at {settings.qdrant_test_host}:{settings.qdrant_test_port}")
        client = QdrantClient(
            url=settings.qdrant_test_host,
            port=settings.qdrant_test_port,
            api_key=settings.qdrant_test_api_key,
            prefer_grpc=False,  # Use HTTP for simplicity in tests
            https=False,  # Disable HTTPS for tests to avoid SSL errors
            timeout=10.0,  # Increase timeout for test stability
        )
        logger.info("Test Qdrant client initialized")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to test Qdrant: {e}")
        raise


async def get_test_async_qdrant_client() -> AsyncQdrantClient:
    """
    Initialize and return an asynchronous Qdrant client for the test database.
    
    Returns:
        AsyncQdrantClient: A configured async Qdrant client instance for test database
    """
    try:
        logger.info(f"Initializing async test Qdrant client at {settings.qdrant_test_host}:{settings.qdrant_test_port}")
        client = AsyncQdrantClient(
            host=settings.qdrant_test_host,
            port=settings.qdrant_test_port,
            api_key=settings.qdrant_test_api_key,
            prefer_grpc=False,  # Use HTTP for simplicity in tests
            https=False,  # Disable HTTPS for tests to avoid SSL errors
            timeout=10.0,  # Increase timeout for test stability
        )
        logger.info("Async test Qdrant client initialized")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to test Qdrant: {e}")
        raise


async def setup_test_databases():
    """
    Set up test databases with necessary collections and constraints.
    """
    # Initialize Neo4j constraints for test database
    neo4j_driver = await get_test_neo4j_driver()
    try:
        # Define constraints based on dataSchema.md with IF NOT EXISTS for idempotency
        constraints = [
            "CREATE CONSTRAINT user_unique_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            "CREATE CONSTRAINT session_unique_id IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE",
            "CREATE CONSTRAINT message_unique_id IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE",
            "CREATE CONSTRAINT chunk_unique_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
            "CREATE CONSTRAINT document_unique_id IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
            "CREATE CONSTRAINT topic_unique_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT organization_unique_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.org_id IS UNIQUE",
            "CREATE CONSTRAINT team_unique_id IF NOT EXISTS FOR (t:Team) REQUIRE t.team_id IS UNIQUE",
            "CREATE CONSTRAINT project_unique_id IF NOT EXISTS FOR (p:Project) REQUIRE p.project_id IS UNIQUE",
            "CREATE CONSTRAINT preference_unique_id IF NOT EXISTS FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE",
            "CREATE CONSTRAINT vote_unique_id IF NOT EXISTS FOR (v:Vote) REQUIRE v.vote_id IS UNIQUE",
        ]

        logger.info("Setting up Neo4j constraints for test database...")
        async with neo4j_driver.session() as session:
            for i, constraint_query in enumerate(constraints):
                try:
                    await session.run(constraint_query)
                    logger.info(f"Successfully applied constraint {i+1}/{len(constraints)}.")
                except Exception as constraint_error:
                    logger.error(f"Failed to apply constraint: {constraint_query} - Error: {constraint_error}", exc_info=True)
    finally:
        await neo4j_driver.close()
    
    # Initialize Qdrant collection for test database
    # Using synchronous client for simplicity
    qdrant_client = get_test_qdrant_client()
    collection_name = settings.qdrant_collection_name
    vector_size = settings.embedding_dimension
    
    try:
        logger.info(f"Setting up Qdrant collection '{collection_name}' for test database...")
        try:
            # Try to get collection to see if it exists
            qdrant_client.get_collection(collection_name=collection_name)
            logger.info(f"Test Qdrant collection '{collection_name}' already exists")
        except Exception:
            # Collection doesn't exist, create it
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": vector_size,
                    "distance": "Cosine"
                }
            )
            logger.info(f"Created test Qdrant collection '{collection_name}'")
    except Exception as e:
        logger.error(f"Failed to set up test Qdrant collection: {e}", exc_info=True)
        raise


async def clear_test_databases():
    """
    Clear all data from test databases.
    """
    # Clear Neo4j test database
    neo4j_driver = await get_test_neo4j_driver()
    try:
        logger.info("Clearing Neo4j test database...")
        async with neo4j_driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("Neo4j test database cleared")
    except Exception as e:
        logger.error(f"Failed to clear Neo4j test database: {e}", exc_info=True)
    finally:
        await neo4j_driver.close()
    
    # Clear Qdrant test database
    qdrant_client = get_test_qdrant_client()
    collection_name = settings.qdrant_collection_name
    
    try:
        logger.info(f"Clearing Qdrant test collection '{collection_name}'...")
        try:
            # Check if collection exists
            qdrant_client.get_collection(collection_name=collection_name)
            # Collection exists, delete all points
            qdrant_client.delete(
                collection_name=collection_name,
                points_selector=None  # Delete all points
            )
            logger.info(f"Qdrant test collection '{collection_name}' points cleared")
        except Exception:
            # Collection doesn't exist, nothing to clear
            logger.info(f"Qdrant test collection '{collection_name}' doesn't exist, nothing to clear")
    except Exception as e:
        logger.error(f"Failed to clear Qdrant test collection: {e}", exc_info=True) 