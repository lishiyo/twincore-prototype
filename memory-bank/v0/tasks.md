# TwinCore Prototype - Task Breakdown (TDD Focused)

This document outlines the development tasks for building the TwinCore backend prototype, emphasizing a Test-Driven Development (TDD) approach as defined in `testingStrategy.md`.

**Legend:**
*   `(D)`: Dependency Task ID(s)
*   `[TDD Layer]`: Indicates the primary testing focus for the task step (Unit, DAL Int, Service Int, API/Contract, E2E).

---

## Phase 1: Setup & Core Structure

- [x] **Task 1.1: Project Initialization**
    - [x] Steps:
        - [x] Create project directory (`twincore_backend`).
        - [x] Initialize Python environment (`venv`).
        - [x] Create `requirements.txt` (FastAPI, Uvicorn, python-dotenv, Pydantic).
        - [x] Create `.gitignore`.
        - [x] Set up basic FastAPI app structure (`main.py`, `api/`, `services/`, `dal/`, `core/`, `tests/`).
        - [x] Create `core/config.py` (e.g., using `pydantic-settings`).
        - [x] Create `main.py` with root `/` endpoint.
        - [x] [API/Contract] Write basic API test for `/` endpoint in `tests/test_main.py`. Implement endpoint to pass.
    - [x] Dependencies: None

- [x] **Task 1.2: Testing Setup** (D: 1.1)
    - [x] Steps:
        - [x] Add testing dependencies to `requirements.txt` (`pytest`, `pytest-asyncio`, `httpx`, `pytest-mock`, `pytest-cov`, `schemathesis`). Install.
        - [x] Create `pytest.ini`.
        - [x] Create basic test fixtures (e.g., `httpx` client in `tests/conftest.py`).
        - [x] Ensure Task 1.1 test runs via `pytest`.

- [x] **Task 1.3: Docker Setup for Databases**
    - [x] Steps:
        - [x] Create `docker-compose.yml` for Qdrant & Neo4j dev instances.
        - [x] Create `docker-compose.test.yml` (or profiles) for isolated test DB instances.
        - [x] Document basic `docker-compose` usage in README.
    - [x] Dependencies: None

---

## Phase 2: Core Data Models & DB Setup

- [x] **Task 2.1: Pydantic API Models**
    - [x] Steps:
        - [x] Define core Pydantic models in `api/models.py` based on `dataSchema.md` & `projectbrief.md`.
    - [x] Dependencies: None

- [x] **Task 2.2: Database Client Initialization** (D: 1.1, 1.3)
    - [x] Steps:
        - [x] Add `qdrant-client`, `neo4j` to `requirements.txt`. Install.
        - [x] Implement client initialization in `core/db_clients.py`, reading from config.
        - [x] [Unit] Write unit tests mocking config to verify client initialization.

- [x] **Task 2.3: Qdrant Collection Setup** (D: 1.3, 2.2)
    - [x] Steps:
        - [x] Implement utility in `core/db_setup.py` to create `twin_memory` collection via client.
        - [x] [DAL Int] Write integration test using test Qdrant instance to verify collection creation & cleanup.

- [x] **Task 2.4: Neo4j Constraints Setup** (D: 1.3, 2.2)
    - [x] Steps:
        - [x] Implement utility in `core/db_setup.py` to create uniqueness constraints via driver.
        - [x] [DAL Int] Write integration test using test Neo4j instance to verify constraint creation & cleanup.

---

## Phase 3: Embedding & Core Ingestion Logic

- [x] **Task 3.1: Embedding Service** (D: 1.1)
    - [x] Steps:
        - [x] Add openai to `requirements.txt` for the embedding model. Install.
        - [x] Create `services/embedding_service.py`.
        - [x] Implement `EmbeddingService` class (loads model from config, `get_embedding` method).
        - [x] [Unit] Write unit tests mocking model loading, verify method signature and error handling.

- [x] **Task 3.2: DAL Interfaces (ABCs/Protocols)**
    - [x] Steps:
        - [x] Define interfaces in `dal/interfaces.py` (`IQdrantDAL`, `INeo4jDAL`) outlining core methods.
    - [x] Dependencies: None

- [x] **Task 3.3: Neo4j DAL Implementation (Core)** (D: 1.3, 2.2, 2.4, 3.2)
    - [x] Steps:
        - [x] Create `dal/neo4j_dal.py` implementing `INeo4jDAL`.
        - [x] Implement `create_node_if_not_exists`, `create_relationship_if_not_exists` using Cypher MERGE/CREATE.
        - [x] [DAL Int] Write integration tests against test Neo4j: test node/relationship creation, properties, idempotency, cleanup.

- [x] **Task 3.4: Qdrant DAL Implementation (Core)** (D: 1.3, 2.2, 2.3, 3.2)
    - [x] Steps:
        - [x] Create `dal/qdrant_dal.py` implementing `IQdrantDAL`.
        - [x] Implement `upsert_vector`, basic `search_vectors`.
        - [x] [DAL Int] Write integration tests against test Qdrant: test upsert, payload verification, basic search, cleanup.
        - [x] Implement `delete_vectors`.
        - [x] [DAL Int] Write integration tests against test Qdrant: test delete, verification, cleanup.

- [x] **Task 3.5: Ingestion Service (Core Logic)** (D: 3.1, 3.3, 3.4)
    - [x] Steps:
        - [x] Create `services/ingestion_service.py`. Implement `IngestionService` taking DALs/EmbeddingService dependencies.
        - [x] Implement internal helpers (`_prepare_qdrant_point`, `_update_neo4j_graph`).
        - [x] [Service Int] Write integration tests mocking DAL/Embedding interfaces, verify correct DAL methods are called with expected args for given inputs.

---

## Phase 4: Seeding Endpoint (`/api/seed_data`)

