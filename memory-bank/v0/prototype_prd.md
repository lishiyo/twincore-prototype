# TwinCore Prototype PRD

See [vision doc](./vision_doc.md) for the full outline of the project we are building and [./separation_strategy.md](./separation_strategy.md) for how we are dividing this project between two people. We will focus on Developer B (the digital twin service), fleshing out a prototype for this called **TwinCore**.

This prototype validates the core responsibilities of a digital twin that communicates with an external project management agent.

Tech Stack (python):
- Qdrant for vector database
- Neo4j for knowledge graph
- Streamlit for frontend

**I. Core Goal & Scope**

*   **Goal:** Demonstrate the Digital Twin backend's ability to ingest diverse data (docs, chat) and fulfill the core API contract for context retrieval (group & private) and user representation, using Qdrant+Neo4j.
*   **Scope:**
    *   3 simulated users (Alice, Bob, Charlie).
    *   1 simulated project ("Book Generator Agent").
    *   1 simulated *current* session within that project.
    *   Simulated historical data (docs/chat from past sessions/projects).
    *   Simulated API calls representing Canvas Agent needs.
    *   Minimal Streamlit UI for interaction and verification.
    *   Focus on `ingest` and `retrieve` API logic.

**II. Mocked Data & Constants**

We'll use Python constants similar to [`sample_data.py`](../../examples/data/sample_data.py), but tailored to this scenario. Assume these IDs would normally come from a shared User/Project service (like Supabase).

```python
# twin_core_mock_data.py

import uuid
from datetime import datetime, timedelta

# --- Entities (Mocking Postgres/Shared Service) ---
USER_ALICE_ID = str(uuid.uuid4())
USER_BOB_ID = str(uuid.uuid4())
USER_CHARLIE_ID = str(uuid.uuid4())
USERS = {
    USER_ALICE_ID: {"name": "Alice"},
    USER_BOB_ID: {"name": "Bob"},
    USER_CHARLIE_ID: {"name": "Charlie"}
}

PROJECT_BOOK_GEN_ID = str(uuid.uuid4()) # Current Project
PROJECT_PAST_WEB_ID = str(uuid.uuid4()) # Alice/Bob past project

SESSION_BOOK_CURRENT_ID = str(uuid.uuid4()) # Current Session for Book Gen
SESSION_BOOK_PAST_ID = str(uuid.uuid4())    # Past Session for Book Gen
SESSION_WEB_PAST_ID = str(uuid.uuid4())     # Past Session for Web project

# --- Initial Data for Seeding ---
initial_data_chunks = [
    # == Alice's Personal Docs (Historical) ==
    {"user_id": USER_ALICE_ID, "doc_id": str(uuid.uuid4()), "source_type": "document_chunk", "doc_name": "Alice_Personal_Ideas.txt", "text": "Idea: Use stable diffusion for generating unique cover art styles based on genre.", "timestamp": (datetime.now() - timedelta(days=10)).isoformat()},
    {"user_id": USER_ALICE_ID, "doc_id": str(uuid.uuid4()), "source_type": "document_chunk", "doc_name": "Alice_Meeting_Notes_Web.md", "project_id": PROJECT_PAST_WEB_ID, "session_id": SESSION_WEB_PAST_ID, "text": "Web Project Retro: Need better task tracking. Bob suggested ClickUp.", "timestamp": (datetime.now() - timedelta(days=30)).isoformat()},

    # == Bob's Personal Docs (Historical) ==
    {"user_id": USER_BOB_ID, "doc_id": str(uuid.uuid4()), "source_type": "document_chunk", "doc_name": "Bob_Marketing_Notes.txt", "text": "Potential niche for book gen: 'Keto recipes for busy programmers'. High search volume.", "timestamp": (datetime.now() - timedelta(days=5)).isoformat()},

    # == Charlie's Personal Docs (Historical) ==
    {"user_id": USER_CHARLIE_ID, "doc_id": str(uuid.uuid4()), "source_type": "document_chunk", "doc_name": "Charlie_Tech_Thoughts.md", "text": "Exploring using Markov chains for generating simple plot outlines, could be a starting point before LLM refinement.", "timestamp": (datetime.now() - timedelta(days=20)).isoformat()},

    # == Project Book Gen - Shared Docs (Past Session) ==
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_PAST_ID, "doc_id": str(uuid.uuid4()), "source_type": "document_chunk", "doc_name": "BookGen_Initial_Scope.md", "text": "Project Goal: Create an agent that takes a niche and outline, then generates a draft ebook.", "timestamp": (datetime.now() - timedelta(days=7)).isoformat()},
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_PAST_ID, "doc_id": str(uuid.uuid4()), "source_type": "transcript_snippet", "user_id": USER_ALICE_ID, "doc_name": "BookGen_Past_Session_Transcript.txt", "text": "Alice: We need to decide on the core LLM. Claude 3 Opus seems good for long-form.", "timestamp": (datetime.now() - timedelta(days=7, hours=1)).isoformat()},
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_PAST_ID, "doc_id": str(uuid.uuid4()), "source_type": "transcript_snippet", "user_id": USER_BOB_ID, "doc_name": "BookGen_Past_Session_Transcript.txt", "text": "Bob: Agreed on Opus for quality. But maybe GPT-4 for brainstorming outlines?", "timestamp": (datetime.now() - timedelta(days=7, hours=1, minutes=5)).isoformat()},

    # == Project Book Gen - Shared Docs (Current Session - Uploaded during session) ==
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_CURRENT_ID, "doc_id": str(uuid.uuid4()), "source_type": "document_chunk", "doc_name": "Competitor_Analysis.pdf", "user_id": USER_BOB_ID, "text": "Analysis Summary: Existing tools lack robust niche research integration.", "timestamp": datetime.now().isoformat()}, # Bob uploaded this

    # == Chat Messages (Historical - Past Book Gen Session) ==
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_PAST_ID, "user_id": USER_CHARLIE_ID, "message_id": str(uuid.uuid4()), "source_type": "message", "text": "How are we handling plagiarism checks?", "timestamp": (datetime.now() - timedelta(days=7, hours=1, minutes=10)).isoformat()},

    # == Chat Messages (Current Session - Group Chat) ==
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_CURRENT_ID, "user_id": USER_ALICE_ID, "message_id": str(uuid.uuid4()), "source_type": "message", "text": "Okay team, let's finalize the Q3 roadmap for the Book Generator.", "timestamp": (datetime.now() - timedelta(minutes=10)).isoformat()},
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_CURRENT_ID, "user_id": USER_BOB_ID, "message_id": str(uuid.uuid4()), "source_type": "message", "text": "My main priority is integrating the niche research tool.", "timestamp": (datetime.now() - timedelta(minutes=9)).isoformat()},
    {"project_id": PROJECT_BOOK_GEN_ID, "session_id": SESSION_BOOK_CURRENT_ID, "user_id": USER_CHARLIE_ID, "message_id": str(uuid.uuid4()), "source_type": "message", "text": "I think improving the outline generation logic is critical first.", "timestamp": (datetime.now() - timedelta(minutes=8)).isoformat()},
]

# --- Add metadata fields consistently ---
for chunk in initial_data_chunks:
    chunk.setdefault('project_id', None)
    chunk.setdefault('session_id', None)
    chunk.setdefault('user_id', None)
    chunk.setdefault('doc_id', None)
    chunk.setdefault('message_id', None)
    chunk['chunk_id'] = str(uuid.uuid4()) # Ensure every chunk has a unique ID
```

