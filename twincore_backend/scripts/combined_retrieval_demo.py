#!/usr/bin/env python
import uuid
import random
import os
from pprint import pprint
from datetime import datetime
from typing import Literal
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# --- Load Environment Variables ---
load_dotenv()
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

if not NEO4J_PASSWORD:
    raise ValueError("NEO4J_PASSWORD environment variable not set.")

# --- Mock Data Simulation (Keep chunk definitions) ---

# Simulate unique IDs (Keep these definitions)
USER_ALICE = str(uuid.uuid4())
USER_BOB = str(uuid.uuid4())
USER_CHARLIE = str(uuid.uuid4())
PROJ_ALPHA = str(uuid.uuid4())
PROJ_BETA = str(uuid.uuid4())
SESS_ALPHA_1 = str(uuid.uuid4())
SESS_ALPHA_2 = str(uuid.uuid4())
SESS_BETA_1 = str(uuid.uuid4())
DOC_ALPHA_DESIGN = str(uuid.uuid4())
DOC_ALPHA_BUDGET = str(uuid.uuid4())
DOC_BETA_PLAN = str(uuid.uuid4())
DECISION_UI = str(uuid.uuid4())
ACTION_BUDGET_REVIEW = str(uuid.uuid4())

# Mock Chunks (Simulating Qdrant Search Results) - Keep MOCK_CHUNKS definition
# Add chunk_id variables for easier reference in seeding
CHUNK_REACT = str(uuid.uuid4())
CHUNK_BUDGET = str(uuid.uuid4())
CHUNK_FASTAPI_PREF = str(uuid.uuid4())
CHUNK_BETA_PYTHON = str(uuid.uuid4())
CHUNK_VUE = str(uuid.uuid4())
CHUNK_DOCKER_DEPLOY = str(uuid.uuid4())
CHUNK_BETA_DESIGN_SYSTEM = str(uuid.uuid4())

MOCK_CHUNKS = [
    {
        "chunk_id": CHUNK_REACT,
        "text_content": "For Project Alpha's UI, we should definitely consider using React for its component model.",
        "score": 0.95,
        "metadata": {"user_id": USER_ALICE, "project_id": PROJ_ALPHA, "session_id": SESS_ALPHA_1, "doc_id": DOC_ALPHA_DESIGN, "source_type": "message", "timestamp": datetime.now().isoformat(), "is_twin_interaction": False}
    },
    {
        "chunk_id": CHUNK_BUDGET,
        "text_content": "The budget discussion for Alpha needs revisiting; estimates seem high.",
        "score": 0.88,
        "metadata": {"user_id": USER_BOB, "project_id": PROJ_ALPHA, "session_id": SESS_ALPHA_2, "doc_id": DOC_ALPHA_BUDGET, "source_type": "message", "timestamp": datetime.now().isoformat(), "is_twin_interaction": False}
    },
    {
        "chunk_id": CHUNK_FASTAPI_PREF,
        "text_content": "I strongly prefer FastAPI for the backend API implementation in Alpha.",
        "score": 0.85,
        "metadata": {"user_id": USER_ALICE, "project_id": PROJ_ALPHA, "session_id": SESS_ALPHA_2, "doc_id": None, "source_type": "preference_statement", "timestamp": datetime.now().isoformat(), "is_twin_interaction": False} # Explicit preference
    },
    {
        "chunk_id": CHUNK_BETA_PYTHON,
        "text_content": "Project Beta's planning phase is going well, focusing on Python.",
        "score": 0.80,
        "metadata": {"user_id": USER_CHARLIE, "project_id": PROJ_BETA, "session_id": SESS_BETA_1, "doc_id": DOC_BETA_PLAN, "source_type": "document_chunk", "timestamp": datetime.now().isoformat(), "is_twin_interaction": False}
    },
    {
        "chunk_id": CHUNK_VUE,
        "text_content": "Thinking about UI components, maybe Vue is another option?",
        "score": 0.78,
        "metadata": {"user_id": USER_BOB, "project_id": PROJ_ALPHA, "session_id": SESS_ALPHA_1, "doc_id": None, "source_type": "message", "timestamp": datetime.now().isoformat(), "is_twin_interaction": False}
    },
    {
        "chunk_id": CHUNK_DOCKER_DEPLOY,
        "text_content": "Deployment for Alpha should use Docker containers on AWS.",
        "score": 0.75,
        "metadata": {"user_id": USER_ALICE, "project_id": PROJ_ALPHA, "session_id": SESS_ALPHA_2, "doc_id": None, "source_type": "message", "timestamp": datetime.now().isoformat(), "is_twin_interaction": False}
    },
    {
        "chunk_id": CHUNK_BETA_DESIGN_SYSTEM,
        "text_content": "Let's circle back on the design system choice next week.", # Semantically relevant to UI, but context is vague
        "score": 0.70,
        "metadata": {"user_id": USER_CHARLIE, "project_id": PROJ_BETA, "session_id": SESS_BETA_1, "doc_id": None, "source_type": "message", "timestamp": datetime.now().isoformat(), "is_twin_interaction": False} # Belongs to wrong project!
    },
]

