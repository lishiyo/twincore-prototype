# sample_data.py

import uuid

# --- 1. Define Core Entity IDs (Use real UUIDs in practice) ---
USER_ALICE_ID = str(uuid.uuid4()) # Let's say Alice is user 1
USER_BOB_ID = str(uuid.uuid4())   # Let's say Bob is user 2

ORG_AGI_HOUSE_ID = str(uuid.uuid4())

TEAM_CORE_DEV_ID = str(uuid.uuid4())

PROJECT_F0_CANVAS_ID = str(uuid.uuid4()) # Project 1
PROJECT_TWIN_RND_ID = str(uuid.uuid4())  # Project 2

SESSION_P1_KICKOFF_ID = str(uuid.uuid4()) # Project 1, Session 1
SESSION_P1_SYNC_ID = str(uuid.uuid4())    # Project 1, Session 2
SESSION_P2_STANDUP_ID = str(uuid.uuid4()) # Project 2, Session 1

DOC_P1_SPEC_ID = str(uuid.uuid4())        # Doc 1 (Proj 1)
DOC_ALICE_NOTES_ID = str(uuid.uuid4())    # Doc 2 (User Alice)
DOC_P1_S1_TRANSCRIPT_ID = str(uuid.uuid4())# Doc 3 (Proj 1, Session 1)
DOC_P1_S2_DIAGRAM_ID = str(uuid.uuid4())   # Doc 4 (Proj 1, Session 2)

# --- 2. Sample Data for Ingestion (List of Memory Chunks) ---
# Each dict represents a text chunk to be embedded and stored.
# Metadata links it to relevant entities for filtering and graph relationships.