- [x] **Task 4.1: Mock Data Module**
    - [x] Steps:
        - [x] Create `core/mock_data.py` based on [PRD](./projectbrief.md).
    - [x] Dependencies: None

- [x] **Task 4.2: Seeding Logic in Data Seeder Service** (D: 3.5, 4.1)
    - [x] Steps:
        - [x] Create a dedicated `DataSeederService` class to handle seeding operations
        - [x] Implement `seed_initial_data()` method to load mock data from `core/mock_data.py`
        - [x] Use dependency injection with the `IngestionService` to process data
        - [x] [Service Int] Create comprehensive tests for `DataSeederService`

- [x] **Task 4.3: Seeding API Endpoint** (D: 1.1, 4.2)
    - [x] Steps:
        - [x] Create `api/routers/admin_router.py`. Define `POST /api/seed_data`. Inject `DataSeederService` via `Depends`. Call `seed_initial_data()`. Register router in `main.py`. Review [api.md](./api.md) for the expected API contract.
        - [x] [API/Contract] Write API test asserting 200 OK.
        - [x] Create endpoint to clear out all data. That lets us revert the `seed_initial_data`.
        - [x] [API/Contract] Write API test asserting 200 OK.

- [x] **Task 4.4: Seeding End-to-End Test** (D: 1.3, 2.2, 4.3)
    - [x] Steps:
        - [x] [E2E] Write E2E test using `HTTPX` and real test DBs. Call `/api/seed_data`. Directly query test Qdrant/Neo4j to verify data integrity.

---

## Phase 5: Ingestion Endpoints (`/api/ingest/*`)

- [x] **Task 5.1: Ingest Message Endpoint** (D: 2.1, 3.5, 4.4)
    - [x] Steps:
        - [x] Add MessageConnector with `ingest_message(data)` logic.
        - [x] Create `api/routers/ingest_router.py`. Define `POST /ingest/message`. Use Pydantic models. Inject service. Register router.
        - [x] [TDD Steps]:
            - [x] [Service Int] Test `ingest_message` logic.
            - [x] [API/Contract] Test endpoint schema/status.
            - [x] [E2E] Call endpoint, verify data in Qdrant/Neo4j.

- [x] **Task 5.2: Ingest Document Endpoint** (D: 2.1, 3.5, 5.1)
    - [x] Steps:
        - [x] Implement basic text chunking logic in `ingestion/processors`.
        - [x] Add DocumentConnector, add `ingest_document(data)` including chunking & handling `is_private`.
        - [x] Define `POST /ingest/document` endpoint in `ingest_router.py`.
        - [x] [TDD Steps]:
            - [x] [Unit] Test chunking logic.
            - [x] [Service Int] Test `ingest_document` logic.
            - [x] [API/Contract] Test endpoint schema/status.
            - [x] [E2E] Call endpoint, verify doc node, chunks, relationships, `is_private` flag propagation.
              * **Note:** Current E2E test (`test_document_ingestion_end_to_end`) is failing with `AssertionError: No document chunks found in Qdrant` after test isolation changes.

---

## Phase 6: Retrieval Endpoints (`/v1/retrieve/*`)

- [x] **Task 6.1: Retrieval Service & DAL Methods** (D: 3.3, 3.4, Phase 4)
    - [x] Steps:
        - [x] Define & Implement retrieval methods in `dal/interfaces.py`, `dal/neo4j_dal.py`, `dal/qdrant_dal.py` (e.g., get_session_participants, get_project_context, get_related_content, get_content_by_topic, search_with_filters). Focus on filter logic.
        - [x] [TDD Steps]:
            - [x] [DAL Int] Test retrieval methods against test DBs (filtering, scoring, limits).
            - [x] [Service Int] Implement `RetrievalService`, mock DALs, test logic combining search results.
            - [x] [API/Contract] Test endpoint schema/status for `/v1/retrieve/*` endpoints.
            - [x] [E2E] Call endpoints, verify correct filtered data is retrieved from Qdrant/Neo4j.

- [x] **Task 6.2: Context Retrieval Endpoint (`/v1/retrieve/context`)** (D: 2.1, 6.1)
    - [x] Steps:
        - [x] Implement `retrieve_context(data)` and `retrieve_enriched_context(data)` logic in `RetrievalService`.
        - [x] Define `GET /v1/retrieve/context` endpoint in `retrieve_router.py` (with `include_graph` flag). Use Pydantic models. Inject RetrievalService. Register router.
        - [x] [TDD Steps]:
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [x] [E2E] Test scenario simulating Canvas Agent call, verify group context retrieval.

- [x] **Task 6.3: Private Memory Retrieval Endpoint (`/v1/retrieve/private_memory`)** (D: 2.1, 5.1, 6.1)
    - [x] Steps:
        - [x] Implement dual logic in the endpoint: ingest query via MessageConnector, then retrieve via RetrievalService with strict user/privacy filtering.
            - [x] Implement `retrieve_private_memory(data)` logic in `RetrievalService`.
            - [x] **Important:** Ensure this service method *also* calls `MessageConnector.ingest_message` to store the user's query as a twin interaction (as per `projectbrief.md`).
        - [x] Define `POST /v1/retrieve/private_memory` endpoint in `retrieve_router.py` (with `include_graph` flag).
        - [x] [TDD Steps]:
            - [x] [Service Int] Test combined retrieval + ingestion logic for private memory.
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [x] [E2E] Test scenario simulating User->Twin call, verify private filtering AND query ingestion.
            - [x] [E2E] Seed public/private data, call endpoint as different users, verify query ingestion AND correct data/privacy filtering in results.

- [x] **Task 6.4: Related Content Retrieval Endpoint (`/v1/retrieve/related_content`)** (D: 2.1, 6.1)
    - [x] Steps:
        - [x] Implement `retrieve_related_content(data)` logic in `RetrievalService`.
        - [x] Define `GET /v1/retrieve/related_content` endpoint in `retrieve_router.py`. Use Pydantic models. Inject RetrievalService.
        - [x] [TDD Steps]:
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [x] [E2E] Test scenario retrieving related content via graph traversal.