**III. Backend (FastAPI App)**

*   **Setup:** FastAPI project structure, install dependencies (`fastapi`, `uvicorn`, `qdrant-client`, `neo4j`, `sentence-transformers`, `python-dotenv`, `pydantic`).
*   **Database Clients:** Initialize Qdrant and Neo4j clients (connecting to local/Docker instances).
*   **Embedding Model:** Load `SentenceTransformer`.
*   **API Models (Pydantic):** Define models for API request bodies and responses (e.g., `IngestRequest`, `RetrievalRequest`, `ContextResponse`).
*   **Core Endpoints:**
    *   `POST /api/seed_data`: Endpoint to load `initial_data_chunks` into Qdrant/Neo4j.
    *   `POST /api/ingest/message`: Accepts user chat, group chat, or twin chat messages. Embeds text, stores in Qdrant with full metadata (`user_id`, `session_id`, `project_id`, `is_twin_chat: bool`), updates Neo4j relationships.
    *   `POST /api/ingest/document`: Simulates file upload. Accepts text content, `user_id`, `doc_name`, context (`project_id`, `session_id`), `is_private: bool`. Chunks the text (simple split for prototype), embeds chunks, stores in Qdrant with metadata (incl. `doc_id`), updates Neo4j.
    *   `POST /api/retrieve/context`: (Simulates Canvas Agent call) Takes `session_id`, `project_id`, `query_text`. Finds participants in Neo4j for the session, performs filtered Qdrant search across *all* relevant docs/messages in that session/project context. Returns ranked list of text chunks + metadata.
    *   `POST /api/retrieve/private_memory`: (Simulates User->Twin call) Takes `user_id`, `query_text`, optional `session_id`, `project_id` for scoping. Performs Qdrant search filtered *only* by `user_id` (+ optional scope), potentially boosting recent items or items from specified context. Returns ranked list. *Crucially, this endpoint also ingests the `query_text` as a twin chat message for the user.*
    *   `POST /api/query/user_preference`: (Simulates Canvas Agent -> Twin call) Takes `user_id`, `session_id`, `project_id`, `decision_topic` (e.g., "LLM Choice", "Roadmap Priority"). Queries Neo4j/Qdrant for past statements, votes (if implemented), or relevant messages by that `user_id` related to the topic in the given context. Returns a summary or relevant snippets. (Could use an LLM here eventually, but start with retrieval).
