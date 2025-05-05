# TwinCore Active Context - Sun May  4 21:26:25 PDT 2025

## Current Work Focus
- **Implementing User and Group Context Retrieval (Task 7.6):**
    - **Sub-task 7.6.1 (Complete):** Implemented User Context endpoint (`GET /v1/users/{user_id}/context`) in `user_router.py` with tests.
    - **Sub-task 7.6.2 (In Progress):** Working on Group Context endpoint (`GET /v1/retrieve/group`).
- **Transcript Strategy (Task 7.5):**
    - **Sub-task 7.5.1 (Complete):** Updated Neo4j DAL (`neo4j_dal.py` and tests) to support document metadata updates (`source_uri`, etc.).
    - **Sub-task 7.5.2 (Complete):** Implemented chunk ingestion logic in `DocumentConnector` (`ingestion/connectors/document_connector.py` and tests), ensuring parent `Document` nodes are handled in Neo4j.
    - **Sub-task 7.5.3 (Complete):** Implemented Chunk Ingestion API Endpoint (`/v1/ingest/chunk`).
    - **Sub-task 7.5.4 (Complete):** Implemented Document Metadata Update API Endpoint (`/v1/documents/{doc_id}/metadata`).
- **Plan Adjustment:** Decided to complete Task 7.6 (User and Group Context Retrieval) before moving to Phase 8.

## Project State
### What's Working
- Basic FastAPI application structure
- Root endpoint with test
- Project directory structure
- Python virtual environment
- Configuration using pydantic-settings
- Initial Pydantic models for API contracts
- Full testing setup including pytest, pytest-asyncio, httpx, pytest-mock, pytest-cov, schemathesis
- Docker Compose files for both development and testing environments
- Database client initialization with proper singleton pattern for Qdrant and Neo4j
- Modular database setup utilities in `core/db_setup/` directory
- Testing environment with properly configured test databases
- OpenAI-based Embedding Service with proper error handling
- DAL interfaces defined with clear method signatures for all three database types
- Neo4j DAL implementation with all core CRUD operations and tests
- Qdrant DAL implementation with core operations and integration tests
- Core Ingestion Service implementation with proper integration
- Mock data module with realistic test data
- DataSeederService for handling initial data seeding
- Admin API Router with endpoints for system operations
- DataManagementService for system-wide database operations
- Most End-to-end tests verifying the full data seeding pipeline (excluding document ingestion)
- Comprehensive test running documentation in README.md
- Fixed async function caching with proper singleton pattern
- Proper async dependency functions in router files
- Corrected FastAPI dependency injection throughout the app
- Comprehensive test fixtures for both sync and async tests
- Ingestion API Router with message ingestion endpoint
- MessageConnector in the ingestion/connectors directory
- Full test coverage for the message ingestion flow
- **Task 5.2 Complete:** Document Ingestion Endpoint implementation (connector, service logic, API endpoint) is done.
- **Phase 6 Complete:** All retrieval endpoints are implemented and tested:
    - `RetrievalService` implementation with all methods: `retrieve_context`, `retrieve_enriched_context`, `retrieve_private_memory`, `retrieve_related_content`, `retrieve_by_topic`
    - Retrieval API Router (`/v1/retrieve/*`) with all planned endpoints: context, private memory, related content, and topic retrieval
    - Unit/Integration/API tests for all retrieval components
    - E2E tests for related content retrieval endpoint fixed and now passing
    - All other retrieval endpoint E2E tests verified and passing
- Test isolation improvements:
    - Added `pytest.mark.xdist_group` markers for Qdrant and Neo4j tests
    - Refactored `ensure_collection_exists` fixtures in E2E tests for better Qdrant setup/cleanup per test class
    - Adjusted `clear_test_data` fixture in E2E `conftest.py` to run automatically (`autouse=True`) for consistent cleanup
    - Corrected `async_client` fixture in E2E `conftest.py` using `ASGITransport`
    - Added reusable `use_test_databases` fixture to properly override database connections in E2E tests
- **Phase 7 Complete:** Preference retrieval endpoints implemented and tested:
    - `PreferenceService` with multi-strategy `query_user_preference` method
    - Extended DAL interfaces with `search_user_preferences` and `get_user_preference_statements`
    - Added `/v1/retrieve/preferences` endpoint with proper request/response models and `score_threshold` parameter
    - Comprehensive unit, integration, and E2E tests for all preference components, now passing after debugging
    - Successfully implemented fallback strategies for preference retrieval (explicit preferences, topic-based, vector similarity with thresholding)
- **Twin Interaction Filtering (Task 7.4)**: Updated DAL and Service layers to correctly handle `include_twin_interactions` parameter, including fixing related tests.
- **Transcript Ingestion Strategy Design:** Detailed plan documented in `transcript_strategy.md`.
- **Core Transcript Ingestion Logic (Task 7.5):** Implemented all subtasks including Neo4j DAL updates for metadata, `DocumentConnector` with `ingest_chunk` logic, and API endpoints for chunk ingestion and document metadata updates.
- **User Context Retrieval (Task 7.6.1):** Implemented endpoint for retrieving context specific to a single user with proper privacy and twin interaction filtering.

### What's Broken
- **`test_document_ingestion_end_to_end`:** Still failing with `AssertionError: No document chunks found in Qdrant`. Investigation ongoing.