# --- Neo4j Seeding and Cleanup ---

def seed_neo4j_data(driver: Driver, chunks: list[dict]):
    print("--- Seeding Mock Data into Neo4j ---")
    # Create constraints for uniqueness
    constraints_queries = [
        "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
        "CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.project_id IS UNIQUE",
        "CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE",
        "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE",
        "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
        "CREATE CONSTRAINT topic_name_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
        "CREATE CONSTRAINT preference_id_unique IF NOT EXISTS FOR (p:Preference) REQUIRE p.preference_id IS UNIQUE",
        "CREATE CONSTRAINT decision_id_unique IF NOT EXISTS FOR (d:Decision) REQUIRE d.decision_id IS UNIQUE",
        "CREATE CONSTRAINT action_id_unique IF NOT EXISTS FOR (a:ActionItem) REQUIRE a.action_id IS UNIQUE",
    ]
    with driver.session() as session:
        for query in constraints_queries:
            try:
                session.run(query)
            except Exception as e:
                print(f"Constraint creation possibly failed (may already exist): {e}")

        # Create User/Project/Session/Doc base nodes from metadata
        user_ids = {c["metadata"]["user_id"] for c in chunks}
        project_ids = {c["metadata"]["project_id"] for c in chunks}
        session_ids = {c["metadata"]["session_id"] for c in chunks if c["metadata"].get("session_id")}
        doc_ids = {c["metadata"]["doc_id"] for c in chunks if c["metadata"].get("doc_id")}

        session.run("UNWIND $ids AS id MERGE (u:User {user_id: id})", ids=list(user_ids))
        session.run("UNWIND $ids AS id MERGE (p:Project {project_id: id})", ids=list(project_ids))
        session.run("UNWIND $ids AS id MERGE (s:Session {session_id: id})", ids=list(session_ids))
        session.run("UNWIND $ids AS id MERGE (d:Document {document_id: id})", ids=list(doc_ids))

        # Create Topic Nodes
        topics_to_create = ["UI Framework", "Backend Framework", "Deployment", "Budgeting", "Python", "React", "Vue"]
        session.run("""
        UNWIND $topics AS topic_name
        MERGE (t:Topic {name: topic_name})
        """, topics=topics_to_create)

        # Create Chunk Nodes and Relationships
        for chunk in chunks:
            metadata = chunk["metadata"]
            params = {
                "chunk_id": chunk["chunk_id"],
                "text_content": chunk["text_content"],
                "score": chunk["score"],
                "user_id": metadata["user_id"],
                "project_id": metadata["project_id"],
                "session_id": metadata.get("session_id"),
                "doc_id": metadata.get("doc_id"),
                "source_type": metadata["source_type"],
                "timestamp": metadata["timestamp"],
                "is_twin_interaction": metadata["is_twin_interaction"]
            }
            # Create Chunk and link to User and Project
            session.run("""
            MATCH (u:User {user_id: $user_id})
            MATCH (p:Project {project_id: $project_id})
            MERGE (c:Chunk {chunk_id: $chunk_id})
            SET c += {text_content: $text_content, score: $score, source_type: $source_type, timestamp: $timestamp, is_twin_interaction: $is_twin_interaction}
            MERGE (u)-[:AUTHORED]->(c)
            MERGE (c)-[:CONTEXT_PROJECT]->(p) // Simple relationship for project context filtering
            """, params)

            # Link Chunk to Session if present
            if params["session_id"]:
                session.run("""
                MATCH (c:Chunk {chunk_id: $chunk_id})
                MATCH (s:Session {session_id: $session_id})
                MERGE (c)-[:PART_OF_SESSION]->(s)
                """, params)

            # Link Chunk to Document if present
            if params["doc_id"]:
                session.run("""
                MATCH (c:Chunk {chunk_id: $chunk_id})
                MATCH (d:Document {document_id: $doc_id})
                MERGE (c)-[:PART_OF_DOCUMENT]->(d)
                """, params)

            # Create simulated MENTIONS relationships to Topics
            mentioned_topics = []
            content_lower = chunk["text_content"].lower()
            if "react" in content_lower: mentioned_topics.extend(["UI Framework", "React"])
            if "vue" in content_lower: mentioned_topics.extend(["UI Framework", "Vue"])
            if "fastapi" in content_lower: mentioned_topics.append("Backend Framework")
            if "docker" in content_lower or "aws" in content_lower: mentioned_topics.append("Deployment")
            if "budget" in content_lower: mentioned_topics.append("Budgeting")
            if "python" in content_lower: mentioned_topics.append("Python")

            if mentioned_topics:
                 session.run("""
                 MATCH (c:Chunk {chunk_id: $chunk_id})
                 UNWIND $topics AS topic_name
                 MATCH (t:Topic {name: topic_name})
                 MERGE (c)-[:MENTIONS]->(t)
                 """, {"chunk_id": chunk["chunk_id"], "topics": list(set(mentioned_topics))}) # Use set to avoid duplicates

            # Create simulated explicit Preference (Example for Alice/Backend)
            if chunk["chunk_id"] == CHUNK_FASTAPI_PREF:
                pref_id = str(uuid.uuid4())
                session.run("""
                    MATCH (u:User {user_id: $user_id})
                    MATCH (t:Topic {name: 'Backend Framework'})
                    MATCH (src_chunk:Chunk {chunk_id: $chunk_id})
                    MERGE (pref:Preference {preference_id: $pref_id})
                    SET pref += {statement: 'Prefers FastAPI for backend.', user_id: $user_id, topic: 'Backend Framework'}
                    MERGE (u)-[:STATED]->(pref)
                    MERGE (pref)-[:RELATED_TO]->(t)
                    MERGE (pref)-[:DERIVED_FROM]->(src_chunk)
                """, {"user_id": USER_ALICE, "pref_id": pref_id, "chunk_id": chunk["chunk_id"]})

            # Create simulated inferred Preference (Example for Alice/Deployment)
            if chunk["chunk_id"] == CHUNK_DOCKER_DEPLOY:
                pref_id = str(uuid.uuid4())
                session.run("""
                    MATCH (u:User {user_id: $user_id})
                    MATCH (t:Topic {name: 'Deployment'})
                    MATCH (src_chunk:Chunk {chunk_id: $chunk_id})
                    MERGE (pref:Preference {preference_id: $pref_id})
                    SET pref += {statement: 'Prefers Docker on AWS for deployment.', user_id: $user_id, topic: 'Deployment'}
                    MERGE (u)-[:STATED]->(pref)
                    MERGE (pref)-[:RELATED_TO]->(t)
                    MERGE (pref)-[:DERIVED_FROM]->(src_chunk)
                """, {"user_id": USER_ALICE, "pref_id": pref_id, "chunk_id": chunk["chunk_id"]})

        # Create sample Decision and ActionItem, link them
        session.run("""
            MERGE (d:Decision {decision_id: $dec_id, text: 'Decided to use React for Project Alpha UI', timestamp: datetime()})
            MERGE (a:ActionItem {action_id: $act_id, text: 'Bob to review Alpha budget estimates by Friday', status: 'Open', assigned_to: $bob_id})
            WITH d, a
            MATCH (c_react:Chunk {chunk_id: $chunk_react_id})
            MATCH (c_budget:Chunk {chunk_id: $chunk_budget_id})
            MERGE (c_react)-[:LED_TO]->(d) // Link chunk to the decision it influenced
            MERGE (a)-[:CONTEXT_CHUNK]->(c_budget) // Link action item to the chunk that prompted it
        """, {
            "dec_id": DECISION_UI,
            "act_id": ACTION_BUDGET_REVIEW,
            "bob_id": USER_BOB,
            "chunk_react_id": CHUNK_REACT,
            "chunk_budget_id": CHUNK_BUDGET
        })

        # --- Add relationships for new filtering examples ---
        print("Adding extra relationships for filtering examples...")
        session.run("""
            MATCH (u:User {user_id: $alice_id})
            MATCH (p:Project {project_id: $proj_alpha_id})
            MERGE (u)-[:MANAGES]->(p)
        """, {"alice_id": USER_ALICE, "proj_alpha_id": PROJ_ALPHA})

        session.run("""
            MATCH (s:Session {session_id: $sess_alpha_1_id})
            MATCH (d:Document {document_id: $doc_alpha_design_id})
            MERGE (s)-[:ASSOCIATED_WITH]->(d)
        """, {"sess_alpha_1_id": SESS_ALPHA_1, "doc_alpha_design_id": DOC_ALPHA_DESIGN})
        print("Extra relationships added.")
        # --- End of added relationships ---

    print("--- Neo4j Seeding Complete ---")


