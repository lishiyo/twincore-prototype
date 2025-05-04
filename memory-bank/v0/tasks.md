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

- [ ] **Task 6.1: Retrieval Service & DAL Methods** (D: 3.3, 3.4, Phase 4)
    - [x] Steps:
        - [x] Define & Implement retrieval methods in `dal/interfaces.py`, `dal/neo4j_dal.py`, `dal/qdrant_dal.py` (e.g., get_session_participants, get_project_context, get_related_content, get_content_by_topic, search_with_filters). Focus on filter logic.
        - [x] [TDD Steps]:
            - [x] [DAL Int] Test retrieval methods against test DBs (filtering, scoring, limits).
            - [x] [Service Int] Implement `RetrievalService`, mock DALs, test logic combining search results.
            - [ ] [API/Contract] Test endpoint schema/status for `/v1/retrieve/*` endpoints.
            - [ ] [E2E] Call endpoints, verify correct filtered data is retrieved from Qdrant/Neo4j.

- [x] **Task 6.2: Context Retrieval Endpoint (`/v1/retrieve/context`)** (D: 2.1, 6.1)
    - [x] Steps:
        - [x] Implement `retrieve_context(data)` and `retrieve_enriched_context(data)` logic in `RetrievalService`.
        - [x] Define `GET /v1/retrieve/context` endpoint in `retrieve_router.py` (with `include_graph` flag). Use Pydantic models. Inject RetrievalService. Register router.
        - [x] [TDD Steps]:
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [ ] [E2E] Test scenario simulating Canvas Agent call, verify group context retrieval.

- [x] **Task 6.3: Private Memory Retrieval Endpoint (`/v1/retrieve/private_memory`)** (D: 2.1, 5.1, 6.1)
    - [x] Steps:
        - [x] Implement dual logic in the endpoint: ingest query via MessageConnector, then retrieve via RetrievalService with strict user/privacy filtering.
            - [x] Implement `retrieve_private_memory(data)` logic in `RetrievalService`.
            - [x] **Important:** Ensure this service method *also* calls `MessageConnector.ingest_message` to store the user's query as a twin interaction (as per `projectbrief.md`).
        - [x] Define `POST /v1/retrieve/private_memory` endpoint in `retrieve_router.py` (with `include_graph` flag).
        - [x] [TDD Steps]:
            - [x] [Service Int] Test combined retrieval + ingestion logic for private memory.
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [ ] [E2E] Test scenario simulating User->Twin call, verify private filtering AND query ingestion.
            - [ ] [E2E] Seed public/private data, call endpoint as different users, verify query ingestion AND correct data/privacy filtering in results.

- [x] **Task 6.4: Related Content Retrieval Endpoint (`/v1/retrieve/related_content`)** (D: 2.1, 6.1)
    - [x] Steps:
        - [x] Implement `retrieve_related_content(data)` logic in `RetrievalService`.
        - [x] Define `GET /v1/retrieve/related_content` endpoint in `retrieve_router.py`. Use Pydantic models. Inject RetrievalService.
        - [x] [TDD Steps]:
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [ ] [E2E] Test scenario retrieving related content via graph traversal.

- [x] **Task 6.5: Topic Retrieval Endpoint (`/v1/retrieve/topic`)** (D: 2.1, 6.1)
    - [x] Steps:
        - [x] Implement `retrieve_by_topic(data)` logic in `RetrievalService`.
        - [x] Define `GET /v1/retrieve/topic` endpoint in `retrieve_router.py`. Use Pydantic models. Inject RetrievalService.
        - [x] [TDD Steps]:
            - [x] [API/Contract] Verify specific request/response for this endpoint.
            - [ ] [E2E] Test scenario retrieving content by topic.

---

## Phase 7: Preference Endpoint (`/v1/retrieve/user_preference`)

- [ ] **Task 7.1: Preference Service & DAL Methods** (D: 3.3, 3.4, Phase 4)
    - [ ] Steps:
        - [ ] Define & Implement necessary DAL methods for finding user statements/messages related to a topic (querying past statements/data) in `dal/qdrant_dal.py` and/or `dal/neo4j_dal.py`. *Note: Relies on existing data/embeddings for prototype; explicit Preference nodes are phase 9.*
        - [ ] Create `services/preference_service.py`. Implement `PreferenceService` taking DAL dependencies.
        - [ ] Implement `query_user_preference(data)` logic in `PreferenceService`.
        - [ ] [TDD Steps]:
            - [ ] [DAL Int] Test preference retrieval queries against test DBs with seeded relevant data.
            - [ ] [Service Int] Implement `PreferenceService`, mock DALs, test logic for interpreting/returning preferences.

- [ ] **Task 7.2: Preference API Endpoint** (D: 2.1, 7.1)
    - [ ] Steps:
        - [ ] Create `api/routers/query_router.py`. Define `POST /api/query/user_preference`. Use Pydantic models. Inject service. Register router.
        - [ ] [TDD Steps]:
            - [ ] [API/Contract] Test endpoint schema/status.

