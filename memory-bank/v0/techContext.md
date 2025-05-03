# TwinCore Prototype - Technical Context

This document summarizes the technical aspects of the TwinCore backend prototype, focusing on Developer B's responsibilities as outlined in the project brief, separation strategy, system patterns, data schema, and testing strategy documents.

**1. Technology Stack:**

*   **Backend Framework:** FastAPI (Python)
*   **Vector Database:** Qdrant (for semantic search)
*   **Graph Database:** Neo4j (for relationship modeling)
*   **Relational Database (Source of Truth/External):** Postgres (Initially mocked/read-only via DAL for core IDs like Users, Projects, Sessions provided by Dev A's system)
*   **Embedding Model:** Sentence Transformers (Specific model TBD, abstracted via `EmbeddingService`)
*   **Knowledge Extraction LLM:** Gemini (or other suitable LLM, via `KnowledgeExtractionService` - Phase 9)
*   **Named Entity Extraction:** Use Gemini flash
*   **API Modeling:** Pydantic
*   **Testing Framework:** `pytest`
*   **Testing Tools:** `pytest-asyncio`, `HTTPX`, `Schemathesis`, `pytest-mock`, `Hypothesis` (optional), `pytest-cov`, Docker/Docker Compose (for test environment DBs)
*   **Configuration:** Environment variables / `.env` files

**2. Architecture (`systemPatterns.md`):**

*   **Pattern:** Layered Architecture (API Layer, Business Logic Layer, Data Access Layer, Ingestion Pipeline, Core Utilities)
*   **API Layer (`api/`):** FastAPI routers, Pydantic models. Defines the contract for Dev A.
*   **Service Layer (`services/`):** Business logic orchestration (Retrieval, Ingestion, Preference, Embedding). Uses Dependency Injection. Includes `KnowledgeExtractionService` (Phase 9) for LLM-based extraction.
*   **Data Access Layer (DAL) (`dal/`):** **Crucial Abstraction.** Hides DB interaction specifics. Modules for Qdrant, Neo4j, and Shared Postgres (read-only interface to Dev A's data).
*   **Ingestion Pipeline (`ingestion/`):** Modular design for handling data intake (API triggers initially, extensible for GDrive, GCal etc. via Connectors/Processors).
*   **Core Utilities (`core/`):** DB Clients, Config, Logging.

**3. Data Schema (`dataSchema.md`):**

*   **Qdrant (`twin_memory` collection):**
    *   Stores text chunk embeddings.
    *   Payload includes: `chunk_id`, `text_content`, `source_type`, `timestamp`, foreign keys (`user_id`, `session_id`, `project_id`, `doc_id`, `message_id`), flags (`is_twin_interaction`, `is_private`), and optional future fields.
*   **Neo4j:**
    *   Models relationships between `User`, `Project`, `Session`, `Document`, `Message` nodes (initially).
    *   Also nodes: `Preference`, `Topic`, `Vote`, `Organization`, `Team`.
    *   Relationships capture participation, authorship, upload source, context, etc. (`PARTICIPATED_IN`, `AUTHORED`, `UPLOADED`, `POSTED_IN`, `PART_OF`).
*   **Postgres (Shared/Mocked):** Provides canonical IDs for `User`, `Project`, `Session`. Accessed via `DAL_Postgres_Shared`.

**4. Testing Strategy (`testingStrategy.md`):**

*   **Approach:** Test-Driven Development (TDD).
*   **Layers:** Unit (pytest, mock), Integration (DAL/Service - pytest, real test DBs), API/Contract (HTTPX, Schemathesis), E2E (Backend - pytest, HTTPX, real test DBs).
*   **Focus:** High priority on Unit, DAL Integration, API/Contract tests.
*   **Environment:** Isolated test databases (Qdrant, Neo4j) managed via Docker.
*   **Goal:** >85% code coverage, 100% test pass rate in CI.

**5. Key Responsibilities (Dev B):**

*   Implement the FastAPI backend service (TwinCore).
*   Define and implement the DAL for Qdrant, Neo4j, and Shared Postgres.
*   Implement core services (Ingestion, Retrieval, Embedding).
*   Manage Qdrant and Neo4j database setup and interaction.
*   Implement the API contract endpoints (`/ingest`, `/retrieve`, `/query`).
*   Develop and maintain the test suite according to the TDD strategy.
*   Ensure data privacy and security within the twin layer.
*   Handle deployment/hosting for the TwinCore service and its databases. 