def clear_neo4j_data(driver: Driver):
    print("--- Clearing All Data from Neo4j ---")
    with driver.session() as session:
        try:
            # Drop constraints first to avoid issues with deleting nodes
            constraints = session.run("SHOW CONSTRAINTS YIELD name").data()
            for constraint in constraints:
                session.run(f"DROP CONSTRAINT {constraint['name']}")
            print("Dropped constraints.")
        except Exception as e:
            print(f"Could not drop constraints (may not exist): {e}")

        # Delete all nodes and relationships
        session.run("MATCH (n) DETACH DELETE n")
    print("--- Neo4j Data Cleared ---")


# --- Mock Qdrant DAL Function (Remains Mocked) ---

def mock_qdrant_search(query_text: str, limit: int = 5) -> list[dict]:
    """Simulates Qdrant semantic search. Returns top N potentially relevant chunks."""
    print(f"--- Simulating Qdrant search for: '{query_text}' ---")
    # Very basic keyword matching for demo purposes (Keep this simple mock)
    keywords = query_text.lower().split()
    results = []
    
    # Special case for the document-session filtering example
    if "design document" in query_text.lower():
        # For this specific query, prioritize returning chunks from SESS_ALPHA_1 that are related to DOC_ALPHA_DESIGN
        # These are known to be CHUNK_REACT and CHUNK_VUE based on our mock data setup
        for chunk in MOCK_CHUNKS:
            if chunk["chunk_id"] in [CHUNK_REACT, CHUNK_VUE]:
                # Boost the score to ensure they're returned
                chunk_copy = chunk.copy()
                chunk_copy["score"] = 0.99 if chunk["chunk_id"] == CHUNK_REACT else 0.98
                results.append(chunk_copy)
        # Add a few more chunks for variety
        for chunk in MOCK_CHUNKS:
            if chunk["chunk_id"] not in [CHUNK_REACT, CHUNK_VUE] and "design" in chunk["text_content"].lower():
                results.append(chunk)
    else:
        # Regular keyword matching for other queries
        for chunk in MOCK_CHUNKS:
            # Simple keyword check
            content_lower = chunk["text_content"].lower()
            if any(keyword in content_lower for keyword in keywords):
                results.append(chunk)
            # Add some semantic near-matches based on simple rules
            elif "ui" in keywords and ("react" in content_lower or "vue" in content_lower or "design" in content_lower):
                 results.append(chunk)
            elif "deployment" in keywords and "docker" in content_lower:
                 results.append(chunk)
            elif "backend" in keywords and "fastapi" in content_lower:
                 results.append(chunk)
            elif "decision" in keywords and ("ui" in content_lower or "react" in content_lower):
                 results.append(chunk)

    # Sort by score desc and limit
    results.sort(key=lambda x: x["score"], reverse=True)
    print(f"Qdrant mock returned {len(results)} potential matches before limit.")
    return results[:limit]