memory_chunks_data = [
    # == Document 1: Project 1 Spec (Scoped to Project) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "text": "Framework Zero Vision: Enable post-labor, autonomous organizations blending human creativity with transparent AI orchestration. Focus on agentic workflows.",
        "metadata": {
            "doc_id": DOC_P1_SPEC_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "document_chunk",
            "doc_name": "F0 Canvas Core Spec",
            "user_id": None, # Document level, not user-specific chunk authorship
            "session_id": None,
            "message_id": None,
            "team_id": TEAM_CORE_DEV_ID, # Assume project owned by team
            "timestamp": "2025-05-01T10:00:00Z",
        }
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "text": "Core Tech Stack: React/Vite frontend with Yjs for CRDT sync. Supabase backend (Postgres+Realtime). LangGraph for LLM orchestration. Qdrant for vector search, Neo4j for relationship graph.",
        "metadata": {
            "doc_id": DOC_P1_SPEC_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "document_chunk",
            "doc_name": "F0 Canvas Core Spec",
            "user_id": None,
            "session_id": None,
            "message_id": None,
            "team_id": TEAM_CORE_DEV_ID,
            "timestamp": "2025-05-01T10:05:00Z",
        }
    },

    # == Document 2: Alice's Private Notes (Scoped to User) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "text": "Personal thought: Need to rigorously test LLM latency during live editing. A 5-second delay for diagram generation might be too long. Async fallback is key.",
        "metadata": {
            "doc_id": DOC_ALICE_NOTES_ID,
            "user_id": USER_ALICE_ID, # Clearly Alice's note
            "project_id": None, # Personal note, could be implicitly linked later
            "org_id": ORG_AGI_HOUSE_ID, # Assume user context implies org
            "source_type": "document_chunk",
            "doc_name": "Alice's Personal Dev Notes",
            "session_id": None,
            "message_id": None,
            "team_id": None, # Not tied to a specific team necessarily
            "timestamp": "2025-05-03T11:00:00Z",
        }
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "text": "Idea for Preference Aggregation UI: Maybe a dynamic Sankey diagram showing vote flow over time within a project session?",
        "metadata": {
            "doc_id": DOC_ALICE_NOTES_ID,
            "user_id": USER_ALICE_ID,
            "project_id": None,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "document_chunk",
            "doc_name": "Alice's Personal Dev Notes",
            "session_id": None,
            "message_id": None,
            "team_id": None,
            "timestamp": "2025-05-03T11:05:00Z",
        }
    },

    # == Document 3: Session P1S1 Transcript (Scoped to Project + Session) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "text": "Alice speaking: Welcome to the F0 Canvas Core kickoff! Our main goal today is to align on the 90-day roadmap and MVP scope.",
        "metadata": {
            "doc_id": DOC_P1_S1_TRANSCRIPT_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "session_id": SESSION_P1_KICKOFF_ID, # Linked to this specific session
            "user_id": USER_ALICE_ID, # Speaker identified
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "transcript_snippet",
            "doc_name": "Transcript: P1 Kickoff Meeting",
            "message_id": None, # Could link to a message if chat was source
            "team_id": TEAM_CORE_DEV_ID,
            "timestamp": "2025-05-04T09:05:00Z", # Timestamp within session
        }
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "text": "Bob speaking: Regarding the tech stack, Supabase seems solid for the backend, but we need strong vector search for the twin memory. Qdrant looks promising.",
        "metadata": {
            "doc_id": DOC_P1_S1_TRANSCRIPT_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "session_id": SESSION_P1_KICKOFF_ID,
            "user_id": USER_BOB_ID, # Speaker identified
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "transcript_snippet",
            "doc_name": "Transcript: P1 Kickoff Meeting",
            "message_id": None,
            "team_id": TEAM_CORE_DEV_ID,
            "timestamp": "2025-05-04T09:15:00Z",
        }
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "text": "Alice speaking: Good point, Bob. Let's add Qdrant to the plan. We also need to consider graph relationships for the twin layer - Neo4j could handle that well.",
        "metadata": {
            "doc_id": DOC_P1_S1_TRANSCRIPT_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "session_id": SESSION_P1_KICKOFF_ID,
            "user_id": USER_ALICE_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "transcript_snippet",
            "doc_name": "Transcript: P1 Kickoff Meeting",
            "message_id": None,
            "team_id": TEAM_CORE_DEV_ID,
            "timestamp": "2025-05-04T09:16:00Z",
        }
    },

    # == Document 4: Session P1S2 Diagram Desc (Scoped to Project + Session) ==
     {
        "chunk_id": str(uuid.uuid4()),
        "text": "Auto-generated description of canvas activity: Diagram shows user flow for 'Make Diagram' button. Connects transcript processor to LangGraph orchestrator node.",
        "metadata": {
            "doc_id": DOC_P1_S2_DIAGRAM_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "session_id": SESSION_P1_SYNC_ID, # Different Session, Same Project
            "user_id": None, # System generated
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "document_chunk",
            "doc_name": "Diagram Desc: Make Diagram Flow",
            "message_id": None,
            "team_id": TEAM_CORE_DEV_ID,
            "timestamp": "2025-05-10T14:30:00Z",
        }
    },

    # == Chat Messages ==

    # -- Project 1, Session 1 --
    {
        "chunk_id": str(uuid.uuid4()),
        "message_id": str(uuid.uuid4()), # Unique message ID
        "text": "Let's define the MVP scope clearly. What's the absolute minimum for the 'Make Diagram' feature?",
        "metadata": {
            "message_id": None, # Set above
            "user_id": USER_ALICE_ID,
            "session_id": SESSION_P1_KICKOFF_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "team_id": TEAM_CORE_DEV_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "message",
            "doc_id": None,
            "timestamp": "2025-05-04T09:25:00Z",
        }
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "message_id": str(uuid.uuid4()),
        "text": "I think just raw transcript -> static graph generation is MVP. Real-time editing and refinement can come in v2.",
        "metadata": {
            "message_id": None, # Set above
            "user_id": USER_BOB_ID, # Different user, same session/project
            "session_id": SESSION_P1_KICKOFF_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "team_id": TEAM_CORE_DEV_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "message",
            "doc_id": None,
            "timestamp": "2025-05-04T09:26:00Z",
        }
    },

    # -- Project 1, Session 2 --
    {
        "chunk_id": str(uuid.uuid4()),
        "message_id": str(uuid.uuid4()),
        "text": "Now discussing the Twin Whisperer aspect from the roadmap. How do we ensure user privacy with their personal data?",
        "metadata": {
            "message_id": None, # Set above
            "user_id": USER_ALICE_ID, # Alice again, but different session
            "session_id": SESSION_P1_SYNC_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "team_id": TEAM_CORE_DEV_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "message",
            "doc_id": None,
            "timestamp": "2025-05-10T14:45:00Z",
        }
    },
     {
        "chunk_id": str(uuid.uuid4()),
        "message_id": str(uuid.uuid4()),
        "text": "E2E encryption for the twin's private memory store stored locally or user-controlled cloud seems essential. Needs careful IAM design.",
        "metadata": {
            "message_id": None, # Set above
            "user_id": USER_BOB_ID, # Bob again, different session
            "session_id": SESSION_P1_SYNC_ID,
            "project_id": PROJECT_F0_CANVAS_ID,
            "team_id": TEAM_CORE_DEV_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "message",
            "doc_id": None,
            "timestamp": "2025-05-10T14:46:00Z",
        }
    },

    # -- Project 2, Session 1 --
    {
        "chunk_id": str(uuid.uuid4()),
        "message_id": str(uuid.uuid4()),
        "text": "Okay, for the Twin Memory R&D project: I'm exploring Neo4j vs pure relational models for storing and querying user preferences efficiently.",
        "metadata": {
            "message_id": None, # Set above
            "user_id": USER_ALICE_ID, # Alice on a different project
            "session_id": SESSION_P2_STANDUP_ID,
            "project_id": PROJECT_TWIN_RND_ID, # Different project
            "team_id": TEAM_CORE_DEV_ID, # Assume same team, different project context
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "message",
            "doc_id": None,
            "timestamp": "2025-05-11T10:05:00Z",
        }
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "message_id": str(uuid.uuid4()),
        "text": "Need to benchmark Qdrant filtering performance, especially with lists in metadata like topic_ids.",
        "metadata": {
            "message_id": None, # Set above
            "user_id": USER_ALICE_ID, # Alice on Project 2
            "session_id": SESSION_P2_STANDUP_ID,
            "project_id": PROJECT_TWIN_RND_ID,
            "team_id": TEAM_CORE_DEV_ID,
            "org_id": ORG_AGI_HOUSE_ID,
            "source_type": "message",
            "doc_id": None,
            "timestamp": "2025-05-11T10:15:00Z",
        }
    },
]

