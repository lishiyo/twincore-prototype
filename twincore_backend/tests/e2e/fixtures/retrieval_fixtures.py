"""Fixtures for seeding data for retrieval E2E tests."""

import uuid
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime

from services.ingestion_service import IngestionService
from services.embedding_service import EmbeddingService
from ingestion.connectors.message_connector import MessageConnector
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver

# --- Fixtures moved from test_retrieval_e2e.py ---

@pytest_asyncio.fixture
async def seed_test_data():
    """Seed test data for retrieval tests into the test databases.
    
    Returns a dict with the key IDs (user_id, project_id, session_id) for the test data.
    """
    # Generate unique IDs for our test data
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Initialize services with TEST database connections
    from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
    
    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )
    
    # Create MessageConnector to handle message ingestion
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Create test data for retrieval tests
    await message_connector.ingest_message({
        "text": "Today's meeting notes: We discussed the roadmap for Q3.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message"
    })
    
    await message_connector.ingest_message({
        "text": "Key action item from the meeting: Improve the search algorithm.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message"
    })
    
    # Return the key IDs for use in the tests
    return {
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id
    }

@pytest_asyncio.fixture
async def seed_private_test_data():
    """Seed private test data for retrieval tests into the test databases.
    
    Returns a dict with the key IDs (user_id, project_id) for the test data.
    """
    # Generate unique IDs for our test data
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    
    # Initialize services with TEST database connections
    from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
    
    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )
    
    # Create MessageConnector to handle message ingestion
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Create test data with both private and public content
    # Private content
    await message_connector.ingest_message({
        "text": "This is my personal document with private information.",
        "user_id": user_id,
        "project_id": project_id,
        "is_twin_chat": True,  # Mark as private
        "source_type": "message"
    })
    
    # Public content
    await message_connector.ingest_message({
        "text": "This is a public message everyone can see.",
        "user_id": user_id,
        "project_id": project_id,
        "is_twin_chat": False,  # Not private
        "source_type": "message"
    })
    
    # Return the key IDs for use in the tests
    return {
        "user_id": user_id,
        "project_id": project_id
    }

