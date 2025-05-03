# Twincore Prototype Architecture

**Core Principles:**

1.  **Layered Architecture:** Separate API handling, business logic, data access, and external integrations.
2.  **Dependency Inversion / Interfaces:** Code against abstractions (interfaces/abstract base classes) rather than concrete implementations where possible, especially for data access and external services.
3.  **Clear API Contract:** The FastAPI layer defines the stable interface for Dev A.
4.  **Modular Ingestion:** Design ingestion pipelines to easily add new sources.
5.  **Configuration Driven:** Use environment variables or config files for database connections, model names, etc.

**Proposed Architecture Diagram:**

```mermaid
graph LR
    subgraph External Systems
        A[Canvas/Orchestration (Dev A)]
        PG_Shared[Shared Postgres DB (Users, Projects, Sessions)]
        GDrive[Google Drive API]
        GCal[Google Calendar API]
        FileUpload[File Upload Interface]
        LLM_API[LLM API (e.g., Gemini)]
    end

    subgraph TwinCore Service (Dev B - FastAPI App)
        subgraph API Layer (api/)
            Router_Ingest[Ingest Router (/ingest)]
            Router_Retrieve[Retrieve Router (/retrieve)]
            Router_Query[Query Router (/query)]
            Models_Pydantic[Pydantic Models (Request/Response)]
        end

        subgraph Business Logic Layer (services/)
            Service_Retrieval[RetrievalService]
            Service_Ingestion[IngestionService]
            Service_Preference[PreferenceService]
            Service_Embedding[EmbeddingService]
            Service_KnowledgeExtract[KnowledgeExtractionService]
        end

        subgraph Data Access Layer (dal/)
            DAL_Qdrant[Qdrant DAL]
            DAL_Neo4j[Neo4j DAL]
            DAL_Postgres_Shared[Shared Postgres DAL (Read-Only)]
            DAL_Postgres_Twin[Twin Postgres DAL (Read/Write - Optional)]
        end

        subgraph Ingestion Pipeline (ingestion/)
            Ingestion_API[API Triggered Ingestion (via Service_Ingestion)]
            Ingestion_Connectors[Connectors (GDrive, GCal, FileUpload)]
            Ingestion_Processor[Data Processor (Parse, Chunk, Embed)]
            Ingestion_Scheduler[(Optional) Task Scheduler/Queue (Celery/RQ)]
        end

        subgraph Core Utilities (core/)
            Config[Configuration Loading]
            Logging[Logging Setup]
            DB_Clients[Database Clients (Qdrant, Neo4j, SQLAlchemy)]
        end
    end

    %% Connections %%
    A -- HTTP Requests --> Router_Ingest;
    A -- HTTP Requests --> Router_Retrieve;
    A -- HTTP Requests --> Router_Query;

    Router_Ingest -- Uses --> Service_Ingestion;
    Router_Retrieve -- Uses --> Service_Retrieval;
    Router_Query -- Uses --> Service_Preference; %% And potentially Service_Retrieval
    Router_Ingest & Router_Retrieve & Router_Query -- Use --> Models_Pydantic;

    Service_Ingestion -- Calls --> Service_KnowledgeExtract;
    Service_Ingestion -- Uses --> Service_Embedding;
    Service_Ingestion -- Uses --> DAL_Qdrant;
    Service_Ingestion -- Uses --> DAL_Neo4j;
    Service_Ingestion -- Uses --> DAL_Postgres_Twin; %% If needed for twin-specific tables

    Service_KnowledgeExtract -- Calls --> LLM_API;
    Service_KnowledgeExtract -- Updates Via --> DAL_Neo4j;

    Service_Retrieval -- Uses --> DAL_Qdrant;
    Service_Retrieval -- Uses --> DAL_Neo4j;
    Service_Retrieval -- Uses --> DAL_Postgres_Shared; %% To get user/project details

    Service_Preference -- Uses --> DAL_Qdrant;
    Service_Preference -- Uses --> DAL_Neo4j;
    Service_Preference -- Uses --> DAL_Postgres_Shared;
    Service_Preference -- Uses --> DAL_Postgres_Twin; %% If storing complex preferences

    DAL_Qdrant -- Interacts --> DB_Clients;
    DAL_Neo4j -- Interacts --> DB_Clients;
    DAL_Postgres_Shared -- Interacts --> DB_Clients;
    DAL_Postgres_Twin -- Interacts --> DB_Clients;

    %% Ingestion Flow %%
    Ingestion_API -- Triggers --> Service_Ingestion; %% Direct API uploads/messages
    GDrive & GCal & FileUpload -- Processed By --> Ingestion_Connectors;
    Ingestion_Connectors -- May use --> Ingestion_Scheduler;
    Ingestion_Connectors -- Send Data To --> Ingestion_Processor;
    Ingestion_Processor -- Uses --> Service_Embedding;
    Ingestion_Processor -- Send Processed Data To --> Service_Ingestion; %% Or directly to DAL methods

    %% Shared Postgres (Managed Externally by Dev A ideally) %%
    PG_Shared -- Read By --> DAL_Postgres_Shared;

    %% Dependencies %%
    Service_Retrieval & Service_Ingestion & Service_Preference & Service_Embedding & Service_KnowledgeExtract --> Config & Logging;
    DAL_Qdrant & DAL_Neo4j & DAL_Postgres_Shared & DAL_Postgres_Twin --> Config & Logging;

```

