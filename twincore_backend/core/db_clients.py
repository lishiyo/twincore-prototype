"""
Database client initialization for Qdrant and Neo4j.

This module provides functions to create and get client instances
for Qdrant (vector database) and Neo4j (graph database).
"""

from functools import lru_cache
import logging
from typing import Optional

from neo4j import GraphDatabase, Driver
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """
    Initialize and return a Qdrant client.
    Uses LRU cache to prevent multiple client instances.
    
    Returns:
        QdrantClient: A configured Qdrant client instance
    """
    try:
        logger.info(f"Initializing Qdrant client at {settings.qdrant_host}:{settings.qdrant_port}")
        client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            prefer_grpc=settings.qdrant_prefer_grpc,
            grpc_port=settings.qdrant_grpc_port,
            https=False,  # Explicitly use HTTP instead of HTTPS for local development
        )
        # Simple health check
        client.get_collections()
        logger.info("Qdrant client initialized successfully")
        return client
    except UnexpectedResponse as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing Qdrant client: {e}")
        raise


@lru_cache
def get_async_qdrant_client() -> AsyncQdrantClient:
    """
    Initialize and return an asynchronous Qdrant client.
    Uses LRU cache to prevent multiple client instances.
    
    Returns:
        AsyncQdrantClient: A configured async Qdrant client instance
    """
    try:
        logger.info(f"Initializing async Qdrant client at {settings.qdrant_host}:{settings.qdrant_port}")
        client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            prefer_grpc=settings.qdrant_prefer_grpc,
            grpc_port=settings.qdrant_grpc_port,
            https=False,  # Explicitly use HTTP instead of HTTPS for local development
        )
        # Note: We don't do a health check here since it would require an await
        # Health check is performed at first use
        logger.info("Async Qdrant client initialized")
        return client
    except Exception as e:
        logger.error(f"Unexpected error initializing async Qdrant client: {e}")
        raise


@lru_cache
def get_neo4j_driver() -> Driver:
    """
    Initialize and return a Neo4j driver.
    Uses LRU cache to prevent multiple driver instances.
    
    Returns:
        Driver: A configured Neo4j driver instance
    """
    try:
        logger.info(f"Initializing Neo4j driver at {settings.neo4j_uri}")
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        # Verify connection
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info("Neo4j driver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j database: {e}")
        raise


# Convenience function to get both clients
@lru_cache
def get_database_clients():
    """
    Get both Qdrant client and Neo4j driver.
    
    Returns:
        tuple: (QdrantClient, Neo4j Driver)
    """
    return get_qdrant_client(), get_neo4j_driver()


# Helper function to clear caches for testing
def clear_all_client_caches():
    """Clear all client LRU caches."""
    get_qdrant_client.cache_clear()
    get_async_qdrant_client.cache_clear()
    get_neo4j_driver.cache_clear()
    get_database_clients.cache_clear()

# Helper functions for testing removed, as they are replaced by fixture in conftest.py 