@pytest_asyncio.fixture
async def seed_related_content_data():
    """Seed test data with related content and relationships for testing related content retrieval.
    
    Returns key IDs for the test data.
    """
    # Generate unique IDs for our test data
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Initialize services with TEST database connections
    from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
    
    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    print("Using TEST database connections for data setup")
    
    # Create unique content IDs for our nodes - use exact UUIDs
    source_chunk_id = str(uuid.uuid4())
    related_chunk_id1 = str(uuid.uuid4())
    related_chunk_id2 = str(uuid.uuid4())
    
    print(f"Created source chunk ID: {source_chunk_id}")
    print(f"Created related chunk ID 1: {related_chunk_id1}")
    print(f"Created related chunk ID 2: {related_chunk_id2}")
    
    # Directly create Content nodes in Neo4j with known IDs
    source_props = {
        "chunk_id": source_chunk_id,  # Use chunk_id as the constraint property
        "text_content": "We need to discuss the UI design for the new feature.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "timestamp": datetime.now().isoformat(),
        "is_private": False  # Explicitly set as public
    }
    
    related_props1 = {
        "chunk_id": related_chunk_id1,
        "text_content": "I think we should use a card-based layout for the UI design.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "timestamp": datetime.now().isoformat(),
        "is_private": False  # Explicitly set as public
    }
    
    related_props2 = {
        "chunk_id": related_chunk_id2,
        "text_content": "The color scheme should match our brand guidelines.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "timestamp": datetime.now().isoformat(),
        "is_private": False  # Explicitly set as public
    }
    
    # Create the Content nodes directly in Neo4j
    await neo4j_dal.create_node_if_not_exists(
        label="Content",
        properties=source_props,
        constraints={"chunk_id": source_chunk_id}
    )
    
    await neo4j_dal.create_node_if_not_exists(
        label="Content",
        properties=related_props1,
        constraints={"chunk_id": related_chunk_id1}
    )
    
    await neo4j_dal.create_node_if_not_exists(
        label="Content",
        properties=related_props2,
        constraints={"chunk_id": related_chunk_id2}
    )
    
    # Add a small delay to ensure nodes are indexed before creating relationships
    await asyncio.sleep(1)
    
    # Create vector embeddings for these nodes in Qdrant
    source_embedding = await embedding_service.get_embedding(source_props["text_content"])
    related_embedding1 = await embedding_service.get_embedding(related_props1["text_content"])
    related_embedding2 = await embedding_service.get_embedding(related_props2["text_content"])
    
    await qdrant_dal.upsert_vector(
        chunk_id=source_chunk_id,
        vector=source_embedding,
        text_content=source_props["text_content"],
        user_id=user_id,
        project_id=project_id,
        session_id=session_id,
        source_type="message",
        timestamp=source_props["timestamp"]
    )
    
    await qdrant_dal.upsert_vector(
        chunk_id=related_chunk_id1,
        vector=related_embedding1,
        text_content=related_props1["text_content"],
        user_id=user_id,
        project_id=project_id,
        session_id=session_id,
        source_type="message",
        timestamp=related_props1["timestamp"]
    )
    
    await qdrant_dal.upsert_vector(
        chunk_id=related_chunk_id2,
        vector=related_embedding2,
        text_content=related_props2["text_content"],
        user_id=user_id,
        project_id=project_id,
        session_id=session_id,
        source_type="message",
        timestamp=related_props2["timestamp"]
    )
    
    # Create relationships between source and related chunks
    result1 = await neo4j_dal.create_relationship_if_not_exists(
        start_label="Content",
        start_constraints={"chunk_id": source_chunk_id},
        end_label="Content",
        end_constraints={"chunk_id": related_chunk_id1},
        relationship_type="RELATED_TO",
        properties={"strength": 0.9}
    )
    
    result2 = await neo4j_dal.create_relationship_if_not_exists(
        start_label="Content",
        start_constraints={"chunk_id": source_chunk_id},
        end_label="Content",
        end_constraints={"chunk_id": related_chunk_id2},
        relationship_type="RELATED_TO",
        properties={"strength": 0.8}
    )
    
    print(f"Created relationship 1: {result1}")
    print(f"Created relationship 2: {result2}")
    
    # Verify the nodes exist and are connected by running a query
    async with neo4j_driver.session() as session:
        # First check if nodes exist
        node_query = """
        MATCH (c:Content)
        WHERE c.chunk_id IN [$source_id, $related_id1, $related_id2]
        RETURN c.chunk_id as id
        """
        node_result = await session.run(
            node_query, 
            {
                "source_id": source_chunk_id,
                "related_id1": related_chunk_id1,
                "related_id2": related_chunk_id2
            }
        )
        node_rows = await node_result.data()
        
        print(f"Found {len(node_rows)} Content nodes in Neo4j:")
        for row in node_rows:
            print(f"  Node ID: {row['id']}")
        assert len(node_rows) == 3, "Failed to find all created Content nodes"
        
        # Check relationships AFTER creation attempts
        rel_query = """
        MATCH (src:Content {chunk_id: $source_id})-[r:RELATED_TO]->(dest:Content)
        RETURN src.chunk_id as source, dest.chunk_id as destination, type(r) as relationship_type
        """
        rel_result = await session.run(rel_query, {"source_id": source_chunk_id})
        rel_rows = await rel_result.data()
        
        # Log the relationship results for debugging
        print(f"Found {len(rel_rows)} relationships from source {source_chunk_id}:")
        for row in rel_rows:
            print(f"  {row['source']} -> {row['relationship_type']} -> {row['destination']}")
        
        # Assertion to catch issues early - we should have exactly 2 relationships now
        assert len(rel_rows) == 2, f"Expected exactly 2 relationships for source node {source_chunk_id}, but found {len(rel_rows)}"

        # Log the exact Cypher query that would be used by the get_related_content method
        debug_query = f"""
        MATCH (c1:Content {{chunk_id: \"{source_chunk_id}\"}})
        MATCH (c1)-[*1..2]-(c2:Content)
        WHERE NOT c2.is_private
        RETURN c2, 
            [(c2)-[r]->(n) | {{type: type(r), target_id: n.chunk_id, target_type: labels(n)[0]}}] as outgoing_rels,
            [(n)-[r]->(c2) | {{type: type(r), source_id: n.chunk_id, source_type: labels(n)[0]}}] as incoming_rels
        LIMIT 10
        """
        print(f"Debug query that would be executed:\n{debug_query}")
        
        # Try running our own simplified query
        simple_query = """
        MATCH (c1:Content {chunk_id: $source_id})-[r]-(c2:Content)
        RETURN c2.chunk_id as related_id
        """
        simple_result = await session.run(simple_query, {"source_id": source_chunk_id})
        simple_rows = await simple_result.data()
        
        print(f"Simple query found {len(simple_rows)} related Content nodes:")
        for row in simple_rows:
            print(f"  Related ID: {row['related_id']}")
        
        # Assertion to catch issues early - we should have at least 2 relationships
        assert len(simple_rows) >= 2, f"Simple query expected at least 2 relationships for source node {source_chunk_id}, but found {len(simple_rows)}"
    
    return {
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_chunk_id": source_chunk_id,
        "related_chunk_ids": [related_chunk_id1, related_chunk_id2]
    }

