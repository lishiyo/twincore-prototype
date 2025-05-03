import logging
from qdrant_client import models, AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from core.config import settings

logger = logging.getLogger(__name__)

# Define Qdrant distance model (Collection name and vector size come from settings)
QDRANT_DISTANCE = models.Distance.COSINE


async def setup_qdrant_collection():
    """
    Ensures the Qdrant collection specified in settings exists and has the correct configuration.
    """
    qdrant_client = get_async_qdrant_client()
    collection_name = settings.qdrant_collection_name
    vector_size = settings.embedding_dimension

    try:
        logger.info(f"Checking if Qdrant collection '{collection_name}' exists...")
        try:
            # Check if collection exists
            await qdrant_client.get_collection(collection_name=collection_name)
            logger.info(f"Collection '{collection_name}' already exists.")
            # Optional: Verify existing collection parameters if necessary,
            # e.g., vector size and distance. For simplicity, we assume recreation
            # or manual intervention if parameters mismatch severely.

        except (UnexpectedResponse, ValueError) as e:
            # ValueError can be raised for 404 Not Found, UnexpectedResponse for others
             if isinstance(e, ValueError) or (isinstance(e, UnexpectedResponse) and e.status_code == 404):
                logger.info(f"Collection '{collection_name}' not found. Creating...")
                await qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size, distance=QDRANT_DISTANCE
                    ),
                    # Add other configurations like HNSW parameters if needed later
                )
                logger.info(f"Successfully created Qdrant collection '{collection_name}'.")
             else:
                 # Re-raise unexpected errors
                 raise e

    except Exception as e:
        logger.error(f"Failed to setup Qdrant collection '{collection_name}': {e}", exc_info=True)
        raise


async def setup_neo4j_constraints():
    """
    Sets up the necessary uniqueness constraints in Neo4j.
    """
    driver = get_neo4j_driver()
    # Define constraints based on dataSchema.md
    # Using IF NOT EXISTS for idempotency
    constraints = [
        "CREATE CONSTRAINT user_unique_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
        "CREATE CONSTRAINT session_unique_id IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE",
        "CREATE CONSTRAINT message_unique_id IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE",
        "CREATE CONSTRAINT chunk_unique_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
        "CREATE CONSTRAINT document_unique_id IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
        "CREATE CONSTRAINT topic_unique_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
        # Add any other constraints identified later
    ]

    try:
        logger.info("Setting up Neo4j constraints...")
        # Use managed transactions for constraint creation
        async with driver.session(database=settings.neo4j_database) as session:
            for i, constraint_query in enumerate(constraints):
                try:
                    # Using execute_write to ensure it runs within a transaction
                    await session.execute_write(lambda tx: tx.run(constraint_query))
                    logger.info(f"Successfully applied constraint {i+1}/{len(constraints)}.")
                except Exception as constraint_error:
                    # Log specific constraint error but continue trying others
                    logger.error(f"Failed to apply constraint: {constraint_query} - Error: {constraint_error}", exc_info=True)
                    # Depending on policy, you might want to raise an error here to stop the process

        logger.info("Finished setting up Neo4j constraints.")

    except Exception as e:
        logger.error(f"Failed during Neo4j constraint setup: {e}", exc_info=True)
        raise

async def initialize_databases():
    """
    Initializes all database setups (collections, constraints, etc.).
    """
    logger.info("Starting database initialization...")
    await setup_qdrant_collection()
    await setup_neo4j_constraints()
    logger.info("Database initialization finished.")

# Example of how this might be called at startup (e.g., in main.py)
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(initialize_databases()) 