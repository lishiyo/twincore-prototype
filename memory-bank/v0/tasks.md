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

- [ ] **Task 4.3: Seeding API Endpoint** (D: 1.1, 4.2)
    - [ ] Steps:
        - [ ] Create `api/routers/admin_router.py`. Define `POST /api/seed_data`. Inject `DataSeederService` via `Depends`. Call `seed_initial_data()`. Register router in `main.py`. Review [api.md](./api.md) for the expected API contract.
        - [ ] [API/Contract] Write API test asserting 200 OK.
        - [ ] Create endpoint to clear out all data. That lets us revert the `seed_initial_data`.
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
        - [ ] Define & Implement retrieval methods in `dal/interfaces.py`, `dal/neo4j_dal.py`, `dal/qdrant_dal.py`