# --- Actual Neo4j DAL Functions ---

def neo4j_filter_by_project(driver: Driver, chunk_results: list[dict], project_id: str) -> list[dict]:
    """Uses Neo4j to filter chunk results, keeping only those related to the project."""
    print(f"--- Using Neo4j filter: Keeping only chunks for Project ID: {project_id} ---")
    chunk_ids_from_qdrant = [chunk["chunk_id"] for chunk in chunk_results]
    if not chunk_ids_from_qdrant:
        return []

    query = """
    MATCH (c:Chunk)-[:CONTEXT_PROJECT]->(p:Project {project_id: $project_id})
    WHERE c.chunk_id IN $chunk_ids
    RETURN c.chunk_id AS valid_chunk_id
    """
    params = {"project_id": project_id, "chunk_ids": chunk_ids_from_qdrant}

    valid_ids = set()
    with driver.session() as session:
        result = session.run(query, params)
        for record in result:
            valid_ids.add(record["valid_chunk_id"])

    print(f"Neo4j confirmed {len(valid_ids)} chunks belong to the project.")
    return [chunk for chunk in chunk_results if chunk["chunk_id"] in valid_ids]


def neo4j_filter_by_project_manager(driver: Driver, chunk_results: list[dict], manager_id: str) -> list[dict]:
    """Uses Neo4j to filter chunks belonging to projects managed by the specified user."""
    print(f"--- Using Neo4j filter: Keeping only chunks for projects managed by User ID: {manager_id} ---")
    chunk_ids_from_qdrant = [chunk["chunk_id"] for chunk in chunk_results]
    if not chunk_ids_from_qdrant:
        return []

    query = """
    MATCH (manager:User {user_id: $manager_id})-[:MANAGES]->(p:Project)<-[:CONTEXT_PROJECT]-(c:Chunk)
    WHERE c.chunk_id IN $chunk_ids
    RETURN DISTINCT c.chunk_id AS valid_chunk_id
    """
    params = {"manager_id": manager_id, "chunk_ids": chunk_ids_from_qdrant}

    valid_ids = set()
    with driver.session() as session:
        result = session.run(query, params)
        for record in result:
            valid_ids.add(record["valid_chunk_id"])

    print(f"Neo4j confirmed {len(valid_ids)} chunks belong to projects managed by the user.")
    return [chunk for chunk in chunk_results if chunk["chunk_id"] in valid_ids]

