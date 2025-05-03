import logging
from typing import Union
from neo4j import Driver, AsyncDriver

from core.db_clients import get_neo4j_driver
from core.config import settings

logger = logging.getLogger(__name__)


async def setup_neo4j_constraints(driver: Union[Driver, AsyncDriver] = None, database: str = None):
    """
    Sets up the necessary uniqueness constraints in Neo4j.
    
    Args:
        driver (Driver or AsyncDriver, optional): Neo4j driver instance. If None, a new driver will be created.
        database (str, optional): Database name to use. If None, uses the value from settings.
        
    Note: This function handles both synchronous and asynchronous Neo4j driver instances.
    """
    # Use provided driver or get a new one
    use_driver = driver or await get_neo4j_driver()
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
        "CREATE CONSTRAINT organization_unique_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.org_id IS UNIQUE",
        "CREATE CONSTRAINT team_unique_id IF NOT EXISTS FOR (t:Team) REQUIRE t.team_id IS UNIQUE",
        "CREATE CONSTRAINT project_unique_id IF NOT EXISTS FOR (p:Project) REQUIRE p.project_id IS UNIQUE",
        "CREATE CONSTRAINT preference_unique_id IF NOT EXISTS FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE",
        "CREATE CONSTRAINT vote_unique_id IF NOT EXISTS FOR (v:Vote) REQUIRE v.vote_id IS UNIQUE",
    ]

    try:
        logger.info("Setting up Neo4j constraints...")
        
        # Check if we have an async or sync driver and handle accordingly
        if isinstance(use_driver, AsyncDriver):
            # Async driver handling
            async with use_driver.session(database=use_database) as session:
                for i, constraint_query in enumerate(constraints):
                    try:
                        await session.run(constraint_query)
                        logger.info(f"Successfully applied constraint {i+1}/{len(constraints)}.")
                    except Exception as constraint_error:
                        logger.error(f"Failed to apply constraint: {constraint_query} - Error: {constraint_error}", exc_info=True)
        else:
            # Sync driver handling (for tests)
            with use_driver.session(database=use_database) as session:
                for i, constraint_query in enumerate(constraints):
                    try:
                        session.run(constraint_query)
                        logger.info(f"Successfully applied constraint {i+1}/{len(constraints)}.")
                    except Exception as constraint_error:
                        logger.error(f"Failed to apply constraint: {constraint_query} - Error: {constraint_error}", exc_info=True)

        logger.info("Finished setting up Neo4j constraints.")

    except Exception as e:
        logger.error(f"Failed during Neo4j constraint setup: {e}", exc_info=True)
        raise
    finally:
        # Only close the driver if we created a new one
        if driver is None and use_driver is not None:
            # Different closing methods for sync vs async
            if isinstance(use_driver, AsyncDriver):
                await use_driver.close()
            else:
                use_driver.close() 