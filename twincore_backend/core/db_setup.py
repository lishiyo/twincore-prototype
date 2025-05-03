import logging
from qdrant_client import models, AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from neo4j import Driver

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


async def setup_neo4j_constraints(driver: Driver = None, database: str = None):
    """
    Sets up the necessary uniqueness constraints in Neo4j.
    
    Args:
        driver (Driver, optional): Neo4j driver instance. If None, a new driver will be created.
        database (str, optional): Database name to use. If None, uses the value from settings.
        
    Note: Neo4j Python driver does not support native async/await,
    so we use the synchronous API within our async function.
    """
    # Use provided driver or get a new one
    use_driver = driver or get_neo4j_driver()
    # Use provided database or get from settings
    use_database = database or settings.neo4j_database
    
    # Define constraints based on dataSchema.md
    # Using IF NOT EXISTS for idempotency
    constraints = [
        "CREATE CONSTRAINT user_unique_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
        "CREATE CONSTRAINT session_unique_id IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE",
        "CREATE CONSTRAINT message_unique_id IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE",
        "CREATE CONSTRAINT chunk_unique_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
        "CREATE CONSTRAINT document_unique_id IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
        "CREATE CONSTRAINT topic_unique_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
        # Add missing constraints for all node types in dataSchema.md
        "CREATE CONSTRAINT organization_unique_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.org_id IS UNIQUE",
        "CREATE CONSTRAINT team_unique_id IF NOT EXISTS FOR (t:Team) REQUIRE t.team_id IS UNIQUE",
        "CREATE CONSTRAINT project_unique_id IF NOT EXISTS FOR (p:Project) REQUIRE p.project_id IS UNIQUE",
        "CREATE CONSTRAINT preference_unique_id IF NOT EXISTS FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE",
        "CREATE CONSTRAINT vote_unique_id IF NOT EXISTS FOR (v:Vote) REQUIRE v.vote_id IS UNIQUE",
    ]

    try:
        logger.info("Setting up Neo4j constraints...")
        # Use standard session instead of async session
        with use_driver.session(database=use_database) as session:
            for i, constraint_query in enumerate(constraints):
                try:
                    # Use standard write_transaction instead of execute_write
                    session.write_transaction(lambda tx: tx.run(constraint_query))
                    logger.info(f"Successfully applied constraint {i+1}/{len(constraints)}.")
                except Exception as constraint_error:
                    # Log specific constraint error but continue trying others
                    logger.error(f"Failed to apply constraint: {constraint_query} - Error: {constraint_error}", exc_info=True)
                    # Depending on policy, you might want to raise an error here to stop the process

        logger.info("Finished setting up Neo4j constraints.")

    except Exception as e:
        logger.error(f"Failed during Neo4j constraint setup: {e}", exc_info=True)
        raise
    finally:
        # Only close the driver if we created a new one
        if driver is None and use_driver is not None:
            use_driver.close()

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