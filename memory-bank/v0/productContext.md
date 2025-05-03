# TwinCore Prototype - Product Context

This document outlines the product goals, scope, features, and simulated context for the TwinCore backend prototype, derived from the PRD (`projectbrief.md`) and Separation Strategy.

**1. Core Goal:**

*   Demonstrate the Digital Twin backend's ability to ingest diverse data (simulated docs, chat) and fulfill the core API contract for context retrieval (group & private) and basic user preference representation, using Qdrant+Neo4j.
*   Validate the backend service (Dev B) for integration with the Canvas Agent (Dev A).

**2. Scope:**

*   **Simulated Entities:**
    *   3 Users: Alice, Bob, Charlie (IDs defined in `twin_core_mock_data.py`)
    *   2 Projects: "Book Generator Agent" (current), "Past Web Project" (historical)
    *   3 Sessions: Current Book Gen session, Past Book Gen session, Past Web session.
*   **Data:** Simulated historical documents and chat messages, plus data generated via API interactions during testing (uploads, chat).
*   **API Focus:** Implementation and testing of core `ingest` (`/message`, `/document`), `retrieve` (`/context`, `/private_memory`), and `query` (`/user_preference`) endpoints.
*   **UI:** A *minimal* Streamlit UI will be created solely for interaction and verification of the backend API during development. It is *not* the primary product focus.
*   **Out of Scope (Prototype):** Real external data connectors (GDrive, GCal), complex NLP/inference for preferences (start with retrieval), sophisticated UI, advanced governance features, performance optimization, user authentication (assume IDs are passed correctly).

**3. Core Features (Backend API Endpoints):**

*   `POST /api/seed_data`: Loads initial mock data into Qdrant/Neo4j.
*   `POST /api/ingest/message`: Ingests user/group/twin chat messages. Stores in Qdrant/Neo4j with metadata.
*   `POST /api/ingest/document`: Simulates file upload. Chunks text, stores in Qdrant/Neo4j with metadata (including privacy flag).
*   `POST /api/retrieve/context`: Simulates Canvas Agent request. Retrieves relevant public/group context for a given session/project based on query text.
*   `POST /api/retrieve/private_memory`: Simulates User->Twin chat/query. Retrieves context filtered *only* for the requesting user (and optional scope). Also ingests the user's query as a twin interaction.
*   `POST /api/query/user_preference`: Simulates Canvas Agent request. Retrieves past statements/data relevant to a user's preference on a specific topic within a context.

**4. Simulated Interaction Model (`separationStrategy.md`):**

*   **Canvas Agent (Dev A):** Expected to call TwinCore API endpoints for:
    *   Getting general context relevant to the current session/project (`/retrieve/context`).
    *   Getting a specific user's viewpoint or preference on a topic (`/query/user_preference`).
*   **User (via Minimal UI):**
    *   Can directly interact with their Twin (`/retrieve/private_memory` endpoint handles both retrieval and ingestion of the user query).
    *   Can simulate uploading documents (`/ingest/document`).
*   **Data Flow:** Canvas Agent events or user actions trigger API calls to TwinCore for ingestion or retrieval.

**5. Mock Data (`projectbrief.md` - `twin_core_mock_data.py`):**

*   Provides initial state for users, projects, sessions.
*   Includes sample document chunks and chat messages (historical and current) with varying context (personal, project-specific, session-specific).
*   Data includes timestamps and relevant IDs (`user_id`, `project_id`, `session_id`, `doc_id`, `message_id`).
*   Each data chunk has a unique `chunk_id` for Qdrant. 