**Component Breakdown & Extensibility:**

1.  **API Layer (`api/`)**
    *   **Technology:** FastAPI, Pydantic.
    *   **Responsibility:** Define HTTP endpoints, validate requests/responses using Pydantic models, handle HTTP errors, call appropriate business logic services. Uses FastAPI's `APIRouter` for organization.
    *   **Extensibility:** Adding new endpoints involves adding a new function to a router and calling a new or existing service method. Pydantic models define the clear data contract.

2.  **Business Logic Layer (`services/`)**
    *   **Technology:** Plain Python classes/modules.
    *   **Responsibility:** Orchestrate the steps needed to fulfill an API request. Contains the core "how-to" logic. It doesn't know *how* data is stored, only *what* data access functions to call (via the DAL).
        *   `EmbeddingService`: Abstracts sentence-transformer/LLM embedding model. `get_embedding(text)` method.
        *   `IngestionService`: Coordinates getting data -> embedding -> optional knowledge extraction -> calling DAL methods (`upsert_vector`, `create_node`, `create_relationship`, `merge_extracted_knowledge`).
        *   `RetrievalService`: Coordinates getting context IDs -> building filters -> calling semantic search -> potentially enriching with data from Postgres DAL.
        *   `PreferenceService`: Logic for interpreting preferences from retrieved data.
        *   `KnowledgeExtractionService`: (Phase 9) Calls external LLM API to extract structured information (topics, preferences, etc.) from text. Parses the result.
    *   **Extensibility:** Add new service methods for new features. If logic gets complex, split services further. Uses Dependency Injection (FastAPI `Depends`).

