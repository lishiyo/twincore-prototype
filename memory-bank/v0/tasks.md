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

- [ ] **Task 1.2: Testing Setup** (D: 1.1)
    - [ ] Steps:
        - [ ] Add testing dependencies to `requirements.txt` (`pytest`, `pytest-asyncio`, `httpx`, `pytest-mock`, `pytest-cov`, `schemathesis`). Install.
        - [x] Create `pytest.ini`.
        - [x] Create basic test fixtures (e.g., `httpx` client in `tests/conftest.py`).
        - [x] Ensure Task 1.1 test runs via `pytest`.

- [ ] **Task 1.3: Docker Setup for Databases**
    - [ ] Steps:
        - [ ] Create `docker-compose.yml` for Qdrant & Neo4j dev instances.
        - [ ] Create `docker-compose.test.yml` (or profiles) for isolated test DB instances.
        - [ ] Document basic `docker-compose` usage in README.
    - [ ] Dependencies: None

---

## Phase 2: Core Data Models & DB Setup

- [x] **Task 2.1: Pydantic API Models**
    - [x] Steps:
        - [x] Define core Pydantic models in `api/models.py` based on `dataSchema.md` & `projectbrief.md`.
    - [x] Dependencies: None

- [ ] **Task 2.2: Database Client Initialization** (D: 1.1, 1.3)
    - [ ] Steps:
        - [ ] Add `qdrant-client`, `neo4j` to `requirements.txt`. Install.
        - [ ] Implement client initialization in `core/db_clients.py`, reading from config.
        - [ ] [Unit] Write unit tests mocking config to verify client initialization.

- [ ] **Task 2.3: Qdrant Collection Setup** (D: 1.3, 2.2)
    - [ ] Steps:
        - [ ] Implement utility in `core/db_setup.py` to create `twin_memory` collection via client.
        - [ ] [DAL Int] Write integration test using test Qdrant instance to verify collection creation & cleanup.

- [ ] **Task 2.4: Neo4j Constraints Setup** (D: 1.3, 2.2)
    - [ ] Steps:
        - [ ] Implement utility in `core/db_setup.py` to create uniqueness constraints via driver.
        - [ ] [DAL Int] Write integration test using test Neo4j instance to verify constraint creation & cleanup.

---

## Phase 3: Embedding & Core Ingestion Logic

- [ ] **Task 3.1: Embedding Service** (D: 1.1)
    - [ ] Steps:
        - [ ] Add openai to `requirements.txt` for the embedding model. Install.
        - [ ] Create `services/embedding_service.py`.
        - [ ] Implement `EmbeddingService` class (loads model from config, `get_embedding` method).
        - [ ] [Unit] Write unit tests mocking model loading, verify method signature and error handling.

- [ ] **Task 3.2: DAL Interfaces (ABCs/Protocols)**
    - [ ] Steps:
        - [ ] Define interfaces in `dal/interfaces.py` (`IQdrantDAL`, `INeo4jDAL`) outlining core methods.
    - [ ] Dependencies: None

- [ ] **Task 3.3: Neo4j DAL Implementation (Core)** (D: 1.3, 2.2, 2.4, 3.2)
    - [ ] Steps:
        - [ ] Create `dal/neo4j_dal.py` implementing `INeo4jDAL`.
        - [ ] Implement `create_node_if_not_exists`, `create_relationship_if_not_exists` using Cypher MERGE/CREATE.
        - [ ] [DAL Int] Write integration tests against test Neo4j: test node/relationship creation, properties, idempotency, cleanup.

- [ ] **Task 3.4: Qdrant DAL Implementation (Core)** (D: 1.3, 2.2, 2.3, 3.2)
    - [ ] Steps:
        - [ ] Create `dal/qdrant_dal.py` implementing `IQdrantDAL`.
        - [ ] Implement `upsert_vector`, basic `search_vectors`.
        - [ ] [DAL Int] Write integration tests against test Qdrant: test upsert, payload verification, basic search, cleanup.

- [ ] **Task 3.5: Ingestion Service (Core Logic)** (D: 3.1, 3.3, 3.4)
    - [ ] Steps:
        - [ ] Create `services/ingestion_service.py`. Implement `IngestionService` taking DALs/EmbeddingService dependencies.
        - [ ] Implement internal helpers (`_prepare_qdrant_point`, `_update_neo4j_graph`).
        - [ ] [Service Int] Write integration tests mocking DAL/Embedding interfaces, verify correct DAL methods are called with expected args for given inputs.

---

## Phase 4: Seeding Endpoint (`/api/seed_data`)

- [ ] **Task 4.1: Mock Data Module**
    - [ ] Steps:
        - [ ] Create `core/mock_data.py` based on PRD.
    - [ ] Dependencies: None

- [ ] **Task 4.2: Seeding Logic in Ingestion Service** (D: 3.5, 4.1)
    - [ ] Steps:
        - [ ] Add `seed_initial_data()` method to `IngestionService`. Iterate mock data, call internal processing/DAL methods.
        - [ ] [Service Int] Update tests for `IngestionService` to cover `seed_initial_data`, verify DAL call sequences.