@pytest_asyncio.fixture
async def seed_topic_data():
    """Seed test data for topic retrieval tests.
    
    Creates content with topic relationships for testing the topic endpoint.
    """
    # Generate unique IDs for our test data
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Create a unique topic name for this test run
    topic_name = f"test-topic-{uuid.uuid4()}"
    
    # Initialize services with TEST database connections
    from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
    
    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    print("Using TEST database connections for data setup")
    
    # Create unique content IDs for our messages - use exact UUIDs
    chunk_id1 = str(uuid.uuid4())
    chunk_id2 = str(uuid.uuid4())
    topic_id = str(uuid.uuid4())
    
    print(f"Created topic ID: {topic_id}")
    print(f"Created chunk ID 1: {chunk_id1}")
    print(f"Created chunk ID 2: {chunk_id2}")
    
    # First, create a Topic node in Neo4j
    topic_props = {
        "id": topic_id,
        "name": topic_name,
        "description": "A test topic for e2e tests"
    }
    
    await neo4j_dal.create_node_if_not_exists(
        label="Topic",
        properties=topic_props,
        constraints={"id": topic_id}
    )
    
    # Create Content nodes directly in Neo4j
    content_props1 = {
        "chunk_id": chunk_id1,
        "text_content": f"This message discusses the {topic_name} in detail.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "timestamp": datetime.now().isoformat()
    }
    
    content_props2 = {
        "chunk_id": chunk_id2,
        "text_content": f"Here's another message mentioning {topic_name}.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "timestamp": datetime.now().isoformat()
    }
    
    await neo4j_dal.create_node_if_not_exists(
        label="Content",
        properties=content_props1,
        constraints={"chunk_id": chunk_id1}
    )
    
    await neo4j_dal.create_node_if_not_exists(
        label="Content",
        properties=content_props2,
        constraints={"chunk_id": chunk_id2}
    )
    
    # Create vector embeddings for these nodes in Qdrant
    content_embedding1 = await embedding_service.get_embedding(content_props1["text_content"])
    content_embedding2 = await embedding_service.get_embedding(content_props2["text_content"])
    
    await qdrant_dal.upsert_vector(
        chunk_id=chunk_id1,
        vector=content_embedding1,
        text_content=content_props1["text_content"],
        user_id=user_id,
        project_id=project_id,
        session_id=session_id,
        source_type="message",
        timestamp=content_props1["timestamp"]
    )
    
    await qdrant_dal.upsert_vector(
        chunk_id=chunk_id2,
        vector=content_embedding2,
        text_content=content_props2["text_content"],
        user_id=user_id,
        project_id=project_id,
        session_id=session_id,
        source_type="message",
        timestamp=content_props2["timestamp"]
    )
    
    # Create MENTIONS relationships between content and topic
    result1 = await neo4j_dal.create_relationship_if_not_exists(
        start_label="Content",
        start_constraints={"chunk_id": chunk_id1},
        end_label="Topic",
        end_constraints={"id": topic_id},
        relationship_type="MENTIONS",
        properties={"confidence": 0.95}
    )
    
    result2 = await neo4j_dal.create_relationship_if_not_exists(
        start_label="Content",
        start_constraints={"chunk_id": chunk_id2},
        end_label="Topic",
        end_constraints={"id": topic_id},
        relationship_type="MENTIONS",
        properties={"confidence": 0.9}
    )
    
    print(f"Created relationship 1: {result1}")
    print(f"Created relationship 2: {result2}")
    
    # Verify the relationships were created
    async with neo4j_driver.session() as session:
        # First check if nodes exist
        node_query = """
        MATCH (c:Content), (t:Topic {name: $topic_name})
        WHERE c.chunk_id IN [$chunk_id1, $chunk_id2]
        RETURN c.chunk_id as chunk_id, t.name as topic_name
        """
        node_result = await session.run(
            node_query, 
            {
                "topic_name": topic_name,
                "chunk_id1": chunk_id1,
                "chunk_id2": chunk_id2
            }
        )
        node_rows = await node_result.data()
        
        print(f"Found {len(node_rows)} Content nodes and topic in Neo4j:")
        for row in node_rows:
            print(f"  Content: {row.get('chunk_id', 'N/A')}, Topic: {row.get('topic_name', 'N/A')}")
        
        query = """
        MATCH (c:Content)-[r:MENTIONS]->(t:Topic {name: $topic_name})
        RETURN c.chunk_id as source, t.name as topic, type(r) as relationship_type
        """
        result = await session.run(query, {"topic_name": topic_name})
        rows = await result.data()
        
        # Log the results for debugging
        print(f"Found {len(rows)} content chunks mentioning topic '{topic_name}':")
        for row in rows:
            print(f"  {row['source']} -> {row['relationship_type']} -> {row['topic']}")
        
        # Try a simpler query to check relationships
        simple_query = """
        MATCH (c:Content)-[r:MENTIONS]->(t:Topic)
        WHERE t.name = $topic_name
        RETURN c.chunk_id as chunk_id
        """
        simple_result = await session.run(simple_query, {"topic_name": topic_name})
        simple_rows = await simple_result.data()
        
        print(f"Simple query found {len(simple_rows)} relationships:")
        for row in simple_rows:
            print(f"  Content chunk: {row['chunk_id']}")
        
        # Assertion to catch issues early
        assert len(rows) >= 2, f"Expected at least 2 relationships for topic '{topic_name}', but found {len(rows)}"
    
    return {
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "topic_name": topic_name,
        "topic_id": topic_id,
        "chunk_ids": [chunk_id1, chunk_id2]
    }