- [x] **Task 6.5: Topic Retrieval Endpoint (`/v1/retrieve/topic`)** (D: 2.1, 6.1)
    - [x] Steps:
        - [x] Implement `retrieve_by_topic(data)` logic in `RetrievalService`.
        - [x] Define `GET /v1/retrieve/topic` endpoint in `retrieve_router.py`. Use Pydantic models. Inject RetrievalService.
        - [x] [TDD Steps]:
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [x] [E2E] Test scenario retrieving content by topic.

---

## Phase 7: Preference Endpoint (`/v1/retrieve/user_preference`)

- [x] **Task 7.1: Preference Service & DAL Methods** (D: 3.3, 3.4, Phase 4)
    - [x] Steps:
        - [x] Define & Implement necessary DAL methods for finding user statements/messages related to a topic (querying past statements/data) in `dal/qdrant_dal.py` and `dal/neo4j_dal.py`. *Note: Relies on existing data/embeddings for prototype; explicit Preference nodes are phase 9.* 
        - [x] Create `services/preference_service.py`. Implement `PreferenceService` taking DAL dependencies.
        - [x] Implement `query_user_preference(data)` logic in `PreferenceService`.
        - [x] [TDD Steps]:
            - [x] [DAL Int] Test preference retrieval queries against test DBs with seeded relevant data.
            - [x] [Service Int] Implement `PreferenceService`, mock DALs, test logic for interpreting/returning preferences.

- [x] **Task 7.2: Preference API Endpoint** (D: 2.1, 7.1)
    - [x] Steps:
        - [x] Define the API endpoint structure for preference retrieval (using Pydantic models) in a relevant router (e.g., `retrieve_router.py` or a new `query_router.py`). Ensure it aligns with the final API spec (`GET /v1/retrieve/preferences`). Inject the service. Register router.
        - [x] [TDD Steps]:
            - [x] [API/Contract] Test endpoint schema/status.

- [x] **Task 7.3: Preference End-to-End Test** (D: 7.2, Phase 4)
    - [x] Steps:
        - [x] [E2E] Write E2E test simulating Canvas Agent call. Call endpoint, verify relevant past statements/data are returned based on seeded mock data.
        - [x] Ingest real data, call endpoint, verify responses look correct.
        - [x] Debug and fix E2E test failures related to status codes, request payloads, fixture overrides, async timing, and vector search thresholds.

- [x] **Task 7.4: Refine Twin Interaction Filtering** (D: 7.1, 7.2, 7.3)
    - [ ] Steps:
        - [x] Modify `QdrantDAL.search_vectors` and `QdrantDAL.search_user_preferences` to accept `include_twin_interactions: bool` parameter (instead of `exclude_twin_interactions`) and update filtering logic.
        - [x] Modify `RetrievalService` and `PreferenceService` methods to accept the new flag (e.g., `include_messages_to_twin`) and pass it to DAL methods. Adjust default behavior based on endpoint purpose (True for preferences/private memory, False otherwise).
        - [x] Modify relevant API endpoints (`/context`, `/preferences`, `/private_memory`, `/group`, `/timeline`) to accept the `include_messages_to_twin` parameter (in query or body) with appropriate defaults as specified in `api.md`.
        - [x] Update Pydantic models if necessary for the new parameter (e.g., in `PrivateMemoryQuery`).
        - [x] [TDD - DAL] Update Qdrant DAL tests to verify filtering behavior with `include_twin_interactions=True` and `include_twin_interactions=False`.
        - [x] [TDD - Service] Update Service tests to verify the flag is passed correctly to DAL mocks.
        - [x] [TDD - API/Contract] Update API tests to verify the new parameter, its defaults, and schema validation.
        - [x] [TDD - E2E] Update relevant E2E tests (e.g., for private memory, context, preferences) to specifically test scenarios with both `include_messages_to_twin=True` and `include_messages_to_twin=False` to ensure correct filtering.

- [ ] **Task 7.5: Implement Transcript Ingestion Strategy** (D: 2.1, 3.3, 3.4, 3.5)
    - [ ] Steps:
        - [x] **Sub-task 7.5.1: Update Neo4j DAL for Document Metadata**
            - [x] Add `source_uri` property handling to `Document` node creation/update methods in `dal/neo4j_dal.py`.
            - [x] Add new method `update_document_metadata(doc_id, source_uri=None, metadata=None)` to update existing document nodes.
            - [x] [DAL Int] Write/update integration tests to verify `source_uri` and metadata updates on `Document` nodes.
        - [x] **Sub-task 7.5.2: Implement Chunk Ingestion Logic**
            - [x] Add `ingest_chunk(data)` method to `ingestion/connectors/document_connector.py` (or a new `transcript_connector.py`).
            - [x] Logic should ensure parent `Document` node exists in Neo4j (creating if first chunk via DAL call) and upsert chunk to Qdrant via DAL.
            - [x] [Service Int] Test `ingest_chunk` logic in isolation, mocking DAL calls.
        - [x] **Sub-task 7.5.3: Implement Chunk Ingestion API Endpoint (`/v1/ingest/chunk`)**
            - [x] Define `POST /v1/ingest/chunk` endpoint in `api/routers/ingest_router.py`. Use Pydantic models. Inject relevant connector/service.
            - [x] [API/Contract] Write API test verifying endpoint schema, request/response, status code.
            - [x] [E2E] Write E2E test: Call `/v1/ingest/chunk` multiple times for the same `doc_id`, verify chunks in Qdrant with correct metadata and the parent `Document` node in Neo4j.
        - [x] **Sub-task 7.5.4: Implement Document Metadata Update API Endpoint (`/v1/documents/{doc_id}/metadata`)**
            - [x] Add `update_document_metadata` method to neo4j_dal.
            - [x] Define `POST /v1/documents/{doc_id}/metadata` endpoint in a relevant router (e.g. `document_router.py`).
            - [x] Add service logic (e.g., in `DataManagementService` or `IngestionService`) to call the new `neo4j_dal.update_document_metadata` method.
            - [x] [Service Int] Test service logic for metadata updates, mocking DAL.
            - [x] [API/Contract] Write API test verifying endpoint schema, path parameter, request/response, status code.
            - [x] [E2E] Write E2E test: Create a document via ingestion, then call `/v1/documents/{doc_id}/metadata` to update `source_uri`, verify change in Neo4j.