- [ ] **Task 4.3: Seeding API Endpoint** (D: 1.1, 4.2)
    - [ ] Steps:
        - [ ] Create `api/routers/admin_router.py`. Define `POST /api/seed_data`. Inject `IngestionService` via `Depends`. Call `seed_initial_data()`. Register router in `main.py`.
        - [ ] [API/Contract] Write API test asserting 200 OK.

- [ ] **Task 4.4: Seeding End-to-End Test** (D: 1.3, 2.2, 4.3)
    - [ ] Steps:
        - [ ] [E2E] Write E2E test using `HTTPX` and real test DBs. Call `/api/seed_data`. Directly query test Qdrant/Neo4j to verify data integrity.

---

## Phase 5: Ingestion Endpoints (`/api/ingest/*`)

- [ ] **Task 5.1: Ingest Message Endpoint** (D: 2.1, 3.5, 4.4)
    - [ ] Steps:
        - [ ] Add `ingest_message(data)` logic to `IngestionService`.
        - [ ] Create `api/routers/ingest_router.py`. Define `POST /api/ingest/message`. Use Pydantic models. Inject service. Register router.
        - [ ] [TDD Steps]:
            - [ ] [Service Int] Test `ingest_message` logic.
            - [ ] [API/Contract] Test endpoint schema/status.
            - [ ] [E2E] Call endpoint, verify data in Qdrant/Neo4j.

- [ ] **Task 5.2: Ingest Document Endpoint** (D: 2.1, 3.5, 5.1)
    - [ ] Steps:
        - [ ] Implement basic text chunking logic (e.g., in `core/utils.py`).
        - [ ] Add `ingest_document(data)` logic to `IngestionService`, including chunking & handling `is_private`.
        - [ ] Define `POST /api/ingest/document` endpoint in `ingest_router.py`.
        - [ ] [TDD Steps]:
            - [ ] [Unit] Test chunking logic.
            - [ ] [Service Int] Test `ingest_document` logic.
            - [ ] [API/Contract] Test endpoint schema/status.
            - [ ] [E2E] Call endpoint, verify doc node, chunks, relationships, `is_private` flag propagation.

---

## Phase 6: Retrieval Endpoints (`/api/retrieve/*`)

- [ ] **Task 6.1: Retrieval Service & DAL Methods** (D: 3.3, 3.4, Phase 4)
    - [ ] Steps:
        - [ ] Define & Implement retrieval methods in `dal/interfaces.py`, `dal/neo4j_dal.py`, `dal/qdrant_dal.py` (e.g., `get_session_participants`, `search_with_filters`). Focus on filter logic.
        - [ ] Create `services/retrieval_service.py`. Implement `RetrievalService` taking DAL dependencies.
        - [ ] Implement core logic (`retrieve_session_context`, `retrieve_private_memory`).
        - [ ] [TDD Steps]:
            - [ ] [DAL Int] Test new DAL retrieval/filtering methods thoroughly.
            - [ ] [Service Int] Test `RetrievalService`, mocking DALs, verify filter construction & data flow.

- [ ] **Task 6.2: Retrieve Context Endpoint** (D: 2.1, 6.1)
    - [ ] Steps:
        - [ ] Create `api/routers/retrieve_router.py`. Define `POST /api/retrieve/context`. Use Pydantic models. Inject `RetrievalService`. Register router.
        - [ ] [TDD Steps]:
            - [ ] [API/Contract] Test endpoint schema/status.
            - [ ] [E2E] Seed data, call endpoint (various scopes/queries), verify returned chunks match DB state.

- [ ] **Task 6.3: Retrieve Private Memory Endpoint** (D: 5.1, 6.2)
    - [ ] Steps:
        - [ ] Implement dual logic in the endpoint: ingest query via `IngestionService`, then retrieve via `RetrievalService` with strict user/privacy filtering.
        - [ ] Define `POST /api/retrieve/private_memory` endpoint in `retrieve_router.py`.
        - [ ] [TDD Steps]:
            - [ ] [Service Int] Update tests for `IngestionService` (twin interaction type) & `RetrievalService` (private filtering).
            - [ ] [API/Contract] Test endpoint schema/status.
            - [ ] [E2E] Seed public/private data, call endpoint as different users, verify query ingestion AND correct data/privacy filtering in results.

---

## Phase 7: Preference Endpoint (`/api/query/user_preference`)

- [ ] **Task 7.1: Preference Service & DAL Methods** (D: 6.1)
    - [ ] Steps:
        - [ ] Define & Implement necessary DAL methods for finding user statements/messages related to a topic (simple retrieval focus for prototype).
        - [ ] Create `services/preference_service.py`. Implement `PreferenceService`.
        - [ ] Implement `query_user_preference(user_id, topic, scope)` logic.
        - [ ] [TDD Steps]:
            - [ ] [DAL Int] Test preference-related DAL queries.
            - [ ] [Service Int] Test `PreferenceService` logic.

