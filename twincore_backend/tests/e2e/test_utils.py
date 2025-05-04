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
    Create a fresh Neo4j driver for test database.
    
    Returns:
        AsyncDriver: A new Neo4j driver instance
    """
    logger.info(f"Creating new test Neo4j driver at {settings.neo4j_test_uri}")
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_test_uri,
        auth=(settings.neo4j_test_user, settings.neo4j_test_password),
    )
    # Verify connection
    async with driver.session() as session:
        await session.run("RETURN 1")
    logger.info("Test Neo4j driver created")
    return driver


def get_test_qdrant_client() -> QdrantClient:
    """
    Create a new Qdrant client for test database.
    
    Returns:
        QdrantClient: A new Qdrant client
    """
    logger.info(f"Creating new test Qdrant client at {settings.qdrant_test_host}:{settings.qdrant_test_port}")
    client = QdrantClient(
        url=settings.qdrant_test_host,
        port=settings.qdrant_test_port,
        api_key=settings.qdrant_test_api_key,
        prefer_grpc=False,
        https=False,
        timeout=10.0,
    )
    logger.info("Test Qdrant client created")
    return client


async def get_test_async_qdrant_client() -> AsyncQdrantClient:
    """
    Create a new async Qdrant client for test database.
    
    Returns:
        AsyncQdrantClient: A new async Qdrant client
    """
    logger.info(f"Creating new async test Qdrant client at {settings.qdrant_test_host}:{settings.qdrant_test_port}")
    client = AsyncQdrantClient(
        host=settings.qdrant_test_host,
        port=settings.qdrant_test_port,
        api_key=settings.qdrant_test_api_key,
        prefer_grpc=False,
        https=False,
        timeout=10.0,
    )
    logger.info("New async test Qdrant client created")
    return client


async def setup_test_databases():
    """
    Set up test databases with necessary collections and constraints.
    """
    # Initialize Neo4j constraints for test database
    logger.info("Creating fresh Neo4j driver for setup")
    driver = await get_test_neo4j_driver()
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
        async with driver.session() as session:
            for i, constraint_query in enumerate(constraints):
                try:
                    await session.run(constraint_query)
                    logger.info(f"Applied constraint {i+1}/{len(constraints)}.")
                except Exception as constraint_error:
                    logger.error(f"Failed to apply constraint: {constraint_query} - Error: {constraint_error}")
    finally:
        logger.info("Closing Neo4j driver after setup")
        await driver.close()
    
    # Initialize Qdrant collection for test database
    qdrant_client = get_test_qdrant_client()
    collection_name = settings.qdrant_collection_name
    vector_size = settings.embedding_dimension
    
    try:
        logger.info(f"Setting up Qdrant collection '{collection_name}'...")
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
        logger.error(f"Failed to set up test Qdrant collection: {e}")
        raise


async def clear_test_databases():
    """
    Clear all data from test databases.
    """
    # Clear Neo4j test database
    logger.info("Creating fresh Neo4j driver for database clearing")
    driver = await get_test_neo4j_driver()
    try:
        logger.info("Clearing Neo4j test database...")
        async with driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("Neo4j test database cleared")
    finally:
        logger.info("Closing Neo4j driver after clearing")
        await driver.close()
    
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
            logger.info(f"Qdrant test collection '{collection_name}' doesn't exist")
    except Exception as e:
        logger.error(f"Failed to clear Qdrant test collection: {e}") 