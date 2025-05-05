# TwinCore Frontend (Streamlit Verification UI)

This directory contains a simple Streamlit application designed solely for testing and verifying the backend API endpoints of the TwinCore prototype.

**IMPORTANT:** This frontend is *not* part of the final product architecture. It acts as a simulator for the external "Canvas Agent" (Developer A) described in the project's `separationStrategy.md`, allowing Developer B (working on the TwinCore backend) to easily send requests and inspect responses without needing the actual Canvas Agent implementation.

## Purpose

*   **API Endpoint Testing:** Provide a user interface to manually trigger all major backend API endpoints (`/v1/ingest/*`, `/v1/retrieve/*`, `/v1/documents/*`, etc.).
*   **Data Flow Verification:** Simulate the different interaction patterns:
    *   Canvas Agent querying for session/project context.
    *   Canvas Agent querying for user preferences.
    *   User interacting directly with their Twin (querying private memory, which also triggers query ingestion).
    *   User uploading documents.
    *   Real-time system (simulated) sending transcript chunks and final metadata.
*   **Response Inspection:** Display the raw JSON responses from the backend API to verify correctness, filtering, and data structure.
*   **Ease of Development:** Offer a quick way to interact with the backend during development without relying on `curl` or other API tools for every test case.

## Key Simulated Features

Based on `tasks.md` (Phase 8), `vision_doc.md`, and `separationStrategy.md`, this UI simulates the following interactions that Developer A's system would initiate:

1.  **User Selection:** Choose which simulated user (Alice, Bob, Charlie from `mock_data.py`) is performing the action or being queried about.
2.  **Canvas Agent Simulation:**
    *   **Shared Context Retrieval (`GET /v1/retrieve/context`):** Input fields for `session_id` OR `project_id` (one required), and `query_text`. Button to trigger the API call. Simulates querying the general context of a session/project.
    *   **User Context Retrieval (`GET /v1/users/{user_id}/context`):** Input fields for `user_id` (selected user), `query_text`, and optional `session_id`/`project_id` for filtering. Button to trigger API call. *Simulates the core query needed for a twin agent to understand a specific user's perspective.*
    *   **User Preference Retrieval (`GET /v1/users/{user_id}/preferences`):** Input fields for `user_id` (selected user), `decision_topic`, and optional `project_id`/`session_id` filtering. Button to trigger the API call.
    *   **Group Context Retrieval (`GET /v1/retrieve/group`):** Input fields for `session_id` OR `project_id` OR `team_id` (one required), and `query_text`. Button to trigger API call. Simulates querying across all participants in a group.
3.  **Group Chat Simulation:**
    *   **Ingest Message (`POST /v1/ingest/message`):** Text area for typing a message. Button like "Send Group Message". This simulates a message sent by the selected `user_id` within the currently assumed `session_id` and `project_id`. It verifies the direct message ingestion pathway separate from twin interactions or document uploads.
4.  **User <> Twin Interaction:**
    *   **Private Memory (`POST /v1/users/{user_id}/private_memory`):** Text area for user's query. Button sends the query text and selected `user_id` to the backend. *Crucially verifies that this endpoint both returns private results AND ingests the user's query text as a twin interaction.* Input fields for optional `session_id`, `project_id` scoping.
5.  **Document Upload Simulation:**
    *   **Ingest Document (`POST /v1/ingest/document`):** Inputs for `doc_name`, `text` content, and an `is_private` checkbox. Button sends data with selected `user_id` and potentially current context IDs (session/project).
6.  **Transcript Simulation:**
    *   **Ingest Chunk (`POST /v1/ingest/chunk`):** Input for a persistent `doc_id` for the transcript. Text area for the utterance/chunk text. Button sends the chunk with selected `user_id`, `doc_id`, current context IDs (session/project), and timestamp.
    *   **Update Metadata (`POST /v1/documents/{doc_id}/metadata`):** Input for the `source_uri` where the final transcript is stored. Button sends the `doc_id` and `source_uri` to update the corresponding Document node in Neo4j.
7.  **Output Display:** A designated area (e.g., `st.json` or `st.text_area`) to show the complete JSON response received from the backend for the last executed API call.
8.  **(Optional) DB Stats Display:** Buttons to call simple backend admin endpoints (e.g., `/v1/stats/qdrant_count`, `/v1/stats/neo4j_nodes`) to get a quick count of records in the databases.

## How to Run

1.  Ensure the TwinCore backend FastAPI server is running.
2.  Navigate to this directory: `cd twincore_frontend`
3.  Create a virtual environment if necessary (you may already have one in root, sharing between frontend and backend):
    ```bash
    python -m venv venv
    source venv/bin/activate # or venv\Scripts\activate on Windows
    ```
4. Instll dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the Streamlit app:
    ```bash
    python -m streamlit run streamlit_app.py
    ``` 