*   **Internal Logic:**
    *   **Ingestion:** Function to handle embedding, Qdrant upsert (vector + payload), and Neo4j MERGE operations for nodes and relationships based on metadata.
    *   **Retrieval:** Functions to build Qdrant filters dynamically based on API parameters, perform searches, and potentially query Neo4j first for IDs (like session participants).

**IV. Minimal UI (Streamlit App)**

*   **Setup:** Create a separate Python file (`streamlit_app.py`), install `streamlit`, `requests`.
*   **UI Layout:**
    *   **User Selector:** `st.selectbox` to choose which user (Alice, Bob, Charlie) is currently interacting.
    *   **Canvas Agent Simulation:**
        *   `st.text_input("Canvas Agent Query (e.g., 'Summarize discussion on roadmap')")`
        *   `st.button("Get Session Context")` -> Calls backend `/api/retrieve/context` with current project/session IDs.
        *   `st.text_input("Canvas Agent Preference Query (e.g., 'Niche research priority')")`
        *   `st.button("Ask Twin Preference")` -> Calls backend `/api/query/user_preference` for the *selected user*.
    *   **User <> Twin Interaction:**
        *   `st.text_area("Chat with your Twin")`
        *   `st.button("Send to Twin")` -> Calls backend `/api/retrieve/private_memory` with selected `user_id` and chat text. *This backend endpoint handles both retrieval AND ingestion of the user's query*.
    *   **Document Upload Simulation:**
        *   `st.text_input("Document Name (e.g., 'MyNewIdea.txt')")`
        *   `st.text_area("Document Content")`
        *   `st.checkbox("Make Private to Me")`
        *   `st.button("Upload Document")` -> Calls backend `/api/ingest/document` with selected `user_id`, content, name, context (current project/session), and privacy flag.
    *   **Output Display:** `st.text_area` or `st.json` to show responses from the backend API calls.
    *   **(Bonus) Verification View:** Maybe a button "Show DB Stats" that calls simple backend endpoints like `/api/stats/qdrant_count` or `/api/stats/neo4j_nodes` to confirm ingestion.

**V. Development Steps & Verification**

1.  **Setup:** Install tools, DBs. Create `twin_core_mock_data.py`.
2.  **Backend API Shell:** Build FastAPI app, define Pydantic models, basic endpoint structure.
3.  **DB Connection:** Add Qdrant/Neo4j client initialization.
4.  **Implement Seeding:** Build `/api/seed_data` endpoint and the core ingestion logic (embed -> Qdrant upsert -> Neo4j MERGE). Run it once.
5.  **Implement Ingestion Endpoints:** Build `/ingest/message` and `/ingest/document`.
6.  **Implement Retrieval Endpoints:** Build `/retrieve/context`, `/retrieve/private_memory`, `/query/user_preference`. Focus on correct filtering and data retrieval logic.
7.  **Build Streamlit UI:** Create the layout and widgets.
8.  **Connect UI <-> Backend:** Use `requests` in Streamlit button callbacks to hit FastAPI endpoints. Display results.
9.  **Test Scenarios:**
    *   Select Alice. Ask Twin "What did I say about cover art?". Verify personal doc retrieval.
    *   Ask Twin "What did Bob say about the roadmap?". Verify current session group chat retrieval *filtered by Bob*.
    *   Simulate Canvas Agent: "Get Session Context" for "Roadmap". Verify group chat messages from Alice, Bob, Charlie are returned.
    *   Simulate Canvas Agent: "Ask Twin Preference" for Alice about "Roadmap Priority". Verify it retrieves Alice's related statements (or lack thereof).
    *   Upload a new "Private Document" as Bob. Ask Twin (as Bob) about it. Verify retrieval. Ask Twin (as Alice) about it. Verify it's *not* retrieved.
    *   Verify twin chat history is ingested by asking the twin about something you just asked it.
10. **Iterate:** Debug and refine based on test results.