- [ ] **Task 7.2: User Preference Endpoint** (D: 7.1)
    - [ ] Steps:
        - [ ] Create `api/routers/query_router.py`. Define `POST /api/query/user_preference`. Use Pydantic models. Inject `PreferenceService`. Register router.
        - [ ] [TDD Steps]:
            - [ ] [API/Contract] Test endpoint schema/status.
            - [ ] [E2E] Seed relevant data, call endpoint, verify correct snippets are returned based on user/topic/scope.

---

## Phase 8: Verification UI (Minimal Streamlit App)

- [ ] **Task 8.1: Streamlit App Setup** (D: None)
    - [ ] Steps:
        - [ ] Create `streamlit_app.py`.
        - [ ] Add `streamlit`, `requests` to `requirements.txt`. Install.
        - [ ] Set up basic UI layout per `projectbrief.md`.

- [ ] **Task 8.2: Connect UI to Backend** (D: 8.1, Phase 4-7 API Endpoints)
    - [ ] Steps:
        - [ ] Implement button callbacks using `requests` to call FastAPI endpoints.
        - [ ] Display JSON responses.
    - [ ] Testing: Manual verification against running backend.

---

## Phase 9: LLM-Based Knowledge Extraction (Post-Prototype Enhancement)

*Note: This phase focuses on enriching the knowledge graph by extracting entities (Topics, Preferences, etc.) and relationships directly from text content using an LLM. It builds upon the foundation laid in Phases 1-8.*

- [ ] **Task 9.1: Design Extraction Schema & Prompts**
    - [ ] Steps:
        - [ ] Define the target entities and relationships to extract (e.g., `Topic`, `Preference`, `Decision`, `ActionItem`, `MENTIONS`, `STATES_PREFERENCE`).
        - [ ] Design the structured output format (e.g., JSON schema) expected from the LLM.
        - [ ] Develop and refine prompts (and potentially function/tool schemas) for the chosen LLM (e.g., Gemini) to reliably extract the target information into the desired format.
        - [ ] Select and configure the specific LLM API/model to use.
    - [ ] Dependencies: Phase 1 (Config), `dataSchema.md` (understanding existing graph)

- [ ] **Task 9.2: Implement KnowledgeExtractionService** (D: 9.1)
    - [ ] Steps:
        - [ ] Add LLM client library (e.g., `google-generativeai`) to `requirements.txt`. Install.
        - [ ] Create `services/knowledge_extraction_service.py`.
        - [ ] Implement `KnowledgeExtractionService` class. Include methods to:
            - [ ] Initialize the LLM client (reading API keys/config).
            - [ ] Call the LLM API with text and the designed prompt/schema.
            - [ ] Parse the structured LLM response (handle potential errors/malformed output).
        - [ ] [Unit] Write unit tests mocking the LLM API client. Test prompt formatting, response parsing, and error handling.

- [ ] **Task 9.3: Update Neo4j DAL for Extracted Knowledge** (D: 3.3, 9.1)
    - [ ] Steps:
        - [ ] Add new methods to `dal/interfaces.py` and `dal/neo4j_dal.py` to handle merging extracted entities (e.g., `merge_topic`, `create_preference_node`) and relationships (e.g., `link_message_to_topic`, `link_user_to_preference`).
        - [ ] [DAL Int] Write integration tests for these new DAL methods using the test Neo4j instance.

- [ ] **Task 9.4: Integrate Extraction into IngestionService** (D: 3.5, 9.2, 9.3)
    - [ ] Steps:
        - [ ] Modify `services/ingestion_service.py`.
        - [ ] Inject `KnowledgeExtractionService` as a dependency.
        - [ ] Within the core ingestion logic (e.g., `ingest_message`, `ingest_document` chunk processing), *after* basic metadata processing, call the `KnowledgeExtractionService` with the text content.
        - [ ] Use the parsed results from the extraction service to call the new Neo4j DAL methods (Task 9.3) to update the graph with extracted knowledge.
        - [ ] Decide whether/how to add extracted info (e.g., topic IDs) to the Qdrant payload (requires potential update to Task 3.4/3.5 logic).
        - [ ] [Service Int] Update integration tests for `IngestionService`. Mock the `KnowledgeExtractionService` and the updated DAL methods. Verify that the extraction service is called and the relevant DAL methods for graph enrichment are subsequently called with the correct data.

- [ ] **Task 9.5: End-to-End Testing for Knowledge Extraction** (D: 4.4, 5.1, 5.2, 9.4)
    - [ ] Steps:
        - [ ] [E2E] Write new E2E tests or modify existing ones.
        - [ ] Ingest sample text containing clear topics, preferences, etc.
        - [ ] Directly query Neo4j to verify that the corresponding `Topic`, `Preference` nodes and `MENTIONS`, `STATES_PREFERENCE` relationships were created correctly, linked to the source message/document and user.
        - [ ] (Optional) Test retrieval mechanisms that leverage this extracted knowledge (likely requires new retrieval logic/endpoints in a subsequent phase).