3.  **Data Access Layer (`dal/`)**
    *   **Technology:** Python modules using specific DB clients (`qdrant-client`, `neo4j`, `sqlalchemy` or `psycopg2` for Postgres).
    *   **Responsibility:** **Crucial Abstraction.** Hides the specifics of interacting with each database. Provides methods like `qdrant_dal.search(...)`, `neo4j_dal.get_session_participants(...)`, `postgres_dal.get_user_info(...)`. The business logic layer calls these high-level methods.
    *   **Extensibility:**
        *   **Adding Real Postgres:** Implement `postgres_dal.py` using SQLAlchemy (recommended for ORM mapping to Dev A's models if possible) or `psycopg2`. Point it to the shared DB connection string. Call its methods from services where needed (e.g., `RetrievalService` getting user names).
        *   **Changing DB Schema:** Changes are contained within the specific DAL module. Business logic shouldn't break if the DAL method signature remains the same.
        *   **Adding Twin-Specific PG Tables:** Create a `DAL_Postgres_Twin` module and point it to potentially a separate schema or DB if needed.

4.  **Ingestion Pipeline (`ingestion/`)**
    *   **Technology:** Python modules, potentially libraries like `google-api-python-client`, `beautifulsoup4` (parsing), `langchain` (doc loaders/splitters), Celery/RQ (task queues).
    *   **Responsibility:** Getting data from outside into the system reliably.
        *   **Connectors:** Modules specific to each source (GDrive, GCal, FileUpload endpoint handler). They fetch raw data. Define a common interface if possible.
        *   **Processor:** Takes raw data, parses it (e.g., PDF text extraction), chunks it intelligently, calls `EmbeddingService`, prepares it for storage (adding metadata).
        *   **Scheduler/Queue:** (Optional but recommended for real sources) For background polling (GCal, GDrive changes) or handling large uploads asynchronously. Prevents blocking API requests. Connectors push tasks; workers pick them up and run the Processor -> IngestionService flow.
    *   **Extensibility:** **Highly extensible.** Add a new `XYZConnector.py` module and potentially a processor step. Wire it into the scheduler or create a new API endpoint to trigger it. The core `IngestionService` and DALs don't need to change much.

5.  **Core Utilities (`core/`)**
    *   **Responsibility:** Cross-cutting concerns. Database client initialization (connections pools), configuration loading (`pydantic-settings` or `.env`), logging setup.

**How This Addresses Extensibility:**

*   **Adding Real Ingestion Sources:** Create a new module in `ingestion/connectors/` and `ingestion/processors/` if needed. Use the existing `Service_Ingestion` or DAL methods to store the data. Minimal impact on API or core retrieval logic. Consider using a task queue (`Celery`, `RQ`, `dramatiq`) for background processing of external sources.
*   **Using Actual Postgres Models:** Implement the `DAL_Postgres_Shared` module. Use environment variables for the connection string. Use SQLAlchemy to map to Dev A's table structures (or raw SQL if needed). The `RetrievalService` can then call `postgres_dal.get_user_details(user_id)` instead of using mock constants.
*   **Adding More Features (e.g., Advanced Preference Analysis):**
    1.  Add new methods to `Service_Preference`.
    2.  These methods might require new DAL functions (e.g., `neo4j_dal.find_voting_patterns(...)`). Implement these in the relevant DAL module (`dal/neo4j_dal.py`).
    3.  Expose the new feature via a new endpoint in the API layer (`api/query_router.py`).
*   **Swapping Databases/Services:** The DAL provides the abstraction. If you wanted to swap Qdrant for Weaviate, you'd primarily rewrite `dal/qdrant_dal.py` to be `dal/weaviate_dal.py` (implementing the same method signatures) and update the client initialization in `core/`. Business logic is largely unaffected. Same for the embedding model via `EmbeddingService`.
*   **Adding LLM-Based Knowledge Extraction (Phase 9):**
    1.  Implement `KnowledgeExtractionService` responsible for calling the LLM API and parsing results.
    2.  Add new methods to `Neo4j DAL` to handle merging extracted entities (Topics, Preferences) and relationships (`MENTIONS`, `STATES_PREFERENCE`).
    3.  Modify `IngestionService` to call `KnowledgeExtractionService` after embedding and before finalizing DB writes. Use the extraction results to call the new Neo4j DAL methods.
    4.  This isolates the LLM dependency and complex extraction logic within the new service and specific DAL updates.

**Prototype Implementation:**

For the TwinCore prototype:

1.  Focus on setting up the FastAPI app structure (`api/`, `services/`, `dal/`, `core/`).
2.  Implement the `EmbeddingService`.
3.  Implement `Qdrant DAL` and `Neo4j DAL`.
4.  Implement `IngestionService` and `RetrievalService` (and basic `PreferenceService` if needed for the queries).
5.  Use mock constants *within* a placeholder `postgres_dal.py` initially.
6.  Implement the API endpoints calling the services.
7.  Build the Streamlit UI to interact with these API endpoints.
8.  The `ingestion/` layer can start simply with the API endpoint handler calling `Service_Ingestion`. You don't need external connectors or task queues for the prototype.

This layered approach provides a solid foundation. You start by implementing the core path (API -> Service -> DAL -> DBs) for your prototype features, and then adding new sources or features becomes a matter of adding specific modules/methods within this structure.

**6. Recommended Directory Structure:**

This structure organizes the codebase according to the layered architecture described above.

```
twincore_backend/
│
├── .venv/                     # Virtual environment files (ignored by Git)
│
├── api/                       # FastAPI API Layer
│   ├── __init__.py
│   ├── models.py              # Pydantic models for request/response validation
│   └── routers/               # API Routers (group endpoints by feature)
│       ├── __init__.py
│       ├── admin_router.py    # e.g., for /seed_data
│       ├── ingest_router.py   # Endpoints for /ingest/...
│       ├── retrieve_router.py # Endpoints for /retrieve/...
│       └── query_router.py    # Endpoints for /query/...
│
├── core/                      # Core utilities, configuration, and setup
│   ├── __init__.py
│   ├── config.py              # Configuration loading (e.g., Pydantic Settings)
│   ├── db_clients.py          # Database client initialization (Qdrant, Neo4j)
│   ├── db_setup.py            # Scripts/functions for DB initialization (collections, constraints)
│   └── mock_data.py           # Mock data definitions for seeding/testing
│   └── utils.py               # Common utility functions (e.g., chunking)
│
├── dal/                       # Data Access Layer
│   ├── __init__.py
│   ├── interfaces.py          # Abstract Base Classes/Protocols for DALs
│   ├── neo4j_dal.py           # Neo4j specific data access logic
│   └── qdrant_dal.py          # Qdrant specific data access logic
│   └── postgres_shared_dal.py # Read-only access logic for shared Postgres (initially mocked)
│
├── services/                  # Business Logic Layer
│   ├── __init__.py
│   ├── embedding_service.py   # Handles text embedding
│   ├── ingestion_service.py   # Orchestrates data ingestion
│   ├── retrieval_service.py   # Orchestrates data retrieval
│   ├── preference_service.py  # Orchestrates preference querying
│   └── knowledge_extraction_service.py # (Phase 9) Extracts knowledge via LLM
│
├── tests/                     # Automated tests (mirrors source structure)
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures (e.g., test clients, DB fixtures)
│   ├── api/                   # API/Contract tests
│   │   └── ...
│   ├── core/                  # Unit tests for core utilities
│   │   └── ...
│   ├── dal/                   # DAL Integration tests
│   │   └── ...
│   ├── services/              # Service Integration tests
│   │   └── ...
│   └── e2e/                   # End-to-end tests
│       └── ...
│
├── .env                       # Environment variables (API keys, DB URIs) - (ignored by Git)
├── .env.example               # Example environment file
├── .gitignore                 # Git ignore rules
├── docker-compose.yml         # Docker Compose for development databases
├── docker-compose.test.yml    # Docker Compose for isolated test databases
├── main.py                    # FastAPI application entry point
├── pytest.ini                 # Pytest configuration
├── README.md                  # Project overview, setup, and usage instructions
├── requirements.txt           # Python package dependencies
└── streamlit_app.py           # Minimal Streamlit UI for verification
```