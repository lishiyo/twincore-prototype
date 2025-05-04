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
        "user_id": user_id, # Using snake_case property name
        "name": "Test User",
        "email": "test@example.com"
    }
    constraints = {"user_id": user_id}
    
    # Act
    result = await test_neo4j_dal.create_node_if_not_exists(
        label, properties, constraints
    )
    
    # Assert
    assert result is not None
    assert result["user_id"] == user_id
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_create_node_if_not_exists_returns_existing_node(test_neo4j_dal: Neo4jDAL, clean_test_database):
    """Test that creating an existing node returns the existing node."""
    # Arrange
    user_id = str(uuid.uuid4())
    label = "User"
    properties = {
        "user_id": user_id,
        "name": "Test User",
        "email": "test@example.com"
    }
    constraints = {"user_id": user_id}
    
    # Create the node first
    await test_neo4j_dal.create_node_if_not_exists(
        label, properties, constraints
    )
    
    # Act - Try to create the same node again with different properties
    new_properties = {
        "user_id": user_id,
        "name": "Updated User",
        "email": "updated@example.com"
    }
    result = await test_neo4j_dal.create_node_if_not_exists(
        label, new_properties, constraints
    )
    
    # Assert - The node exists, but properties are not updated (due to MERGE behavior)
    assert result is not None
    assert result["user_id"] == user_id
    assert result["name"] == "Test User"  # Original name, not updated
    assert result["email"] == "test@example.com"  # Original email, not updated