@pytest_asyncio.fixture
async def seed_multi_user_private_data():
    """Seed test data for multiple users with private and public content.
    
    Creates content for two users with mixed private/public permissions to test
    cross-user privacy filtering.
    """
    # Generate unique IDs for two test users
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())  # Shared project
    
    # Initialize services with TEST database connections
    from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
    
    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )
    
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Create test data for both users with varying privacy settings
    
    # User 1 private content (only visible to user 1)
    await message_connector.ingest_message({
        "text": "User 1's private notes about project planning.",
        "user_id": user1_id,
        "project_id": project_id,
        "is_private": True,
        "is_twin_chat": True,
        "source_type": "message"
    })
    
    # User 1 public content (visible to all)
    await message_connector.ingest_message({
        "text": "User 1's public message in team discussion.",
        "user_id": user1_id,
        "project_id": project_id,
        "is_private": False,
        "source_type": "message"
    })
    
    # User 2 private content (only visible to user 2)
    await message_connector.ingest_message({
        "text": "User 2's confidential meeting notes.",
        "user_id": user2_id,
        "project_id": project_id,
        "is_private": True,
        "is_twin_chat": True,
        "source_type": "message"
    })
    
    # User 2 public content (visible to all)
    await message_connector.ingest_message({
        "text": "User 2's shared project update.",
        "user_id": user2_id,
        "project_id": project_id,
        "is_private": False,
        "source_type": "message"
    })
    
    return {
        "user1_id": user1_id,
        "user2_id": user2_id,
        "project_id": project_id
    }

@pytest_asyncio.fixture
async def seed_twin_interaction_data():
    """Seed test data with both regular messages and twin interactions for testing include_messages_to_twin parameter."""
    # Generate unique IDs for our test data
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Initialize services with TEST database connections
    from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
    
    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )
    
    # Create MessageConnector to handle message ingestion
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Create test data - Regular message (not twin interaction)
    await message_connector.ingest_message({
        "text": "Regular message: We need to discuss the project timeline tomorrow.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "is_twin_chat": False,  # Not a twin interaction
        "is_private": False     # Explicitly not private
    })
    
    # Create test data - Twin interaction message
    await message_connector.ingest_message({
        "text": "Twin interaction: Remind me about the project timeline discussion.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "is_twin_chat": True,   # Mark as a twin interaction
        "is_private": False     # Explicitly not private, for testing purposes
    })
    
    # Wait a moment for data to be indexed
    await asyncio.sleep(2)
    
    # Return the key IDs for use in the tests
    return {
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id
    }

