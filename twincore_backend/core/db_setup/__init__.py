import logging
import asyncio

from .qdrant_setup import setup_qdrant_collection
from .neo4j_setup import setup_neo4j_constraints

logger = logging.getLogger(__name__)

async def initialize_databases():
    """
    Initializes all database setups (collections, constraints, etc.).
    """
    logger.info("Starting database initialization...")
    # Run setups concurrently
    await asyncio.gather(
        setup_qdrant_collection(),
        setup_neo4j_constraints()
    )
    logger.info("Database initialization finished.")

# Example of how this might be called at startup (e.g., in main.py's lifespan event)
# if __name__ == "__main__":
#     asyncio.run(initialize_databases()) 