# Splitting the Repo

The full project is outlined in [the vision doc](./vision_doc.md). This details how we will divide it between two people, Developer A vs Developer B.

**Core Architectural Idea:**

Treat the **Digital Twin Layer** as a distinct microservice (or a cohesive set of services) with a well-defined API. The **Canvas/Orchestration Layer** interacts with this service to fetch user-specific context, preferences, or to push new information for the twin to learn.

```mermaid
graph TD
    subgraph User Interaction Layer
        UI[Frontend Canvas (React, Yjs)]
    end

    subgraph Canvas & Orchestration (Dev A)
        RTB[Realtime Backend (Supabase + Yjs Sync)]
        OS[Orchestration Service (LangGraph, LLM Calls, Action Cortex)]
    end

    subgraph Digital Twin Layer (Dev B)
        DT_API[Digital Twin API (e.g., FastAPI/Flask)]
        DI[Data Ingestion Pipelines]
        DS[Data Stores (Qdrant, Neo4j, Postgres)]
    end

    UI <--> RTB;
    RTB --> OS[Triggers OS on events];
    UI -- Direct Commands --> OS;

    OS -- Needs Twin Info --> DT_API;
    OS -- Logs Actions --> Governance[Governance Hub - Logging];

    RTB -- Pushes Events/Data --> DT_API; # Option 1: Direct Push
    RTB -- Publishes Events --> EventBus[(Optional Event Bus)]; # Option 2: Decoupled
    EventBus --> DI;
    DI -- Stores Data --> DS;

    DT_API -- Queries/Updates --> DS;
    DT_API -- Gets Twin Info --> OS;

    Governance -- Reads Logs --> OS;
    Governance -- Reads Preferences/Votes --> DT_API; # Governance might need data from both
```

**Developer A (Clovis): Canvas & Orchestration**

*   **Focus:** User experience on the canvas, real-time collaboration, core agentic workflows, triggering actions.
*   **Primary Components:**
    *   **Frontend Canvas (UI):** React, Vite, Yjs client integration. Building the visual components, handling user input, displaying real-time updates.
    *   **Realtime Backend (RTB):** Supabase setup, Yjs server-side integration/persistence, managing session presence, basic user authentication flow. Handling WebSocket connections. Broadcasting canvas state changes.
    *   **Orchestration Service (OS):** Python service (e.g., FastAPI, Flask) hosting LangGraph agents. Receives triggers from RTB (e.g., user typed `/make_diagram`) or direct UI commands. Parses commands, interacts with LLMs (OpenAI/Anthropic), makes calls to the `Digital Twin API` for context/preferences, and triggers actions via the `Action Cortex`.
    *   **Action Cortex:** Simple plugins/functions called by the OS (e.g., `schedule_meeting`, `post_to_slack`, `generate_summary_doc`). Initially, these might live within the OS.
    *   **Basic Governance Logging:** Implementing the logging of *actions taken* by the Orchestration Service.
*   **Key Tasks:**
    *   Build out canvas UI elements and interactivity.
    *   Set up and manage Supabase for real-time sync and basic data (users, sessions).
    *   Define main LangGraph flows for core features (diagram generation, summarization).
    *   Integrate LLM calls within LangGraph.
    *   Develop the client-side logic to *call* the Digital Twin API (initially perhaps against a mocked version).
    *   Define and implement the specific requests the OS needs to make to the Digital Twin API (e.g., `get_user_preferences`, `find_relevant_context`).
    *   Build initial Action Cortex integrations.
    *   Handle basic deployment/hosting for these components.

**Developer B (Connie): Digital Twin Layer**

*   **Focus:** User memory persistence, multi-modal data ingestion (probably v2), complex retrieval logic, preference tracking, representing user state/knowledge.
*   **Primary Components:**
    *   **Digital Twin API (DT_API):** A dedicated service (e.g., FastAPI/Flask) that exposes endpoints for the Orchestration Service (and potentially the Frontend for whispers). This is the main interface.
    *   **Data Stores (DS):** Managing the schemas, setup, and interaction logic for Qdrant, Neo4j, and the relevant parts of Postgres.
    *   **Data Ingestion Pipelines (DI):** Scripts/connectors/listeners responsible for pulling data from sources (Google Drive, Calendar, chat messages passed via API/Event Bus, document uploads) and processing/embedding/storing it correctly in the Data Stores.
    *   **Retrieval Logic:** Implementing the core query functions within the DT_API that combine semantic search (Qdrant) with relationship traversal (Neo4j) and structured data lookup (Postgres) based on API request parameters (user\_id, session\_id, project\_id, etc.).
    *   **Preference/Voting Logic:** Storing, updating, and querying explicit/implicit preferences and votes.
    *   **Advanced Governance Queries:** Enabling queries about *why* a twin might recommend something, based on stored preferences/history.
