"""Tests for Neo4j Data Access Layer implementation.

This module contains integration tests for the Neo4jDAL class, which requires
a running Neo4j database instance (test instance via Docker).
"""

import asyncio
import pytest
import uuid
from typing import Dict, Any, Optional
import logging # Import logging

import pytest_asyncio
from neo4j import AsyncDriver, Record, AsyncSession, AsyncGraphDatabase
from neo4j.exceptions import ClientError, ServiceUnavailable # Import ServiceUnavailable

from core.config import settings
from dal.neo4j_dal import Neo4jDAL

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def test_neo4j_driver():
    """Get a test Neo4j async driver connected to the test database."""
    driver: Optional[AsyncDriver] = None # Ensure driver is defined in outer scope
    try:
        logger.info(f"Attempting to connect to Neo4j test instance at {settings.neo4j_test_uri} (async)")
        # Use AsyncGraphDatabase to explicitly get an async driver
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_test_uri,
            auth=(settings.neo4j_test_user, settings.neo4j_test_password),
        )
        
        # Test connection asynchronously
        logger.info("Driver created, attempting connection test...")
        async with driver.session() as session:
            logger.info("Session opened, running test query...")
            result = await session.run("RETURN 1 as n")
            logger.info("Test query executed, fetching result...")
            value = await result.single()
            value = value["n"] if value else None
            logger.info(f"Successfully connected to async Neo4j test instance. Test query result: {value}")
            if value != 1:
                 raise ServiceUnavailable("Neo4j test query did not return expected value.")
        
        logger.info("Connection test successful, yielding driver.")
        yield driver # Yield the driver only if connection test succeeds
        
    except ServiceUnavailable as e:
        logger.error(f"Could not connect to Neo4j test instance: {e}")
        pytest.fail(f"Neo4j connection failed: {e}") # Fail fast if connection fails
    except Exception as e:
        logger.error(f"Error setting up async Neo4j test driver: {e}", exc_info=True)
        pytest.fail(f"Unexpected error during Neo4j driver setup: {e}")
        
    finally:
        if driver is not None:
            logger.info("Closing async Neo4j test driver.")
            await driver.close()
            logger.info("Async Neo4j test driver closed.")


@pytest_asyncio.fixture
async def test_neo4j_dal(test_neo4j_driver: AsyncDriver):
    """Create a Neo4jDAL instance for testing using the async driver."""
    # Driver is now required by the constructor
    dal = Neo4jDAL(driver=test_neo4j_driver)
    yield dal


@pytest_asyncio.fixture
async def clean_test_database(test_neo4j_driver: AsyncDriver):
    """Ensure the test database is clean before and after tests (async)."""
    # Clean up before the test
    async with test_neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    
    yield
    
    # Clean up after the test
    async with test_neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


@pytest.mark.asyncio
async def test_create_node_if_not_exists_creates_new_node(test_neo4j_dal: Neo4jDAL, clean_test_database):
    """Test creating a new node when it doesn't exist."""
    # Arrange
    user_id = str(uuid.uuid4())
    label = "User"
    properties = {
        "userId": user_id, # Using correct property name
        "name": "Test User",
        "email": "test@example.com"
    }
    constraints = {"userId": user_id}
    
    # Act
    result = await test_neo4j_dal.create_node_if_not_exists(
        label, properties, constraints
    )
    
    # Assert
    assert result is not None
    assert result["userId"] == user_id
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_create_node_if_not_exists_returns_existing_node(test_neo4j_dal: Neo4jDAL, clean_test_database):
    """Test that creating an existing node returns the existing node."""
    # Arrange
    user_id = str(uuid.uuid4())
    label = "User"
    properties = {
        "userId": user_id,
        "name": "Test User",
        "email": "test@example.com"
    }
    constraints = {"userId": user_id}
    
    # Create the node first
    await test_neo4j_dal.create_node_if_not_exists(
        label, properties, constraints
    )
    
    # Act - Try to create the same node again with different properties
    new_properties = {
        "userId": user_id,
        "name": "Updated User",
        "email": "updated@example.com"
    }
    result = await test_neo4j_dal.create_node_if_not_exists(
        label, new_properties, constraints
    )
    
    # Assert - The node exists, but properties are not updated (due to MERGE behavior)
    assert result is not None
    assert result["userId"] == user_id
    assert result["name"] == "Test User"  # Original name, not updated
    assert result["email"] == "test@example.com"  # Original email, not updated


@pytest.mark.asyncio
async def test_create_node_with_empty_constraints_uses_properties(test_neo4j_dal: Neo4jDAL, clean_test_database):
    """Test creating a node with empty constraints uses properties as constraints."""
    # Arrange
    user_id = str(uuid.uuid4())
    label = "User"
    properties = {
        "userId": user_id,
        "name": "Test User",
        "email": "test@example.com"
    }
    
    # Act
    result = await test_neo4j_dal.create_node_if_not_exists(
        label, properties, None  # No constraints provided
    )
    
    # Assert
    assert result is not None
    assert result["userId"] == user_id
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"
    
    # Verify idempotency by creating the same node again
    result2 = await test_neo4j_dal.create_node_if_not_exists(
        label, properties, None
    )
    assert result2["userId"] == user_id


@pytest.mark.asyncio
async def test_create_node_with_empty_properties_raises_error(test_neo4j_dal: Neo4jDAL, clean_test_database):
    """Test creating a node with empty properties raises an error."""
    # Arrange
    label = "User"
    properties = {}
    
    # Act & Assert
    with pytest.raises(ValueError, match="Must provide constraint properties"):
        await test_neo4j_dal.create_node_if_not_exists(
            label, properties, None
        )