def neo4j_filter_by_document_session(driver: Driver, chunk_results: list[dict], document_id: str) -> list[dict]:
    """Uses Neo4j to filter chunks belonging to sessions associated with the specified document."""
    print(f"--- Using Neo4j filter: Keeping only chunks from sessions associated with Document ID: {document_id} ---")
    chunk_ids_from_qdrant = [chunk["chunk_id"] for chunk in chunk_results]
    if not chunk_ids_from_qdrant:
        return []

    query = """
    MATCH (doc:Document {document_id: $document_id})<-[:ASSOCIATED_WITH]-(s:Session)<-[:PART_OF_SESSION]-(c:Chunk)
    WHERE c.chunk_id IN $chunk_ids
    RETURN DISTINCT c.chunk_id AS valid_chunk_id
    """
    params = {"document_id": document_id, "chunk_ids": chunk_ids_from_qdrant}

    valid_ids = set()
    with driver.session() as session:
        result = session.run(query, params)
        for record in result:
            valid_ids.add(record["valid_chunk_id"])

    print(f"Neo4j confirmed {len(valid_ids)} chunks belong to sessions associated with the document.")
    return [chunk for chunk in chunk_results if chunk["chunk_id"] in valid_ids]

def neo4j_get_chunk_context(driver: Driver, chunk_results: list[dict]) -> list[dict]:
    """Uses Neo4j to enrich chunks with connected Topic names (SIMPLE VERSION)."""
    print("--- Using Neo4j enrichment (SIMPLE): Adding Topic context ---")
    chunk_ids = [chunk["chunk_id"] for chunk in chunk_results]
    if not chunk_ids:
        return chunk_results

    query = """
    MATCH (c:Chunk)-[:MENTIONS]->(t:Topic)
    WHERE c.chunk_id IN $chunk_ids
    RETURN c.chunk_id AS chunkId, collect(t.name) AS topics
    """
    params = {"chunk_ids": chunk_ids}
    topic_map = {}
    with driver.session() as session:
        result = session.run(query, params)
        for record in result:
            topic_map[record["chunkId"]] = record["topics"]

    enriched_results = []
    for chunk in chunk_results:
        topics = topic_map.get(chunk["chunk_id"], [])
        if topics:
            if "neo4j_context" not in chunk: chunk["neo4j_context"] = {}
            chunk["neo4j_context"]["mentioned_topics"] = topics
        enriched_results.append(chunk)
    print(f"Neo4j (SIMPLE) enriched {len(topic_map)} chunks with topics.")
    return enriched_results