- [x] **Task 7.6: Implement User and Group Context Retrieval** (D: 2.1, 6.1)
    - [x] Steps:
        - [x] **Sub-task 7.6.1: Implement User Context Endpoint (`GET /v1/users/{user_id}/context`)**
            - [x] Implement service logic in `RetrievalService` to fetch all relevant context for a single user, respecting scope and `include_messages_to_twin` (default True) and `include_private` (default True).
            - [x] Define API endpoint in a relevant router (e.g., `user_router.py`), see [api.md](./api.md) for spec.
            - [x] Write API/Contract tests.
            - [x] Write Service Integration tests.
            - [x] Write E2E tests verifying comprehensive user context retrieval.
        - [x] **Sub-task 7.6.2: Implement Group Context Endpoint (`GET /v1/retrieve/group`)**
            - [x] Implement service logic in `RetrievalService` to fetch context for multiple users based on group scope (session, project, team), respecting filters and grouping results.
            - [x] Define API endpoint in `retrieve_router.py`,  see [api.md](./api.md) for spec.
            - [x] Write API/Contract tests.
            - [x] Write Service Integration tests.
            - [x] Write E2E tests verifying group context retrieval across participants.

- [x] **Task 7.7: Refactor Preference Endpoint** (D: Phase 7 completion)
    - [ ] Steps:
        - [x] **Sub-task 7.7.1: Refactor Preference Endpoint Path & Parameters**
            - [x] Move endpoint from `GET /v1/retrieve/preferences`  (currently in `retrieval_router.py`) to `GET /v1/users/{user_id}/preferences` (use `user_router.py`).
            - [x] Update router definition, changing `user_id` from query param to path param.
            - [x] Update service method signature if needed.
            - [x] Update OpenAPI documentation (`/docs`).
            - [x] **Crucially:** Update ALL existing tests (Unit, Integration, API, E2E) for the preference endpoint to use the new path and parameter structure.
        - [x] **Sub-task 7.7.2: Refactor Private Memory Endpoint Path & Parameters**
            - [x] Move endpoint from `POST /v1/retrieve/private_memory` (in `retrieve_router.py`) to `POST /v1/users/{user_id}/private_memory` (in `user_router.py`).
            - [x] Update router definition, changing `user_id` from the request body to a path parameter. Update the request body model (`PrivateMemoryQuery`) accordingly.
            - [x] Update service method signature if needed.
            - [x] Update OpenAPI documentation (`/docs`).
            - [x] Update all relevant tests (Unit, Integration, API, E2E) for the private memory endpoint.
            - [x] Remove the old endpoint and associated tests from `retrieve_router.py`.
            - [x] Update all references (e.g. in the markdown files) from `/v1/retrieve/private_memory` to `/v1/users/{user_id}/private_memory`.

---

## Phase 8: Verification UI (Streamlit)

**Critical**: This Streamlit frontend MUST be completely encapsulated from our backend, because we are only using it for development (the real frontend will be a separate repo). Essentially, we will use this to simulate the calls that the real external client (Developer A in [separationStrategy](./separationStrategy.md)) would mamke.

- [x] **Task 8.1: Streamlit App Setup** (D: 1.1)
    - [x] Steps:
        - [x] Create new `twincore_frontend` folder, create `streamlit_app.py`.
        - [x] Add `streamlit`, `requests` to `requirements.txt`. Install.
        - [x] Basic app structure and title.
        - [x] Add README.md to explain how this frontend works, all its expected features and use case flows, and how to run it.

- [x] **Task 8.2: UI Layout & Components** (D: 8.1)
    - [x] Steps:
        - [x] Implement User Selector (`st.selectbox`).
        - [x] Implement Canvas Agent Simulation section:
            - [x] Inputs/Button for Shared Context (`GET /v1/retrieve/context`).
            - [x] Inputs/Button for User Context (`GET /v1/users/{user_id}/context`).
            - [x] Inputs/Button for User Preference (`GET /v1/users/{user_id}/preferences`).
            - [x] Inputs/Button for Group Context (`GET /v1/retrieve/group`).
        - [x] Implement Group Chat Simulation section:
            - [x] Text area/Button for sending group messages (`POST /v1/ingest/message`).
        - [x] Implement User <> Twin Interaction section (text area, button).
        - [x] Implement Document Upload Simulation section (text inputs, checkbox, button).
        - [x] Implement **Transcript Simulation Section:**
            - [x] Text input for `doc_id` (to represent the ongoing transcript).
            - [x] Text area for entering utterance chunks.
            - [x] Button like "Send Utterance Chunk".
            - [x] Button like "Finalize Transcript & Add URI" (requires input for URI).
        - [x] Implement Output Display area (`st.text_area` or `st.json`).