@pytest_asyncio.fixture
async def seed_group_context_data():
    """Seed test data for group context retrieval tests.

    Creates content for multiple users within the same project/session.
    """
    # Generate unique IDs
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Initialize services with TEST database connections
    from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver

    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()

    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )
    message_connector = MessageConnector(ingestion_service=ingestion_service)

    # Create Project and Session nodes
    await neo4j_dal.create_node_if_not_exists("Project", {"project_id": project_id})
    await neo4j_dal.create_node_if_not_exists("Session", {"session_id": session_id})
    # Link session to project
    await neo4j_dal.create_relationship_if_not_exists(
        "Session", {"session_id": session_id},
        "Project", {"project_id": project_id},
        "PART_OF"
    )

    # User A data (participates in session)
    await message_connector.ingest_message({
        "text": "User A discussing group project features.",
        "user_id": user_a_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message"
    })
    await message_connector.ingest_message({
        "text": "User A's private thought on the group project.",
        "user_id": user_a_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message",
        "is_private": True # Private message
    })

    # User B data (participates in session)
    await message_connector.ingest_message({
        "text": "User B replying about group project timelines.",
        "user_id": user_b_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message"
    })

    # Link users to session (implicitly done by message_connector)
    # Ensure relationships exist for Neo4j participant query
    await neo4j_dal.create_relationship_if_not_exists(
         "User", {"user_id": user_a_id},
         "Session", {"session_id": session_id},
         "PARTICIPATED_IN"
    )
    await neo4j_dal.create_relationship_if_not_exists(
         "User", {"user_id": user_b_id},
         "Session", {"session_id": session_id},
         "PARTICIPATED_IN"
    )

    # Wait for indexing
    await asyncio.sleep(2)

    return {
        "user_a_id": user_a_id,
        "user_b_id": user_b_id,
        "project_id": project_id,
        "session_id": session_id
    }

@pytest_asyncio.fixture
async def seed_multi_user_context_data():
    """Seed test data directly using DALs for user context retrieval.
    
    This fixture is used specifically for testing the /users/{user_id}/context endpoint.
    It creates distinct data scenarios including private docs and twin queries.
    """
    user1_id = str(uuid.uuid4())
    user2_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    qdrant_client = await get_test_async_qdrant_client()
    neo4j_driver = await get_test_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    
    # Local mock embedding service for seeding Qdrant
    # Need numpy for this mock
    import numpy as np
    from unittest.mock import AsyncMock # Need AsyncMock
    mock_embedding_service = AsyncMock(spec=EmbeddingService)
    async def mock_get_embedding(text):
        seed = sum(ord(c) for c in text) % 10000
        np.random.seed(seed)
        return np.random.randn(1536).astype(np.float32).tolist()
    mock_embedding_service.get_embedding = mock_get_embedding

    test_data = [
        # User 1 Data
        {"text": "User 1 private doc about project Alpha", "user_id": user1_id, "project_id": project_id, "session_id": session_id, "is_private": True, "source_type": "document", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
        {"text": "User 1 twin query about project Alpha timeline", "user_id": user1_id, "project_id": project_id, "session_id": session_id, "is_private": False, "source_type": "query", "is_twin_chat": True, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
        {"text": "User 1 public message in session about project Alpha release", "user_id": user1_id, "project_id": project_id, "session_id": session_id, "is_private": False, "source_type": "message", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
        # User 2 Data
        {"text": "User 2 public message about project Alpha features", "user_id": user2_id, "project_id": project_id, "session_id": session_id, "is_private": False, "source_type": "message", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
        {"text": "User 2 private message about project Alpha concerns", "user_id": user2_id, "project_id": project_id, "session_id": session_id, "is_private": True, "source_type": "message", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
    ]

    for item in test_data:
        # Create Neo4j Node
        node_properties = item.copy()
        node_properties["text_content"] = item["text"] # Align property name
        del node_properties["text"] # Remove original key
        
        await neo4j_dal.create_node_if_not_exists(
            label="Content", 
            properties=node_properties, 
            constraints={"chunk_id": item["chunk_id"]}
        )
        
        # Create Qdrant Vector
        vector = await mock_embedding_service.get_embedding(item["text"])
        await qdrant_dal.upsert_vector(
            chunk_id=item["chunk_id"],
            vector=vector,
            text_content=item["text"],
            user_id=item["user_id"],
            project_id=item.get("project_id"),
            session_id=item.get("session_id"),
            source_type=item["source_type"],
            timestamp=item["timestamp"],
            is_twin_interaction=item.get("is_twin_chat", False),
            is_private=item.get("is_private", False)
        )

    # Allow time for indexing
    await asyncio.sleep(2)

    return {
        "user1_id": user1_id,
        "user2_id": user2_id,
        "project_id": project_id,
        "session_id": session_id
    } 