def neo4j_get_comprehensive_chunk_context(driver: Driver, chunk_results: list[dict]) -> list[dict]:
    """Uses Neo4j to enrich chunks with Authors, Topics, Sources, Decisions, Actions."""
    print("--- Using Neo4j enrichment (COMPREHENSIVE): Adding graph context ---")
    chunk_ids = [chunk["chunk_id"] for chunk in chunk_results]
    if not chunk_ids:
        return chunk_results

    # Use a dictionary to store enrichment data per chunk_id
    enrichment_data = {chunk_id: {} for chunk_id in chunk_ids}

    # Combine queries for efficiency where possible
    query = """
    UNWIND $chunk_ids AS c_id
    MATCH (c:Chunk {chunk_id: c_id})
    OPTIONAL MATCH (c)<-[:AUTHORED]-(u:User)
    OPTIONAL MATCH (c)-[:MENTIONS]->(t:Topic)
    OPTIONAL MATCH (c)-[:PART_OF_SESSION]->(s:Session)
    OPTIONAL MATCH (c)-[:PART_OF_DOCUMENT]->(d:Document)
    OPTIONAL MATCH (c)-[:LED_TO]->(dec:Decision)
    OPTIONAL MATCH (act:ActionItem)-[:CONTEXT_CHUNK]->(c)
    RETURN c.chunk_id AS chunkId,
           u.user_id AS authorId,
           collect(DISTINCT t.name) AS topics,
           s.session_id AS sessionId,
           d.document_id AS documentId,
           collect(DISTINCT dec.decision_id) AS decisionIds,
           collect(DISTINCT act.action_id) AS actionItemIds
    """
    params = {"chunk_ids": chunk_ids}

    with driver.session() as session:
        result = session.run(query, params)
        for record in result:
            c_id = record["chunkId"]
            enrichment_data[c_id] = {
                "author_id": record["authorId"],
                "mentioned_topics": [topic for topic in record["topics"] if topic], # Filter out potential nulls if any
                "source_session_id": record["sessionId"],
                "source_document_id": record["documentId"],
                "led_to_decision_ids": [dec_id for dec_id in record["decisionIds"] if dec_id],
                "prompted_action_item_ids": [act_id for act_id in record["actionItemIds"] if act_id]
            }

    enriched_results = []
    count = 0
    for chunk in chunk_results:
        context = enrichment_data.get(chunk["chunk_id"], {})
        if context: # Add context only if Neo4j found related data
            chunk["neo4j_context"] = context
            count += 1
        enriched_results.append(chunk)

    print(f"Neo4j (COMPREHENSIVE) enriched {count} chunks with context.")
    return enriched_results


def neo4j_find_preferences(driver: Driver, user_id: str, topic_name: str) -> list[dict]:
    """Uses Neo4j to find explicitly modeled Preference nodes."""
    print(f"--- Using Neo4j lookup: Finding preferences for User {user_id} on Topic '{topic_name}' ---")
    # Normalize topic name slightly for matching
    topic_match_name = topic_name
    if topic_name.lower() == "backend framework": topic_match_name = "Backend Framework"
    if topic_name.lower() == "deployment": topic_match_name = "Deployment"

    query = """
    MATCH (u:User {user_id: $user_id})-[:STATED]->(pref:Preference)-[:RELATED_TO]->(t:Topic {name: $topic_name})
    OPTIONAL MATCH (pref)-[:DERIVED_FROM]->(src:Chunk) // Get source chunk if linked
    RETURN
        pref.preference_id as preference_id,
        pref.statement as statement,
        pref.topic as topic,
        pref.user_id as user_id,
        src.chunk_id as source_chunk_id, // Include source chunk ID
        'explicit_preference' AS type // Label the type
    """
    params = {"user_id": user_id, "topic_name": topic_match_name}
    preferences = []
    with driver.session() as session:
        result = session.run(query, params)
        for record in result:
            preferences.append(dict(record)) # Convert record to dictionary

    print(f"Neo4j found {len(preferences)} explicit preferences.")
    return preferences


# --- Main Demonstration Logic ---