- [ ] **Task 7.3: Preference End-to-End Test** (D: 7.2, Phase 4)
    - [ ] Steps:
        - [ ] [E2E] Write E2E test simulating Canvas Agent call. Call endpoint, verify relevant past statements/data are returned based on seeded mock data.
        - [ ] Ingest real data, call endpoint, verify responses look correct.

---

## Phase 8: Verification UI (Streamlit)

- [ ] **Task 8.1: Streamlit App Setup** (D: 1.1)
    - [ ] Steps:
        - [ ] Create `streamlit_app.py`.
        - [ ] Add `streamlit`, `requests` to `requirements.txt`. Install.
        - [ ] Basic app structure and title.

- [ ] **Task 8.2: UI Layout & Components** (D: 8.1)
    - [ ] Steps:
        - [ ] Implement User Selector (`st.selectbox`).
        - [ ] Implement Canvas Agent Simulation section (text inputs, buttons for context/preference).
        - [ ] Implement User <> Twin Interaction section (text area, button).
        - [ ] Implement Document Upload Simulation section (text inputs, checkbox, button).
        - [ ] Implement Output Display area (`st.text_area` or `st.json`).

- [ ] **Task 8.3: Backend API Integration** (D: 4.3, 5.1, 5.2, 6.2, 6.3, 7.2, 8.2)
    - [ ] Steps:
        - [ ] Add `requests` calls within button callbacks to hit the corresponding backend API endpoints (`/retrieve/context`, `/query/user_preference`, `/retrieve/private_memory`, `/ingest/document`, `/ingest/message` implicitly via private memory).
        - [ ] Pass appropriate data (selected user ID, text inputs, context IDs) to the API calls.
        - [ ] Display API responses in the Output Display area.

- [ ] **Task 8.4: (Bonus) DB Stats Display** (D: 8.3, potentially new admin endpoints)
    - [ ] Steps:
        - [ ] (Optional) Create simple backend endpoints in `admin_router.py` to return counts from Qdrant/Neo4j (e.g., `/api/stats/qdrant_count`, `/api/stats/neo4j_nodes`). Test these endpoints.
        - [ ] Add a "Show DB Stats" button to Streamlit UI.
        - [ ] Call the stats endpoints and display results.

---

## Phase 9: Knowledge Extraction

*Note: This phase focuses on enriching the knowledge graph by extracting entities (Topics, Preferences, etc.) and relationships directly from text content using an LLM. It builds upon the foundation laid in Phases 1-8.*

- [ ] **Task 9.1: Knowledge Extraction Service** (D: 1.1)
    - [ ] Steps:
        - [ ] Design extraction schema/prompts (Topics, Preferences, Entities etc.).
        - [ ] Create `services/knowledge_extraction_service.py`.
        - [ ] Implement `KnowledgeExtractionService` class, including logic to call LLM API (e.g., Gemini) and parse results.
        - [ ] [TDD Steps]:
            - [ ] [Unit] Test LLM result parsing logic (mock LLM response).

- [ ] **Task 9.2: Update Neo4j DAL for Extraction** (D: 3.3, 9.1)
    - [ ] Steps:
        - [ ] Define new node labels (e.g., `Topic`, `Preference`) and relationship types (e.g., `MENTIONS`, `STATES_PREFERENCE`) in `dataSchema.md` (if not already drafted).
        - [ ] Add methods to `dal/neo4j_dal.py` to merge/create extracted entities and relationships based on parsed LLM results.
        - [ ] [TDD Steps]:
            - [ ] [DAL Int] Test new DAL methods against test Neo4j, verifying graph structure updates.

- [ ] **Task 9.3: Integrate Extraction into Ingestion Service** (D: 3.5, 9.1, 9.2)
    - [ ] Steps:
        - [ ] Modify `services/ingestion_service.py` methods (`ingest_message`, `ingest_document`).
        - [ ] Add step to call `KnowledgeExtractionService` after embedding.
        - [ ] Add step to call new Neo4j DAL methods with extracted information.
        - [ ] [TDD Steps]:
            - [ ] [Service Int] Test modified ingestion logic, mocking extraction service and DALs, verify correct methods are called.

- [ ] **Task 9.4: Extraction Testing** (D: 9.3)
    - [ ] Steps:
        - [ ] [E2E] Write E2E tests: ingest data via API, then query Neo4j directly to verify extracted entities/relationships exist.

---

## Phase 10: Final Testing & Refinement

- [ ] **Task 10.1: Final Testing & Refinement** (D: All Phases 1-8)
    - [ ] Steps:
        - [ ] Run all automated tests (`pytest`). Ensure 100% pass rate.
        - [ ] Check code coverage (`pytest --cov`). Address major gaps.
        - [ ] Perform manual testing using the Streamlit UI (Phase 8) to cover key user flows.
        - [ ] Review code for clarity, consistency, and adherence to patterns (`systemPatterns.md`).
        - [ ] Refactor code as needed based on testing and review.
        - [ ] Update `README.md` with final usage instructions.