@pytest.mark.asyncio
async def test_create_node_with_empty_constraints_uses_properties(test_neo4j_dal: Neo4jDAL, clean_test_database):
    """Test creating a node with empty constraints uses properties as constraints."""
    # Arrange
    user_id = str(uuid.uuid4())
    label = "User"
    properties = {
        "user_id": user_id,
        "name": "Test User",
        "email": "test@example.com"
    }
    
    # Act
    result = await test_neo4j_dal.create_node_if_not_exists(
        label, properties, None  # No constraints provided
    )
    
    # Assert
    assert result is not None
    assert result["user_id"] == user_id
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"
    
    # Verify idempotency by creating the same node again
    result2 = await test_neo4j_dal.create_node_if_not_exists(
        label, properties, None
    )
    assert result2["user_id"] == user_id


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
        "User", {"user_id": user_id, "name": "Test User"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Project", {"project_id": project_id, "name": "Test Project"}
    )
    
    # Act - Create relationship
    result = await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"user_id": user_id},
        "Project", {"project_id": project_id},
        "PARTICIPATED_IN",
        {"role": "Owner"}
    )
    
    # Assert
    assert result is True
    
    # Verify relationship exists in database (use the test DAL's driver)
    driver = test_neo4j_dal.driver # Access driver via property
    async with driver.session() as session:
        query = """
        MATCH (u:User {user_id: $user_id})-[r:PARTICIPATED_IN]->(p:Project {project_id: $project_id})
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
        "User", {"user_id": user_id, "name": "Test User"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Project", {"project_id": project_id, "name": "Test Project"}
    )
    
    # Create the relationship first time
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"user_id": user_id},
        "Project", {"project_id": project_id},
        "PARTICIPATED_IN",
        {"role": "Owner"}
    )
    
    # Act - Create the same relationship again
    result = await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"user_id": user_id},
        "Project", {"project_id": project_id},
        "PARTICIPATED_IN",
        {"role": "Contributor"}  # Different property
    )
    
    # Assert
    assert result is True
    
    # Verify relationship exists with original properties (properties aren't updated due to MERGE)
    driver = test_neo4j_dal.driver # Access driver via property
    async with driver.session() as session:
        query = """
        MATCH (u:User {user_id: $user_id})-[r:PARTICIPATED_IN]->(p:Project {project_id: $project_id})
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
        "User", {"user_id": user_id},
        "Project", {"project_id": project_id},
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
        "Session", {"session_id": session_id, "name": "Test Session"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"user_id": user1_id, "name": "User 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"user_id": user2_id, "name": "User 2"}
    )
    
    # Create relationships
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"user_id": user1_id},
        "Session", {"session_id": session_id},
        "PARTICIPATED_IN"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"user_id": user2_id},
        "Session", {"session_id": session_id},
        "PARTICIPATED_IN"
    )
    
    # Act
    participants = await test_neo4j_dal.get_session_participants(session_id)
    
    # Assert
    assert len(participants) == 2
    participant_ids = [p["user_id"] for p in participants]
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
        "Project", {"project_id": project_id, "name": "Test Project"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Session", {"session_id": session1_id, "name": "Session 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Session", {"session_id": session2_id, "name": "Session 2"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Document", {"doc_id": doc1_id, "name": "Document 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "Document", {"doc_id": doc2_id, "name": "Document 2"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"user_id": user1_id, "name": "User 1"}
    )
    await test_neo4j_dal.create_node_if_not_exists(
        "User", {"user_id": user2_id, "name": "User 2"}
    )
    
    # Create relationships
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Session", {"session_id": session1_id},
        "Project", {"project_id": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Session", {"session_id": session2_id},
        "Project", {"project_id": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Document", {"doc_id": doc1_id},
        "Project", {"project_id": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Document", {"doc_id": doc2_id},
        "Project", {"project_id": project_id},
        "PART_OF"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"user_id": user1_id},
        "Session", {"session_id": session1_id},
        "PARTICIPATED_IN"
    )
    await test_neo4j_dal.create_relationship_if_not_exists(
        "User", {"user_id": user2_id},
        "Session", {"session_id": session2_id},
        "PARTICIPATED_IN"
    )
    
    # Act
    context = await test_neo4j_dal.get_project_context(project_id)
    
    # Assert
    assert len(context["sessions"]) == 2
    assert len(context["documents"]) == 2
    assert len(context["users"]) == 2
    
    session_ids = [s["session_id"] for s in context["sessions"]]
    assert session1_id in session_ids
    assert session2_id in session_ids
    
    doc_ids = [d["doc_id"] for d in context["documents"]]
    assert doc1_id in doc_ids
    assert doc2_id in doc_ids
    
    user_ids = [u["user_id"] for u in context["users"]]
    assert user1_id in user_ids
    assert user2_id in user_ids


@pytest.mark.asyncio
async def test_get_related_content_returns_connected_content(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test retrieving content related to a specific chunk through relationships."""
    # Arrange - Create content nodes and relationships
    chunk_id = str(uuid.uuid4())
    related_chunk_id = str(uuid.uuid4())
    topic_id = str(uuid.uuid4())
    
    # Create content nodes
    await test_neo4j_dal.create_node_if_not_exists(
        "Content", {
            "chunk_id": chunk_id,
            "text_content": "Source content",
            "user_id": "user-1",
            "is_private": False
        }
    )
    
    await test_neo4j_dal.create_node_if_not_exists(
        "Content", {
            "chunk_id": related_chunk_id,
            "text_content": "Related content",
            "user_id": "user-1",
            "is_private": False
        }
    )
    
    # Create a topic node
    await test_neo4j_dal.create_node_if_not_exists(
        "Topic", {
            "name": "Test Topic",
            "topic_id": topic_id
        }
    )
    
    # Create relationships between nodes
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Content", {"chunk_id": chunk_id},
        "Topic", {"topic_id": topic_id},
        "MENTIONS"
    )
    
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Content", {"chunk_id": related_chunk_id},
        "Topic", {"topic_id": topic_id},
        "MENTIONS"
    )
    
    # Act - Retrieve related content
    results = await test_neo4j_dal.get_related_content(
        chunk_id=chunk_id,
        relationship_types=["MENTIONS"],
        limit=10,
        include_private=False,
        max_depth=2
    )
    
    # Assert
    assert len(results) >= 1
    
    # Find the related chunk in the results
    related_content = next((r for r in results if r.get("chunk_id") == related_chunk_id), None)
    assert related_content is not None
    assert related_content["text_content"] == "Related content"
    
    # Check for relationship data
    assert "outgoing_relationships" in related_content
    assert "incoming_relationships" in related_content


@pytest.mark.asyncio
async def test_get_related_content_respects_privacy_setting(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test that get_related_content respects the include_private flag."""
    # Arrange - Create content nodes with different privacy settings
    chunk_id = str(uuid.uuid4())
    public_chunk_id = str(uuid.uuid4())
    private_chunk_id = str(uuid.uuid4())
    topic_id = str(uuid.uuid4())
    
    # Create content nodes
    await test_neo4j_dal.create_node_if_not_exists(
        "Content", {
            "chunk_id": chunk_id,
            "text_content": "Source content",
            "user_id": "user-1",
            "is_private": False
        }
    )
    
    await test_neo4j_dal.create_node_if_not_exists(
        "Content", {
            "chunk_id": public_chunk_id,
            "text_content": "Public related content",
            "user_id": "user-1",
            "is_private": False
        }
    )
    
    await test_neo4j_dal.create_node_if_not_exists(
        "Content", {
            "chunk_id": private_chunk_id,
            "text_content": "Private related content",
            "user_id": "user-1",
            "is_private": True
        }
    )
    
    # Create a topic node
    await test_neo4j_dal.create_node_if_not_exists(
        "Topic", {
            "name": "Test Topic",
            "topic_id": topic_id
        }
    )
    
    # Create relationships between nodes and topic
    for content_id in [chunk_id, public_chunk_id, private_chunk_id]:
        await test_neo4j_dal.create_relationship_if_not_exists(
            "Content", {"chunk_id": content_id},
            "Topic", {"topic_id": topic_id},
            "MENTIONS"
        )
    
    # Act - Retrieve related content excluding private content
    public_results = await test_neo4j_dal.get_related_content(
        chunk_id=chunk_id,
        include_private=False
    )
    
    # Act - Retrieve related content including private content
    all_results = await test_neo4j_dal.get_related_content(
        chunk_id=chunk_id,
        include_private=True
    )
    
    # Assert - Public results should only include public content
    public_chunk_ids = [r.get("chunk_id") for r in public_results]
    assert public_chunk_id in public_chunk_ids
    assert private_chunk_id not in public_chunk_ids
    
    # Assert - All results should include both public and private content
    all_chunk_ids = [r.get("chunk_id") for r in all_results]
    assert public_chunk_id in all_chunk_ids
    assert private_chunk_id in all_chunk_ids


@pytest.mark.asyncio
async def test_get_related_content_with_max_depth(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test that get_related_content respects the max_depth parameter."""
    # Arrange - Create a chain of content nodes
    chunk_ids = [str(uuid.uuid4()) for _ in range(4)]  # Create 4 nodes in a chain
    
    # Create content nodes
    for i, chunk_id in enumerate(chunk_ids):
        await test_neo4j_dal.create_node_if_not_exists(
            "Content", {
                "chunk_id": chunk_id,
                "text_content": f"Content {i}",
                "user_id": "user-1",
                "is_private": False
            }
        )
    
    # Create direct relationships in a chain: 0->1->2->3
    for i in range(len(chunk_ids) - 1):
        await test_neo4j_dal.create_relationship_if_not_exists(
            "Content", {"chunk_id": chunk_ids[i]},
            "Content", {"chunk_id": chunk_ids[i+1]},
            "RELATED_TO"
        )
    
    # Act - Retrieve with depth 1 (should only get node 1)
    depth1_results = await test_neo4j_dal.get_related_content(
        chunk_id=chunk_ids[0],
        max_depth=1
    )
    
    # Act - Retrieve with depth 2 (should get nodes 1 and 2)
    depth2_results = await test_neo4j_dal.get_related_content(
        chunk_id=chunk_ids[0],
        max_depth=2
    )
    
    # Assert - Depth 1 should only include the directly connected node
    depth1_ids = [r.get("chunk_id") for r in depth1_results]
    assert chunk_ids[1] in depth1_ids
    assert chunk_ids[2] not in depth1_ids
    assert chunk_ids[3] not in depth1_ids
    
    # Assert - Depth 2 should include nodes at distance 1 and 2
    depth2_ids = [r.get("chunk_id") for r in depth2_results]
    assert chunk_ids[1] in depth2_ids
    assert chunk_ids[2] in depth2_ids
    assert chunk_ids[3] not in depth2_ids


@pytest.mark.asyncio
async def test_get_content_by_topic_returns_related_content(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test retrieving content related to a specific topic."""
    # Arrange - Create topic and content nodes
    topic_name = "Test Topic"
    user_id = "user-1"
    project_id = "project-1"
    
    # Create content chunks that mention the topic
    content1_id = str(uuid.uuid4())
    content2_id = str(uuid.uuid4())
    
    # Create a topic node
    await test_neo4j_dal.create_node_if_not_exists(
        "Topic", {
            "name": topic_name,
            "description": "A test topic"
        }
    )
    
    # Create content nodes
    await test_neo4j_dal.create_node_if_not_exists(
        "Content", {
            "chunk_id": content1_id,
            "text_content": "Content mentioning test topic",
            "user_id": user_id,
            "project_id": project_id,
            "is_private": False
        }
    )
    
    await test_neo4j_dal.create_node_if_not_exists(
        "Content", {
            "chunk_id": content2_id,
            "text_content": "Another content about test topic",
            "user_id": user_id,
            "project_id": project_id,
            "is_private": True
        }
    )
    
    # Create relationships - both content chunks mention the topic
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Content", {"chunk_id": content1_id},
        "Topic", {"name": topic_name},
        "MENTIONS"
    )
    
    await test_neo4j_dal.create_relationship_if_not_exists(
        "Content", {"chunk_id": content2_id},
        "Topic", {"name": topic_name},
        "MENTIONS"
    )
    
    # Act - Retrieve content by topic
    results = await test_neo4j_dal.get_content_by_topic(
        topic_name=topic_name,
        user_id=user_id,
        project_id=project_id,
        include_private=False
    )
    
    # Assert
    assert len(results) == 1  # Only the public content
    assert results[0]["chunk_id"] == content1_id
    assert "topic" in results[0]
    assert results[0]["topic"]["name"] == topic_name
    
    # Act - Retrieve including private content
    all_results = await test_neo4j_dal.get_content_by_topic(
        topic_name=topic_name,
        user_id=user_id,
        project_id=project_id,
        include_private=True
    )
    
    # Assert
    assert len(all_results) == 2  # Both public and private content
    result_ids = [r["chunk_id"] for r in all_results]
    assert content1_id in result_ids
    assert content2_id in result_ids


@pytest.mark.asyncio
async def test_get_content_by_topic_with_filters(
    test_neo4j_dal: Neo4jDAL, clean_test_database
):
    """Test get_content_by_topic with various filters."""
    # Arrange - Create topic and content nodes with different metadata
    topic_name = "Filter Topic"
    
    # Create a topic node
    await test_neo4j_dal.create_node_if_not_exists(
        "Topic", {
            "name": topic_name
        }
    )
    
    # Create content nodes with different metadata
    content_data = [
        {
            "chunk_id": str(uuid.uuid4()),
            "text_content": "Content for user 1, project 1, session 1",
            "user_id": "user-1",
            "project_id": "project-1",
            "session_id": "session-1",
            "is_private": False
        },
        {
            "chunk_id": str(uuid.uuid4()),
            "text_content": "Content for user 1, project 1, session 2",
            "user_id": "user-1",
            "project_id": "project-1",
            "session_id": "session-2",
            "is_private": False
        },
        {
            "chunk_id": str(uuid.uuid4()),
            "text_content": "Content for user 2, project 1",
            "user_id": "user-2",
            "project_id": "project-1",
            "is_private": False
        },
        {
            "chunk_id": str(uuid.uuid4()),
            "text_content": "Content for user 1, project 2",
            "user_id": "user-1",
            "project_id": "project-2",
            "is_private": False
        }
    ]
    
    # Create content nodes and relationships
    for content in content_data:
        await test_neo4j_dal.create_node_if_not_exists("Content", content)
        await test_neo4j_dal.create_relationship_if_not_exists(
            "Content", {"chunk_id": content["chunk_id"]},
            "Topic", {"name": topic_name},
            "MENTIONS"
        )
    
    # Act 1 - Filter by user_id
    user_results = await test_neo4j_dal.get_content_by_topic(
        topic_name=topic_name,
        user_id="user-1"
    )
    
    # Act 2 - Filter by project_id
    project_results = await test_neo4j_dal.get_content_by_topic(
        topic_name=topic_name,
        project_id="project-1"
    )
    
    # Act 3 - Filter by session_id
    session_results = await test_neo4j_dal.get_content_by_topic(
        topic_name=topic_name,
        session_id="session-1"
    )
    
    # Act 4 - Combined filters
    combined_results = await test_neo4j_dal.get_content_by_topic(
        topic_name=topic_name,
        user_id="user-1",
        project_id="project-1"
    )
    
    # Assert
    assert len(user_results) == 3  # All content for user-1
    assert len(project_results) == 3  # All content for project-1
    assert len(session_results) == 1  # All content for session-1
    assert len(combined_results) == 2  # Content for user-1 AND project-1


@pytest.mark.asyncio
async def test_get_user_preference_statements(test_neo4j_dal: Neo4jDAL,):
    """Test retrieving user preference statements from Neo4j."""
    # Create a test user
    test_user_id = f"test_user_{uuid.uuid4()}"
    test_topic = "dark mode"
    test_content = f"I really prefer {test_topic} interfaces over light ones."
    test_chunk_id = f"chunk_{uuid.uuid4()}"
    
    try:
        # Setup: Create a user node, a content node, and a topic node with relationships
        user_node = await test_neo4j_dal.create_node_if_not_exists(
            label="User",
            properties={"user_id": test_user_id, "name": "Test User"},
            constraints={"user_id": test_user_id}
        )
        
        # Create content node
        content_node = await test_neo4j_dal.create_node_if_not_exists(
            label="Content",
            properties={
                "chunk_id": test_chunk_id,
                "text_content": test_content,
                "user_id": test_user_id,
                "is_twin_interaction": False
            },
            constraints={"chunk_id": test_chunk_id}
        )
        
        # Create topic node
        topic_node = await test_neo4j_dal.create_node_if_not_exists(
            label="Topic",
            properties={"name": test_topic},
            constraints={"name": test_topic}
        )
        
        # Create relationships
        await test_neo4j_dal.create_relationship_if_not_exists(
            start_label="User",
            start_constraints={"user_id": test_user_id},
            end_label="Content",
            end_constraints={"chunk_id": test_chunk_id},
            relationship_type="CREATED"
        )
        
        # Create MENTIONS relationship
        await test_neo4j_dal.create_relationship_if_not_exists(
            start_label="Content",
            start_constraints={"chunk_id": test_chunk_id},
            end_label="Topic",
            end_constraints={"name": test_topic},
            relationship_type="MENTIONS"
        )
        
        # Create STATES_PREFERENCE relationship (stronger signal)
        await test_neo4j_dal.create_relationship_if_not_exists(
            start_label="Content",
            start_constraints={"chunk_id": test_chunk_id},
            end_label="Topic",
            end_constraints={"name": test_topic},
            relationship_type="STATES_PREFERENCE"
        )
        
        # Test the first query path (explicit STATES_PREFERENCE)
        preference_statements1 = await test_neo4j_dal.get_user_preference_statements(
            user_id=test_user_id,
            topic=test_topic
        )
        
        assert preference_statements1, "No preference statements found (explicit path)"
        assert len(preference_statements1) > 0, "Empty results list (explicit path)"
        assert preference_statements1[0]["chunk_id"] == test_chunk_id, "Wrong chunk ID returned"
        assert preference_statements1[0]["text_content"] == test_content, "Wrong text content returned"
        
        # Break the STATES_PREFERENCE relationship to test the second query path
        async with test_neo4j_dal.driver.session() as session:
            await session.run(
                "MATCH (c:Content {chunk_id: $chunk_id})-[r:STATES_PREFERENCE]->(t:Topic {name: $topic}) DELETE r",
                {"chunk_id": test_chunk_id, "topic": test_topic}
            )
        
        # Test the second query path (MENTIONS)
        preference_statements2 = await test_neo4j_dal.get_user_preference_statements(
            user_id=test_user_id,
            topic=test_topic
        )
        
        assert preference_statements2, "No preference statements found (mentions path)"
        assert len(preference_statements2) > 0, "Empty results list (mentions path)"
        assert preference_statements2[0]["chunk_id"] == test_chunk_id, "Wrong chunk ID returned"
        
        # Break the MENTIONS relationship to test the fallback query path
        async with test_neo4j_dal.driver.session() as session:
            await session.run(
                "MATCH (c:Content {chunk_id: $chunk_id})-[r:MENTIONS]->(t:Topic {name: $topic}) DELETE r",
                {"chunk_id": test_chunk_id, "topic": test_topic}
            )
        
        # Test the third query path (fallback)
        preference_statements3 = await test_neo4j_dal.get_user_preference_statements(
            user_id=test_user_id,
            topic=test_topic
        )
        
        assert preference_statements3, "No preference statements found (fallback path)"
        assert len(preference_statements3) > 0, "Empty results list (fallback path)"
        assert preference_statements3[0]["chunk_id"] == test_chunk_id, "Wrong chunk ID returned"
        
    finally:
        # Cleanup
        try:
            async with test_neo4j_dal.driver.session() as session:
                # Delete all created nodes and relationships
                await session.run(
                    """
                    MATCH (u:User {user_id: $user_id})
                    OPTIONAL MATCH (u)-[r1]->(c:Content {chunk_id: $chunk_id})
                    OPTIONAL MATCH (c)-[r2]->(t:Topic {name: $topic})
                    DETACH DELETE u, c, t
                    """,
                    {"user_id": test_user_id, "chunk_id": test_chunk_id, "topic": test_topic}
                )
        except Exception as e:
            logger.error(f"Error during test cleanup: {e}")


async def close(self):
    """Close the Neo4j driver and release resources."""
    if self._driver:
        try:
            await self._driver.close()
            logger.info("Neo4j driver closed successfully")
        except Exception as e:
            logger.error(f"Error closing Neo4j driver: {e}") 