def run_combined_retrieval(
    driver: Driver,
    query_text: str,
    filter_type: Literal["project", "manager", "doc_session", "none"] = "none",
    filter_context_id: str | None = None,
    enrich_comprehensively: bool = False
):
    """Runs the retrieval process, showing raw and combined results."""
    print(f"{'='*20} Running Query: '{query_text}' {'='*20}")
    print(f"Filter Type: {filter_type}, Context ID: {filter_context_id or 'N/A'}")

    # 1. Get initial semantic results from Qdrant (still mocked)
    # Fetch slightly more to give filtering more to work with
    qdrant_results = mock_qdrant_search(query_text, limit=20)
    print("--- Qdrant Raw Semantic Results: ---")
    if not qdrant_results:
        print("No results found.")
        return # Stop early if Qdrant finds nothing
    else:
        pprint([{"id": r["chunk_id"][:8]+"...", "text": r["text_content"][:50]+"...", "score": r["score"], "project": r["metadata"].get("project_id", "N/A")[:8]+"..."} for r in qdrant_results])

    # 2. Use Neo4j for Contextual Filtering based on filter_type
    filtered_results = qdrant_results # Default to all results if no filtering
    if filter_type != "none" and filter_context_id:
        if filter_type == "project":
            filtered_results = neo4j_filter_by_project(driver, qdrant_results, filter_context_id)
            print("--- Results after Neo4j Project Filtering: ---")
        elif filter_type == "manager":
            filtered_results = neo4j_filter_by_project_manager(driver, qdrant_results, filter_context_id)
            print("--- Results after Neo4j Manager Filtering: ---")
        elif filter_type == "doc_session":
            filtered_results = neo4j_filter_by_document_session(driver, qdrant_results, filter_context_id)
            print("--- Results after Neo4j Document-Session Filtering: ---")

        if not filtered_results:
             print("No results match the specified Neo4j filter context.")
             return # Stop if filtering removed all results
        else:
             # Displaying less info for brevity
             pprint([{"id": r["chunk_id"][:8]+"...", "text": r["text_content"][:50]+"...", "score": r["score"], "project": r["metadata"].get("project_id", "N/A")[:8]+"..."} for r in filtered_results])
    elif filter_type != "none" and not filter_context_id:
        print(f"Warning: Filter type '{filter_type}' specified without a context ID. Skipping Neo4j filtering.")


    # 3. Use Neo4j for Enrichment (using the potentially filtered list)
    if not filtered_results:
         print("No results to enrich.")
         enriched_results = []
    elif enrich_comprehensively:
        enriched_results = neo4j_get_comprehensive_chunk_context(driver, filtered_results)
        print("--- Results after Neo4j COMPREHENSIVE Enrichment: ---")
        # Display comprehensive context using helper
        # Define safe_truncate function within this scope
        def safe_truncate(value, length=8):
            if value is None: return "N/A"
            return str(value)[:length] + "..." # Ensure value is string

        display_list = []
        for r in enriched_results:
            ctx = r.get("neo4j_context", {})
            display_list.append({
                "id": safe_truncate(r["chunk_id"]),
                "text": safe_truncate(r["text_content"], 50),
                "score": r.get("score"),
                "author": safe_truncate(ctx.get("author_id")),
                "topics": ctx.get("mentioned_topics", []),
                "session": safe_truncate(ctx.get("source_session_id")),
                "doc": safe_truncate(ctx.get("source_document_id")),
                "decision_links": ctx.get("led_to_decision_ids", []),
                "action_links": ctx.get("prompted_action_item_ids", [])
            })
        pprint(display_list)
    else:
        enriched_results = neo4j_get_chunk_context(driver, filtered_results) # Simple topic enrichment
        print("--- Results after Neo4j SIMPLE Enrichment (Topics added): ---")
        pprint([{"id": r["chunk_id"][:8]+"...", "text": r["text_content"][:50]+"...", "topics": r.get("neo4j_context", {}).get("mentioned_topics", []), "score": r["score"]} for r in enriched_results])

    # 4. Use Neo4j for Specific Lookups (Example: Preferences)
    final_results = enriched_results # Start with enriched results
    query_lower = query_text.lower()
    target_user_id = None
    target_topic = None

    # Simple logic to detect user/topic preference query
    if "alice" in query_lower and ("prefer" in query_lower or "preference" in query_lower):
        target_user_id = USER_ALICE
        if "backend" in query_lower or "api" in query_lower: target_topic = "Backend Framework"
        elif "deployment" in query_lower: target_topic = "Deployment"

    if target_user_id and target_topic:
         neo4j_preferences = neo4j_find_preferences(driver, target_user_id, target_topic)
         if neo4j_preferences:
             print(f"--- Adding Explicit Neo4j Preference Results for {target_topic}: ---")
             pprint(neo4j_preferences)
             # Avoid showing both the preference and its source chunk if source exists
             pref_source_ids = {p.get("source_chunk_id") for p in neo4j_preferences if p.get("source_chunk_id")}
             # Ensure final_results only contains dicts before filtering
             current_final_results = [r for r in final_results if isinstance(r, dict)]
             final_results = [chunk for chunk in current_final_results if chunk.get("chunk_id") not in pref_source_ids]
             final_results.extend(neo4j_preferences) # Add preference dicts

    print("--- Final Combined & Processed Results: ---")
    processed_display = []
    # Define safe_truncate function for this section as well
    def safe_truncate(value, length=8):
        if value is None: return "N/A"
        return str(value)[:length] + "..." # Ensure value is string

    # Adapt display based on whether comprehensive enrichment was done
    for item in final_results:
        if isinstance(item, dict) and item.get("type") == "explicit_preference": # Check if dict and type exists
            processed_display.append({
                "type": "Preference",
                "statement": item["statement"],
                "topic": item["topic"],
                "user": safe_truncate(item["user_id"])
            })
        elif isinstance(item, dict): # It's a chunk (assuming it's a dict)
            ctx = item.get("neo4j_context", {})
            # Check if comprehensive enrichment was done previously by looking for a specific key
            is_comprehensive = "author_id" in ctx
            chunk_display = {
                "type": "Chunk",
                "id": safe_truncate(item.get("chunk_id")),
                "text": safe_truncate(item.get("text_content"), 60),
                "score": item.get("score"),
                "topics": ctx.get("mentioned_topics", [])
            }
            if is_comprehensive:
                 chunk_display.update({
                     "author": safe_truncate(ctx.get("author_id")),
                     "session": safe_truncate(ctx.get("source_session_id")),
                     "doc": safe_truncate(ctx.get("source_document_id")),
                     "decision_links": ctx.get("led_to_decision_ids", []),
                     "action_links": ctx.get("prompted_action_item_ids", [])
                 })
            processed_display.append(chunk_display)
        # else: # Handle cases where item might not be a dict (e.g., if error occurred)
        #     print(f"Skipping display for unexpected item: {item}")

    pprint(processed_display)