@pytest.mark.asyncio
async def test_create_relationship_if_not_exists_creates_new_relationship(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test creating a new relationship between two nodes."""
    # Arrange - Create user and project nodes
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"userId": user_id, "name": "Test User"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Project", {"projectId": project_id, "name": "Test Project"}
    )
    
    # Act - Create relationship
    result = await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user_id},
        "Project", {"projectId": project_id},
        "PARTICIPATED_IN",
        {"role": "Owner"}
    )
    
    # Assert
    assert result is True
    
    # Verify relationship exists in database (use the test DAL's driver)
    driver = test_neo4j_dal.driver # Access driver via property
    async with driver.session() as session:
        query = """
        MATCH (u:User {userId: $user_id})-[r:PARTICIPATED_IN]->(p:Project {projectId: $project_id})
        RETURN r.role as role
        """
        result = await session.run(query, {"user_id": user_id, "project_id": project_id})
        record = await result.single()
        assert record is not None
        assert record["role"] == "Owner"


@pytest.mark.asyncio
async def test_create_relationship_if_not_exists_is_idempotent(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test creating the same relationship twice is idempotent."""
    # Arrange - Create user and project nodes
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"userId": user_id, "name": "Test User"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Project", {"projectId": project_id, "name": "Test Project"}
    )
    
    # Create the relationship first time
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user_id},
        "Project", {"projectId": project_id},
        "PARTICIPATED_IN",
        {"role": "Owner"}
    )
    
    # Act - Create the same relationship again
    result = await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user_id},
        "Project", {"projectId": project_id},
        "PARTICIPATED_IN",
        {"role": "Contributor"}  # Different property
    )
    
    # Assert
    assert result is True
    
    # Verify relationship exists with original properties (properties aren't updated due to MERGE)
    driver = test_neo4j_dal.driver # Access driver via property
    async with driver.session() as session:
        query = """
        MATCH (u:User {userId: $user_id})-[r:PARTICIPATED_IN]->(p:Project {projectId: $project_id})
        RETURN r.role as role
        """
        result = await session.run(query, {"user_id": user_id, "project_id": project_id})
        record = await result.single()
        assert record is not None
        assert record["role"] == "Owner"  # Original role, not updated


@pytest.mark.asyncio
async def test_create_relationship_with_missing_nodes_creates_no_relationship(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test that trying to create a relationship between non-existent nodes does nothing."""
    # Arrange - Generate IDs but don't create nodes
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    
    # Act - Try to create relationship
    result = await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user_id},
        "Project", {"projectId": project_id},
        "PARTICIPATED_IN"
    )
    
    # Assert - Should return False since no relationship was created
    assert result is False


@pytest.mark.asyncio
async def test_get_session_participants_returns_users(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test retrieving users who participated in a session."""
    # Arrange - Create session and users
    session_id = str(uuid.uuid4())
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    
    await test_neo4j_dal.create_node_if_not_exists(
        "Session", {"sessionId": session_id, "name": "Test Session"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"userId": user1_id, "name": "User 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"userId": user2_id, "name": "User 2"}
    )
    
    # Create relationships
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user1_id},
        "Session", {"sessionId": session_id},
        "PARTICIPATED_IN"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user2_id},
        "Session", {"sessionId": session_id},
        "PARTICIPATED_IN"
    )
    
    # Act
    participants = await test_neo4j_dal.get_session_participants(session_id)
    
    # Assert
    assert len(participants) == 2
    participant_ids = [p["userId"] for p in participants]
    assert user1_id in participant_ids
    assert user2_id in participant_ids


@pytest.mark.asyncio
async def test_get_session_participants_empty_for_nonexistent_session(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test that get_session_participants returns empty list for nonexistent session."""
    # Arrange
    session_id = str(uuid.uuid4())
    
    # Act
    participants = await test_neo4j_dal.get_session_participants(session_id)
    
    # Assert
    assert len(participants) == 0


@pytest.mark.asyncio
async def test_get_project_context_returns_complete_context(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test retrieving the complete context for a project."""
    # Arrange - Create project, sessions, documents, and users
    project_id = str(uuid.uuid4())
    session1_id = str(uuid.uuid4())
    session2_id = str(uuid.uuid4())
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    
    # Create nodes
    await test_neo4j_dal.create_node_if_not_exists(
        "Project", {"projectId": project_id, "name": "Test Project"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Session", {"sessionId": session1_id, "name": "Session 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Session", {"sessionId": session2_id, "name": "Session 2"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Document", {"docId": doc1_id, "name": "Document 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Document", {"docId": doc2_id, "name": "Document 2"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"userId": user1_id, "name": "User 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"userId": user2_id, "name": "User 2"}
    )
    
    # Create relationships
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Session", {"sessionId": session1_id},
        "Project", {"projectId": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Session", {"sessionId": session2_id},
        "Project", {"projectId": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Document", {"docId": doc1_id},
        "Project", {"projectId": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Document", {"docId": doc2_id},
        "Project", {"projectId": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user1_id},
        "Session", {"sessionId": session1_id},
        "PARTICIPATED_IN"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"userId": user2_id},
        "Session", {"sessionId": session2_id},
        "PARTICIPATED_IN"
    )
    
    # Act
    context = await test_neo4j_dal.get_project_context(project_id)
    
    # Assert
    assert len(context["sessions"]) == 2
    assert len(context["documents"]) == 2
    assert len(context["users"]) == 2
    
    session_ids = [s["sessionId"] for s in context["sessions"]]
    assert session1_id in session_ids
    assert session2_id in session_ids
    
    doc_ids = [d["docId"] for d in context["documents"]]
    assert doc1_id in doc_ids
    assert doc2_id in doc_ids
    
    user_ids = [u["userId"] for u in context["users"]]
    assert user1_id in user_ids
    assert user2_id in user_ids 