# --- 3. Example Queries for Testing Retrieval ---

example_queries = [
    {
        "query_description": "GROUP: What did Bob say about the tech stack specifically in the kickoff meeting?",
        "natural_language": "What did Bob say about the tech stack in the kickoff meeting?",
        "semantic_search_terms": ["technology stack", "backend", "vector search"],
        "qdrant_filters": { # Filters applied to Qdrant vector search payload
            "must": [
                {"key": "user_id", "match": {"value": USER_BOB_ID}},
                {"key": "session_id", "match": {"value": SESSION_P1_KICKOFF_ID}},
                {"key": "project_id", "match": {"value": PROJECT_F0_CANVAS_ID}},
            ]
        },
        "expected_chunk_texts": [
            "Bob speaking: Regarding the tech stack, Supabase seems solid for the backend, but we need strong vector search for the twin memory. Qdrant looks promising."
        ] # Based on Doc 3, Chunk 2
    },
    {
        "query_description": "GROUP: What was discussed about diagrams or diagramming during the design sync?",
        "natural_language": "What was discussed about diagrams in the design sync?",
        "semantic_search_terms": ["diagram", "graph generation", "canvas visualization"],
        "qdrant_filters": {
             "must": [
                {"key": "session_id", "match": {"value": SESSION_P1_SYNC_ID}},
                 {"key": "project_id", "match": {"value": PROJECT_F0_CANVAS_ID}},
            ]
        },
         "expected_chunk_texts": [
             "Auto-generated description of canvas activity: Diagram shows user flow for 'Make Diagram' button. Connects transcript processor to LangGraph orchestrator node."
         ] # Based on Doc 4, Chunk 1
    },
    {
        "query_description": "GROUP: Summarize the F0 Canvas Core Spec document.",
        "natural_language": "Summarize the F0 Canvas Core Spec.",
        "semantic_search_terms": None, # Retrieve all chunks for the doc, then summarize
        "qdrant_filters": {
             "must": [
                {"key": "doc_id", "match": {"value": DOC_P1_SPEC_ID}},
            ]
        },
        "expected_chunk_texts": [
             "Framework Zero Vision: Enable post-labor, autonomous organizations blending human creativity with transparent AI orchestration. Focus on agentic workflows.",
             "Core Tech Stack: React/Vite frontend with Yjs for CRDT sync. Supabase backend (Postgres+Realtime). LangGraph for LLM orchestration. Qdrant for vector search, Neo4j for relationship graph."
        ] # Based on Doc 1, Chunks 1 & 2 (LLM would summarize these)
    },
    {
        "query_description": "PRIVATE: What were my (Alice's) concerns about LLM latency?",
        "natural_language": "What were my concerns about latency?",
        "semantic_search_terms": ["latency", "delay", "performance", "speed"],
        "qdrant_filters": {
            "must": [
                {"key": "user_id", "match": {"value": USER_ALICE_ID}}, # Filter strictly by user
            ]
            # Note: We might not filter by project/session here to find *all* mentions
        },
        "expected_chunk_texts": [
            "Personal thought: Need to rigorously test LLM latency during live editing. A 5-second delay for diagram generation might be too long. Async fallback is key."
        ] # Based on Doc 2, Chunk 1
    },
     {
        "query_description": "PRIVATE: What did I (Alice) say about Neo4j during the Twin R&D project?",
        "natural_language": "What did I say about Neo4j in the Twin R&D project?",
        "semantic_search_terms": ["Neo4j", "graph database", "relationships"],
        "qdrant_filters": {
            "must": [
                {"key": "user_id", "match": {"value": USER_ALICE_ID}},
                {"key": "project_id", "match": {"value": PROJECT_TWIN_RND_ID}}, # Scoped to Project 2
            ]
        },
        "expected_chunk_texts": [
             "Okay, for the Twin Memory R&D project: I'm exploring Neo4j vs pure relational models for storing and querying user preferences efficiently."
        ] # Based on Message from P2S1
    },
     {
        "query_description": "CROSS-CONTEXT: Find comments from Alice mentioning Qdrant.",
        "natural_language": "Find my comments mentioning Qdrant.",
         "semantic_search_terms": ["Qdrant", "vector database", "vector search"],
        "qdrant_filters": {
            "must": [
                {"key": "user_id", "match": {"value": USER_ALICE_ID}},
            ]
            # No project/session filter to find across all contexts
        },
        "expected_chunk_texts": [
            "Alice speaking: Good point, Bob. Let's add Qdrant to the plan. We also need to consider graph relationships for the twin layer - Neo4j could handle that well.", # From Doc 3 (P1S1)
            "Need to benchmark Qdrant filtering performance, especially with lists in metadata like topic_ids." # From Message (P2S1)
            # Note: The tech stack mention in Doc 1 might also appear if embedding captures it well enough, even though user_id is None.
        ]
    },
    {
        "query_description": "RELATIONSHIP + SEMANTIC: Who participated in the F0 Canvas Core kickoff? And what did they say about the MVP scope?",
        "natural_language": "Who was in the kickoff meeting and what was said about MVP scope?",
        "neo4j_query_part": "MATCH (s:Session {sessionId: $SESSION_P1_KICKOFF_ID})<-[:PARTICIPATED_IN]-(u:User) RETURN u.userId as participant_id", # Gets USER_ALICE_ID, USER_BOB_ID
        "semantic_search_terms": ["MVP", "minimum viable product", "scope", "feature set"],
        "qdrant_filters": { # Use participant IDs from Neo4j to filter Qdrant
             "must": [
                 {"key": "session_id", "match": {"value": SESSION_P1_KICKOFF_ID}},
                 # In a real script, you'd dynamically add the user IDs found by Neo4j:
                 # {"key": "user_id", "match": {"any": [USER_ALICE_ID, USER_BOB_ID]}}
                 # For this static example, we'll assume the logic finds comments by Alice or Bob in that session
                 {"key": "user_id", "match": {"any": [USER_ALICE_ID, USER_BOB_ID]}} # Static example placeholder
             ]
        },
         "expected_chunk_texts": [
             "Let's define the MVP scope clearly. What's the absolute minimum for the 'Make Diagram' feature?", # Alice's message P1S1
             "I think just raw transcript -> static graph generation is MVP. Real-time editing and refinement can come in v2." # Bob's message P1S1
         ]
    },
]

# --- Helper function to print data (Optional) ---
if __name__ == "__main__":
    print("--- Sample Entity IDs ---")
    print(f"User Alice: {USER_ALICE_ID}")
    print(f"User Bob:   {USER_BOB_ID}")
    print(f"Project F0 Canvas: {PROJECT_F0_CANVAS_ID}")
    print(f"Session P1 Kickoff: {SESSION_P1_KICKOFF_ID}")
    # ... print others as needed

    print("\n--- Sample Memory Chunks Data (First 2) ---")
    for i, chunk in enumerate(memory_chunks_data[:2]):
        print(f"\nChunk {i+1}:")
        print(f"  Text: {chunk['text'][:100]}...") # Print snippet
        print(f"  Metadata: {chunk['metadata']}")

    print("\n--- Sample Example Queries (First 2) ---")
    for i, query in enumerate(example_queries[:2]):
        print(f"\nQuery {i+1}: {query['query_description']}")
        print(f"  NL: {query['natural_language']}")
        print(f"  Search Terms: {query['semantic_search_terms']}")
        print(f"  Qdrant Filters: {query['qdrant_filters']}")
        print(f"  Expected Texts: {query['expected_chunk_texts']}")