- [x] **Task 8.3: Backend API Integration** (D: 4.3, 5.1, 5.2, 6.2, 6.3, 7.2, 8.2)
    - [x] Steps:
        - [x] Add `requests` calls within button callbacks to hit the corresponding backend API endpoints:
            - [x] `GET /v1/retrieve/context` (Shared Context)
            - [x] `GET /v1/users/{user_id}/context` (User Context)
            - [x] `GET /v1/users/{user_id}/preferences` (User Preference)
            - [x] `GET /v1/retrieve/group` (Group Context)
            - [x] `POST /v1/ingest/message` (Group Message)
            - [x] `POST /v1/users/{user_id}/private_memory` (User/Twin Interaction, should ingest message and return user's private context)
            - [x] `POST /v1/ingest/document` (Document text Upload)
        - [x] Add `requests` call for "Send Utterance Chunk" button to hit `POST /v1/ingest/chunk` with `doc_id`, selected user, utterance text, session context.
        - [x] Add `requests` call for "Finalize Transcript" button to hit `POST /v1/documents/{doc_id}/metadata` with `doc_id`, `source_uri` input, etc.
        - [x] Pass appropriate data (selected user ID, text inputs, context IDs) to the API calls.
        - [x] Display API responses in the Output Display area.

- [x] **Task 8.4: DB Stats Display** (D: 8.3, potentially new admin endpoints)
    - [x] Steps:
        - [x] Create backend endpoints in `admin_router.py` to return counts from Qdrant/Neo4j (e.g., `/v1/admin/api/stats/qdrant`, `/v1/admin/api/stats/neo4j`). Test these endpoints.
        - [x] Implement DAL methods for retrieving node/relationship counts and collection info.
        - [x] Add service methods to get and format database statistics.
        - [x] Update the Streamlit UI to call these endpoints and display the results in a user-friendly format.

---

## Phase 9: Knowledge Extraction & Deduplication

*Note: This phase focuses on enriching the knowledge graph by extracting entities (Topics, Preferences, etc.) and relationships directly from text content using an LLM, and ensuring content uniqueness.*

- [ ] **Task 9.0: Implement Content Deduplication** (D: Phase 1-7)
    - **Goal:** Prevent storing duplicate content chunks (identical text from the same user via the same source type) in Qdrant and Neo4j.
    - **Strategy:** Generate a deterministic `chunk_id` based on a hash (e.g., SHA-256) of the `user_id`, `source_type`, and the `text_content`. Use this deterministic ID as the point ID in Qdrant and the `chunk_id` property for `:Chunk` nodes in Neo4j. Qdrant's `upsert` and Neo4j's `MERGE` operations will handle the actual deduplication automatically based on this consistent ID.
    - [ ] Steps:
        - [ ] **Sub-task 9.0.1: Implement Deterministic ID Generation**
            - [ ] Create a utility function (e.g., `generate_deterministic_chunk_id(user_id, source_type, text_content)`) potentially in `core/utils.py`.
            - [ ] [TDD - Unit] Write unit tests for this function to ensure it produces consistent output for the same input and different output for different inputs.
        - [ ] **Sub-task 9.0.2: Update `IngestionService`**
            - [ ] Modify `IngestionService.ingest_chunk` to call the deterministic ID generation function.
            - [ ] Ensure this generated ID is used when calling `_prepare_qdrant_point` (as the point ID) and `_update_neo4j_graph` (as the `chunk_id` parameter).
            - [ ] [TDD - Service Int] Update `IngestionService` tests to mock the ID generation and verify the correct ID is passed to DAL mocks.
        - [ ] **Sub-task 9.0.3: Refactor Connectors**
            - [ ] Modify `MessageConnector.ingest_message` to stop generating a random UUID for the chunk. It should pass the core data to `IngestionService.ingest_chunk`.
            - [ ] Modify `DocumentConnector.ingest_document` (specifically the loop creating chunks) and `DocumentConnector.ingest_chunk` to stop generating random UUIDs for chunks. They should pass core data to `IngestionService.ingest_chunk`.
            - [ ] [TDD - Service Int] Update Connector tests to verify they no longer generate random chunk IDs and correctly call `IngestionService`.
        - [ ] **Sub-task 9.0.4: Verify Deduplication (Testing)**
            - [ ] [TDD - E2E] Write specific E2E tests:
                - Ingest the *exact same message text* from the *same user* via `POST /v1/ingest/message` twice. Verify only one Qdrant point and one Neo4j `:Chunk` node exist with the correct deterministic ID.
                - Ingest the *exact same query text* from the *same user* via `POST /v1/users/{user_id}/private_memory` twice. Verify only one Qdrant point and one Neo4j `:Chunk` node exist for the *query itself* (source_type='query').
                - Ingest a message via `/ingest/message`, then ingest the *same text* as a query via `/private_memory`. Verify *two* distinct points/nodes exist (because `source_type` differs: 'message' vs. 'query').

- [ ] **Task 9.1: Knowledge Extraction Service - Design & Prompt Engineering** (D: 1.1, `dataSchema.md` finalized)
    - **Goal:** Design and refine LLM prompts to reliably extract structured knowledge (entities and relationship hints) from text chunks, and implement the core service logic.
    - [ ] Steps:
        - [ ] **Sub-task 9.1.1: Define Structured Output Schema:**
            - Formalize the expected JSON output structure from the LLM. This structure should include:
                - A list of extracted entities.
                - Each entity having a `temp_id` (for batch processing), `entity_type` (e.g., 'ActionItem', 'Risk', 'Topic'), a `properties` dictionary (with extracted text, status hints, etc.), and a `relationships` list.
                - Each relationship dictionary specifying `type` (e.g., 'ASSIGNED_TO', 'RELATES_TO', 'MENTIONS', 'ADDRESSES'), `target_type` (e.g., 'User', 'Project', 'Topic'), and either `target_hint` (for external entities like 'Bob', 'Project Y') or `target_temp_id` (for linking to another entity within the same LLM output batch).
            - Document this schema clearly for prompt engineering and parsing.
        - [ ] **Sub-task 9.1.2: Develop & Test Prompts:**
            - Create a dedicated test script (e.g., `scripts/test_extraction_prompts.py`) to iterate on prompt design.
            - Include diverse examples covering:
                - Simple entity extraction (Decision, ActionItem, etc.).
                - Entities with associated targets (ActionItem assigned to User, Risk related to Project/Topic).
                - Implicit relationships (ActionItem addressing a previously mentioned Risk).
                - Ambiguous mentions.
            - The script should call the target LLM (e.g., Gemini) with the prompt and sample text, then validate if the returned JSON conforms to the defined schema (Sub-task 9.1.1) and if the extracted entities/relationships are semantically correct for the input text.
            - Refine prompts based on test results until achieving acceptable accuracy and consistency.
        - [ ] **Sub-task 9.1.3: Implement `KnowledgeExtractionService` Core Logic:**
            - Create `services/knowledge_extraction_service.py`.
            - Implement `KnowledgeExtractionService` class (taking LLM client dependency).
            - Implement `extract_knowledge(text_content: str) -> list[dict]` method: call the refined LLM prompt, parse the response according to the defined schema, handle errors/malformed responses.
        - [ ] **Sub-task 9.1.4: Unit Testing (Parsing):**
            - [TDD - Unit] Write unit tests focusing *only* on the response parsing logic within `KnowledgeExtractionService`. Mock the LLM client call and provide various pre-defined valid/invalid JSON strings (based on the schema from 9.1.1) to verify correct parsing into the list of dictionaries, and proper error handling for malformed JSON.

- [ ] **Task 9.2: Update Neo4j DAL for Extracted Entities & Relationships** (D: 3.3, `dataSchema.md` finalized)
    - **Goal:** Ensure Neo4j DAL methods can create/merge all required nodes and relationships based on potentially resolved IDs provided by the `IngestionService`.
    - [ ] Steps:
        - [ ] **Sub-task 9.2.1: Implement Node Creation/Merge Methods:**
            - Add/Verify specific methods in `dal/neo4j_dal.py` for each extractable entity type (`merge_topic`, `create_preference`, `create_decision`, `create_action_item`, `create_blocker`, `create_risk`). These methods take properties extracted by the LLM (text, status, etc.) and context IDs (project, session) *provided by the IngestionService*.
            - Ensure methods return the created/merged node's actual Neo4j ID.
        - [ ] **Sub-task 9.2.2: Implement Generic Relationship Creation:**
            - Add a flexible method like `create_relationship_by_ids(source_node_id: str, relationship_type: str, target_node_id: str, properties: dict | None = None)`.
            - This method will be used by the `IngestionService` in the second pass to create relationships identified by the LLM (both internal batch links and external resolved links).
        - [ ] **Sub-task 9.2.3: Implement Entity Lookup Methods:**
            - Add methods needed for entity resolution by the `IngestionService`, e.g.:
                - `find_user_id_by_name(name: str) -> str | None`
                - `find_project_id_by_name(name: str) -> str | None`
                - `find_topic_id_by_name(name: str) -> str | None` (Consider if topics should be strictly merged by `merge_topic` instead).
            - Implement basic caching for these lookups if needed later.
        - [ ] **Sub-task 9.2.4: DAL Integration Testing:**
            - [TDD - DAL Int] Write/update integration tests for node creation (`9.2.1`), relationship creation (`9.2.2`), and entity lookups (`9.2.3`). Verify correct graph structures are formed and lookups work as expected. Use test fixtures to create necessary context nodes (Users, Projects, etc.) for lookups.

- [ ] **Task 9.3: Integrate Hybrid Extraction into Ingestion Service** (D: 3.5, 9.0, 9.1, 9.2)
    - **Goal:** Orchestrate the hybrid knowledge extraction flow within the ingestion pipeline: call extraction, resolve entity hints, create nodes, and link relationships.
    - [ ] Steps:
        - [ ] **Sub-task 9.3.1: Inject Dependencies:**
            - Inject `KnowledgeExtractionService` and updated `Neo4jDAL` into `IngestionService`.
        - [ ] **Sub-task 9.3.2: Implement Two-Pass Processing in `ingest_chunk`:**
            - **After** creating the source `:Chunk` node via `_update_neo4j_graph`:
            - **Call Extraction:** `extracted_data = knowledge_extraction_service.extract_knowledge(text_content)`.
            - **Pass 1: Node Creation & Entity Resolution:**
                - Initialize an empty dictionary `temp_id_to_neo4j_id = {}`.
                - Initialize an empty dictionary `resolved_external_ids = {}`.
                - Loop through `extracted_data`:
                    - For each entity, extract `temp_id`, `entity_type`, `properties`, and `relationships`.
                    - Call the appropriate DAL node creation method (e.g., `neo4j_dal.create_decision(properties=...)`) passing properties and known context IDs (project_id, session_id from original chunk). Store the returned `neo4j_node_id` in `temp_id_to_neo4j_id[temp_id] = neo4j_node_id`.
                    - Loop through the `relationships` for this entity:
                        - If a relationship has a `target_hint` (external entity like a User name or Project name):
                            - Check if hint is already in `resolved_external_ids`. If not, call the appropriate DAL lookup method (e.g., `neo4j_dal.find_user_id_by_name(target_hint)`).
                            - Store the result (or None if not found) in `resolved_external_ids[target_hint] = resolved_id`.
            - **Pass 2: Relationship Creation:**
                - Loop through `extracted_data` again:
                    - Get the source node's Neo4j ID: `source_neo4j_id = temp_id_to_neo4j_id[entity['temp_id']]`.
                    - Loop through its `relationships`:
                        - Determine the target Neo4j ID:
                            - If it has `target_temp_id`, `target_neo4j_id = temp_id_to_neo4j_id[relationship['target_temp_id']]`.
                            - If it has `target_hint`, `target_neo4j_id = resolved_external_ids.get(relationship['target_hint'])`.
                        - If `target_neo4j_id` is found:
                            - Call `neo4j_dal.create_relationship_by_ids(source_neo4j_id, relationship['type'], target_neo4j_id)`.
                    - Create standard context relationships (e.g., `APPLIES_TO` Project, `CREATED_IN` Session) by calling `neo4j_dal.create_relationship_by_ids` using the `source_neo4j_id` and the context IDs held by the service.
            - **Error Handling:** Implement robust error handling for LLM failures, parsing errors, failed entity resolution, and DAL errors.
        - [ ] **Sub-task 9.3.3: Service Integration Testing:**
            - [TDD - Service Int] Write comprehensive tests for the updated `IngestionService.ingest_chunk` logic:
                - Mock `KnowledgeExtractionService` to return structured output including inter-entity relationships (using `target_temp_id`) and external hints (using `target_hint`).
                - Mock `Neo4jDAL` methods (node creation, relationship creation, entity lookups). Ensure lookups are mocked to return expected IDs for hints.
                - Verify the two-pass logic: Correct node creation calls occur first, followed by correct entity lookup calls, and finally correct relationship creation calls with the right source/target IDs (resolved or mapped from temp IDs).
                - Test edge cases: LLM returns no entities, entity resolution fails for a hint, relationship target not found.

- [ ] **Task 9.4: Extraction End-to-End Testing (Hybrid Approach)** (D: 9.3, Phase 5 E2E Tests)
    - **Goal:** Verify the complete hybrid flow: API -> Ingestion -> Extraction -> Resolution -> Neo4j Persistence.
    - [ ] Steps:
        - [ ] **Sub-task 9.4.1: Develop E2E Tests:**
            - [TDD - E2E] Write/update E2E tests for knowledge extraction, focusing on complex cases:
                - **Test Case 1 (ActionItem with Assignee Hint):** Ingest "Alice needs to review the Q3 budget". Verify `:ActionItem` created, `[:ASSIGNED_TO]` relationship points to the correct resolved `:User` node for Alice, `[:DERIVED_FROM]` points to the source `:Chunk`, context links exist.
                - **Test Case 2 (Risk related to Project Hint):** Ingest "Risk: API latency might impact Project Alpha". Verify `:Risk`, `[:RELATES_TO]` points to resolved `:Project` node for Alpha, `[:IDENTIFIED_IN]` points to source `:Chunk`.
                - **Test Case 3 (Decision addressing Risk - requires LLM to link):** Ingest "Risk: Market shift requires product pivot. Decision: We will target enterprise customers starting Q4.". Query Neo4j to verify `:Risk`, `:Decision`, the link between them (e.g., `[:ADDRESSES]`), and links back to the source `:Chunk`(s).
                - **Test Case 4 (Multiple & Mixed):** Ingest text containing multiple items (e.g., Blocker identified, ActionItem assigned, Topic mentioned). Verify all expected nodes and relationships are created correctly, including inter-entity links identified by the LLM.
        - [ ] **Sub-task 9.4.2: Debug & Refine:**
            - Run E2E tests. Debug failures (prompts, parsing, resolution logic, DAL queries, test setup).

---

## Phase 10: Advanced Retrieval & Suggestions (Leveraging Enriched Graph)

*Note: This phase implements advanced retrieval endpoints, leveraging the enriched knowledge graph from Phase 9 and incorporating strategies like **Graph-Enhanced RAG** and **Advanced Graph Filtering** inspired by `memory-bank/v1/retrieval_improvement.md` and tested in `scripts/combined_retrieval_demo.py`.*

- [ ] **Task 10.0: Implement Core Graph Enrichment Logic** (D: Phase 9 Completion)
    - [ ] **Goal:** Create reusable service/DAL logic for enriching chunk data with connected graph entities.
    - [ ] Steps:
        - [ ] **Sub-task 10.0.1: Enhance Neo4j DAL for Comprehensive Context:**
            - [ ] Implement/Refine `Neo4jDAL.get_comprehensive_chunk_context(chunk_ids)` method (similar to demo script) to efficiently retrieve connected Users (author), Topics (mentioned), Sessions/Projects (context), Documents (source), and crucially, linked Decisions, ActionItems, Risks, Blockers using the relationships defined in Phase 9 (`DERIVED_FROM`, `IDENTIFIED_IN`, `RELATES_TO`, `ASSIGNED_TO`, etc.).
            - [ ] [TDD - DAL Int] Write integration tests verifying this method returns the expected linked entities for various scenarios (chunk linked to decision, action item, risk, etc.).
        - [ ] **Sub-task 10.0.2: Integrate Enrichment into RetrievalService:**
            - [ ] Modify `RetrievalService` methods (like `_enrich_results_with_graph`) to use the comprehensive DAL method.
            - [ ] Ensure enrichment is applied consistently where `include_graph=True` is requested.
            - [ ] [TDD - Service Int] Test that service methods correctly call the comprehensive DAL enrichment and format the results.

- [ ] **Task 10.1: Implement Advanced Filtering Logic** (D: Phase 9 Completion)
    - [ ] **Goal:** Enable filtering of Qdrant results based on graph relationships and properties of connected entities.
    - [ ] Steps:
        - [ ] **Sub-task 10.1.1: Implement Neo4j DAL Filtering Methods:**
            - [ ] Create specific `Neo4jDAL` methods for filtering `chunk_ids` based on graph patterns, e.g.:
                - `filter_chunks_linked_to_entity(chunk_ids, entity_label, entity_properties)` (e.g., find chunks `DERIVED_FROM` a `Decision` with `status='Agreed'`).
                - `filter_chunks_by_relationship_to_node(chunk_ids, target_node_label, target_node_id, relationship_type, direction)` (e.g., find chunks `MENTIONS` a specific `Topic` ID).
                - Adapt filtering patterns from demo script (`filter_by_project_manager`, `filter_by_document_session`).
            - [ ] [TDD - DAL Int] Write integration tests for each new filtering method against seeded graph data.
        - [ ] **Sub-task 10.1.2: Integrate Filtering into RetrievalService:**
            - [ ] Update `RetrievalService` methods to accept new filtering parameters (e.g., `filter_by_decision_status`, `filter_by_assigned_action_user_id`).
            - [ ] Conditionally call the appropriate Neo4j DAL filtering methods *after* the initial Qdrant search but *before* enrichment/returning results.
            - [ ] [TDD - Service Int] Test that service methods apply filters correctly by mocking DAL calls.

- [ ] **Task 10.2: Re-implement Full User Preference Endpoint (`/v1/users/{user_id}/preferences`)** (D: 7.7, 10.0, 10.1)
    - [ ] Steps:
        - [ ] Refine/Implement `PreferenceService` to leverage graph enrichment (Task 10.0) - show context around preference statements (e.g., related decisions, topics).
        - [ ] Add optional graph-based filtering (Task 10.1) via query parameters (e.g., filter by preferences related to a specific `project_id`).
        - [ ] Define `GET /v1/users/{user_id}/preferences` endpoint (confirm path/params). Use Pydantic models reflecting enriched structure.
        - [ ] [TDD Steps]:
            - [ ] [DAL Int] Test underlying graph queries for preferences and context. Test filtering queries.
            - [ ] [Service Int] Test `PreferenceService` logic incorporating enrichment and filtering.
            - [ ] [API/Contract] Test endpoint schema/status, including new filter parameters.
            - [ ] [E2E] Test preference retrieval with enrichment and filtering scenarios.

- [ ] **Task 10.3: Re-implement Group Context Endpoint (`/v1/retrieve/group`)** (D: 7.6.2, 10.0, 10.1)
    - [ ] Steps:
        - [ ] Refactor `retrieve_group_context` logic in `RetrievalService` to apply comprehensive graph enrichment (Task 10.0) to results for each user.
        - [ ] Add advanced graph filtering options (Task 10.1) applicable across the group (e.g., `filter_by_topic`, `filter_by_risk_status`).
        - [ ] Define `GET /v1/retrieve/group` endpoint. Update Pydantic models for enriched results.
        - [ ] [TDD Steps]:
            - [ ] [DAL Int/Service Int] Test participant identification, cross-user Qdrant query, filtering logic, and enrichment aggregation.
            - [ ] [API/Contract] Verify request/response, including new filters.
            - [ ] [E2E] Test group retrieval with enrichment and filtering.

- [ ] **Task 10.4: Implement Entity Connections Endpoint (`/retrieve/entity_connections`)** (D: 10.0)
    - [ ] Steps:
        - [ ] Refine `get_entity_connections` in `Neo4jDAL` to return richer property details for connected nodes (leveraging new entity types).
        - [ ] Refine service method in `RetrievalService`.
        - [ ] Define `GET /retrieve/entity_connections` endpoint. Update Pydantic models.
        - [ ] [TDD Steps]:
            - [ ] [DAL Int] Test richer graph traversal query in Neo4jDAL.
            - [ ] [API/Contract] Test endpoint schema/status.
            - [ ] [E2E] Call endpoint for various entity types (Chunk, Decision, ActionItem, Topic), verify connections and properties.

- [ ] **Task 10.5: Implement Timeline Endpoint (`/retrieve/timeline`)** (D: 10.0, 10.1)
    - [ ] Steps:
        - [ ] Refine Qdrant time filtering/sorting (as before).
        - [ ] Add **optional** graph enrichment (Task 10.0) via `include_graph` parameter.
        - [ ] Add **optional** graph filtering (Task 10.1) via query parameters (e.g., timeline for items `MENTIONS` specific topic).
        - [ ] Define `GET /v1/retrieve/timeline` endpoint. Update Pydantic models.
        - [ ] [TDD Steps]:
            - [ ] [DAL Int] Test Qdrant time filtering + Neo4j graph filtering combinations.
            - [ ] [API/Contract] Test endpoint schema/status with new parameters.
            - [ ] [E2E] Test timeline retrieval with and without enrichment/filtering.

- [ ] **Task 10.6: Implement Suggest Related Entities Endpoint (`/suggest/related_entities`)** (D: 10.0, 10.1)
    - [ ] Steps:
        - [ ] Refactor `suggest_related_entities` logic in `RetrievalService` to heavily rely on graph traversal from the context (chunk or query results). Use comprehensive context (Task 10.0).
        - [ ] Leverage new entity types (Suggest related Decisions, Risks, ActionItems as well as Topics, Docs, Users).
        - [ ] Define `GET /suggest/related_entities` endpoint. Update Pydantic models for richer suggestions.
        - [ ] [TDD Steps]:
            - [ ] [Service Int] Test suggestion logic using mocked comprehensive context.
            - [ ] [API/Contract] Test endpoint schema/status.
            - [ ] [E2E] Test suggestions for different inputs, verifying relevant new entity types are suggested.

- [ ] **Task 10.7: (Optional) Explore Advanced Re-ranking/Query Expansion** (D: All Phase 10 endpoints)
    - [ ] Steps:
        - [ ] Based on Phase 10 results, evaluate if Graph-Aware Re-ranking or Query Expansion (from `retrieval_improvement.md`) is necessary.
        - [ ] If needed, design and implement chosen strategy:
            - Refactor `RetrievalService` methods.
            - Update DAL calls (e.g., fetch more initial results for re-ranking).
            - Add API flags if needed.
            - Write tests specifically verifying the impact of the new strategy.

---

## Phase 11: Final Testing & Refinement

- [ ] **Task 11.1: Final Testing & Refinement** (D: All Phases 1-10)
    - [ ] Steps:
        - [ ] Run all automated tests (`pytest`). Ensure 100% pass rate.
        - [ ] Check code coverage (`pytest --cov`). Address major gaps.
        - [ ] Perform manual testing using the Streamlit UI (Phase 8) to cover key user flows.
        - [ ] Review code for clarity, consistency, and adherence to patterns (`systemPatterns.md`).
        - [ ] Refactor code as needed based on testing and review.
        - [ ] Update `README.md` with final usage instructions.