## Active Decisions & Considerations
- Following the layered architecture defined in systemPatterns.md
- Using the connector pattern for specialized data source handling
- Implementing strict typing with Pydantic models
- Using Test-Driven Development approach consistently
- Using Docker Compose to containerize Qdrant and Neo4j databases
- Separate development and testing database instances to ensure test isolation
- Using proper singleton patterns ONLY for stateless services without event loop dependencies
- Creating fresh instances per request for all services with async database connections
- Providing both sync and async test fixtures for different test scenarios
- Ensuring all API models have proper validation with complete required fields
- Using factory functions for dependency injection rather than direct class dependencies
- Maintaining clear cleanup mechanisms for test resources
- Standardized API path convention to use `/v1` prefix for all endpoints
- Standardized on snake_case for all database property names
- Using `xdist_group` markers and careful fixture design to manage E2E test isolation for shared resources (Qdrant, Neo4j)
- Implementing reusable test fixtures (`use_test_databases`) to ensure proper database connections in E2E tests, overriding dependencies for all relevant routers.
- Created new design for advanced retrieval strategies combining Qdrant and Neo4j for better results
- Defined future expansions for retrieval endpoints to be implemented in Phase 11
- Implemented preference retrieval with multiple fallback strategies and score thresholding to ensure useful and relevant results even with sparse knowledge graphs.
- Refining twin interaction filtering logic (`include_twin_interactions`) across DAL, Services, and eventually APIs.
- Adopted dedicated API endpoints (`/v1/ingest/chunk`, `/v1/documents/{doc_id}/metadata`) for transcript chunk ingestion and metadata updates for clarity.
- Organizing user-specific API endpoints in `user_router.py` while keeping general retrieval endpoints in `retrieve_router.py` for better API organization.

## Tech Stack
- Backend: FastAPI (Python)
- Vector DB: Qdrant 1.7.4 (via Docker)
- Graph DB: Neo4j 5.15.0 (via Docker)
- Embedding: OpenAI (text-embedding-ada-002)
- Knowledge Extraction: Gemini (planned for Phase 9)
- Testing: pytest, httpx, pytest-asyncio, pytest-mock, pytest-cov, Schemathesis
- Configuration: pydantic-settings with environment variables
- Qdrant Client: 1.7.0
- Text Processing: LangChain text splitters (SemanticChunker) - *Note: Currently basic split in DocumentConnector, LangChain planned for refinement*

## Learnings and Insights
- Global singleton instances that depend on event loops cause conflicts in sequential test runs
- Each request should get fresh instances of services that depend on async connections
- FastAPI's dependency injection system is perfect for creating fresh service instances per request
- Creating fresh Neo4j connections for each request ensures resources are properly cleaned up
- Test isolation requires proper resource management at every level of the application
- Only stateless services without event loop dependencies should use global singleton patterns
- Standard `@lru_cache` doesn't work correctly with async functions - a custom singleton pattern is required
- FastAPI's dependency injection system requires careful handling of async/sync boundaries
- Test fixtures should be designed to handle both synchronous and asynchronous testing needs
- API model validation requires complete test data with all required fields
- Proper test documentation improves contributor experience and code quality
- Clear initialization and cleanup mechanisms are essential for reliable tests
- Following the architecture defined in systemPatterns.md leads to cleaner code organization
- Connectors provide a clean way to handle specific data sources while maintaining separation of concerns
- E2E tests using shared resources (like databases) need careful isolation management (`xdist_group`, explicit setup/teardown fixtures, comprehensive dependency overrides).
- Relying on resources created/cleaned up by other tests is brittle; each test/test class should manage its own dependencies
- Correctly configuring async test clients (`httpx.AsyncClient` with `ASGITransport`) is crucial for FastAPI testing
- When testing API endpoints, database connections must be consistent between the test setup and the endpoint execution.
- Proper handling of list parameters in API endpoints requires careful type checking and conversion
- Combining Qdrant (vector search) and Neo4j (graph relationships) can provide more contextually relevant search results
- Cypher query syntax requires careful handling of WITH clauses and relationship traversal paths
- Multi-strategy retrieval approaches (combining explicit relationships, topic-based connections, and vector search) provide robust results.
- Semantic search requires careful thresholding (`score_threshold`) to filter irrelevant results, and relying solely on client parameters may not be sufficient.
- Debugging E2E tests often requires examining logs across multiple layers (test fixtures, API routers, services, DALs).
- Verifying API contracts (status codes, request models) against implementation is crucial during testing.
- Asynchronous operations can introduce timing issues in tests, requiring delays or better synchronization.
- Keeping interfaces and implementations synchronized is crucial and requires diligent testing.
- E2E tests with state changes (like query ingestion) need assertions that verify behavior rather than exact state counts.
- Neo4j `MERGE` requires care when properties might be null; use explicit constraints.
- Separating metadata updates from content ingestion into distinct API endpoints improves clarity.
- Maintaining a clean separation between user-specific endpoints and general retrieval endpoints improves API organization and usability.

## Next Steps
- **Complete Task 7.6:**
    - Implement Sub-task 7.6.2: Group Context Endpoint (`GET /v1/retrieve/group`).
- **Complete Task 7.7:**
    - Implement Sub-task 7.7.1: Refactor Preference Endpoint Path & Parameters.
- **Move to Phase 8:** Verification UI (Streamlit), including transcript simulation.
- Investigate and fix the `AssertionError` in `test_document_ingestion_end_to_end`.