*   **Key Tasks:**
    *   **Define the Digital Twin API Contract (Critical):** Specify precise endpoints, request parameters (scopes like user\_id, session\_id, project\_id), and response formats (e.g., using OpenAPI/Swagger). Examples below.
    *   Set up and configure Qdrant and Neo4j databases.
    *   Implement robust data ingestion pipelines for various sources. Handle parsing, chunking, embedding generation, and storage with correct metadata/relationships.
    *   Write the core query logic within the API service combining Qdrant, Neo4j, Postgres.
    *   Implement storage and retrieval for preferences and votes.
    *   Ensure data security and privacy within the twin layer.
    *   Develop testing strategies for retrieval accuracy and ingestion pipelines.
    *   Handle deployment/hosting for the Digital Twin Service and its databases.

**Key API Contract: Digital Twin API (Examples)**

*(Endpoints Dev B builds, Dev A calls. NOTE: These examples illustrate the core interactions. Formal Pydantic models should be defined in `api/models.py` for robust validation. Authentication/Authorization via tokens will be necessary.)*

**IMPORTANT**: See [api.md](./api.md) for the detailed api.

*   `POST /v1/ingest/message`
    *   Body: `{ "user_id": "uuid", "session_id": "uuid", "project_id": "uuid" (optional, can be derived from session), "message_id": "uuid" (optional, source system ID), "message_text": "...", "timestamp": "isoformat", ... }`
    *   Action: Ingests the message, creates embeddings, stores in Qdrant, updates Neo4j relationships. Requires `user_id` and `session_id`.
*   `POST /v1/ingest/document`
    *   Body: `{ "user_id": "uuid", "doc_id": "uuid", "project_id": "uuid | null", "session_id": "uuid | null", "text": "...", "metadata": {...}, ... }`
    *   Action: Ingests document. Requires `user_id` and `doc_id`. Requires at least one of `project_id` or `session_id` to provide context. Document text will be chunked by this service.
*   `GET /v1/retrieve/context`
    *   Params: `user_id=uuid`, `session_id=uuid | null`, `project_id=uuid | null`, `query=str`, `limit=int`
    *   Action: Performs combined Qdrant/Neo4j search based on scope and semantic query. Requires `user_id`.
    *   Response: `[{ "chunk_id": "uuid", "text": "...", "score": float, "metadata": {"source_doc_id": "uuid", ...} }, ...]` (Structure defined by Pydantic model).
*   `GET /v1/retrieve/preferences`
    *   Params: `user_id=uuid`, `project_id=uuid | null`, `topic=str | null`
    *   Action: Queries Neo4j/Postgres/Qdrant for explicit preferences or relevant voting history. Requires `user_id`.
    *   Response: `{ "explicit": [...], "inferred_from_votes": [...], "relevant_statements": [...] }` (Structure defined by Pydantic models).
*   `GET /v1/retrieve/group`
    *   Params: Exactly one of `session_id=uuid` OR `project_id=uuid` OR `team_id=uuid`, plus `query=str` and optional `metadata`.
    *   Action: Queries Neo4j/Qdrant across participants in the specified scope to find relevant experience, preferences, or memories; the filtering can be in the `metadata`.
    *   Response: `[{ "user_id": "uuid", "results": [{ "chunk_id": "uuid", ... }] }, ...]` (Structure defined by Pydantic models).


**Workflow & Communication:**

1.  **API Definition First:** Agree on the initial Digital Twin API contract ASAP. Dev B can provide a mock server (e.g., using FastAPI's built-in features or tools like Prism) for Dev A to build against while Dev B implements the real logic.
2.  **Shared IDs:** Use consistent UUIDs for users, projects, sessions, etc. Supabase (managed by Dev A) can be the source of truth for creating these entities initially. Dev B's service will reference these IDs.
3.  **Ingestion Path:** Decide if the RTB/OS will push data directly to the DT\_API (`POST /ingest/...`) or if you'll use an event bus (more decoupled, slightly more complex setup). For simplicity, direct API calls might be easier initially.
4.  **Regular Syncs:** Hold brief daily or bi-weekly syncs specifically focused on the API interface, any blocking issues, and shared data assumptions.
5.  **Documentation:** Maintain clear documentation for the Digital Twin API.

This separation allows Dev A to focus on the immediate user interactions and agent flows, while Dev B dives deep into the complex data management and retrieval logic powering the personalized twin experience. The API becomes the crucial boundary ensuring both can progress effectively.