if __name__ == "__main__":
    neo4j_driver = None
    try:
        # Establish Neo4j connection
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        neo4j_driver.verify_connectivity()
        print("Neo4j connection successful.")

        # Clear previous data and seed new data
        clear_neo4j_data(neo4j_driver)
        seed_neo4j_data(neo4j_driver, MOCK_CHUNKS)

        # --- Example Query 1: Project-Scoped Query --- Simple Enrichment
        run_combined_retrieval(
            driver=neo4j_driver,
            query_text="Tell me about the UI design",
            filter_type="project",
            filter_context_id=PROJ_ALPHA,
            enrich_comprehensively=False
        )

        # --- Example Query 2: Topic Enrichment --- Simple Enrichment
        run_combined_retrieval(
            driver=neo4j_driver,
            query_text="What was decided about deployment strategy for Alpha?",
            filter_type="project",
            filter_context_id=PROJ_ALPHA,
            enrich_comprehensively=False
        )

        # --- Example Query 3: Specific Preference Lookup --- Simple Enrichment
        run_combined_retrieval(
            driver=neo4j_driver,
            query_text="What does Alice prefer for the backend API?",
            filter_type="project", # Keep project filter
            filter_context_id=PROJ_ALPHA,
            enrich_comprehensively=False
        )

        # --- Example Query 4: Session Kickoff --- Comprehensive Enrichment
        run_combined_retrieval(
            driver=neo4j_driver,
            query_text="Finalize decision on UI framework",
            filter_type="project",
            filter_context_id=PROJ_ALPHA,
            enrich_comprehensively=True
        )

        # --- Example Query 5: Manager Filter --- Simple Enrichment
        # Goal: Find discussions related to projects managed by Alice
        run_combined_retrieval(
            driver=neo4j_driver,
            query_text="project discussions", # General query
            filter_type="manager",
            filter_context_id=USER_ALICE,
            enrich_comprehensively=False # Simple enrichment is fine
        )

        # --- Example Query 6: Document-Session Filter --- Simple Enrichment
        # Goal: Find discussions from sessions related to the Alpha Design Doc
        run_combined_retrieval(
            driver=neo4j_driver,
            query_text="design document discussion about components",  # More specific to match CHUNK_REACT and CHUNK_VUE
            filter_type="doc_session",
            filter_context_id=DOC_ALPHA_DESIGN,
            enrich_comprehensively=False # Simple enrichment is fine
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
    finally:
        # Clean up data and close connection
        if neo4j_driver:
            # Optional: Clear data after run if you want a clean slate next time
            # clear_neo4j_data(neo4j_driver)
            neo4j_driver.close()
            print("\nNeo4j connection closed.") 