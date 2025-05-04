# TwinCore Active Context - Sat May  3 22:14:40 PDT 2025

## Current Work Focus
- Phase 6: Retrieval Endpoints
- Completing remaining E2E tests for retrieval endpoints.
- Investigating and fixing the E2E test failure for document ingestion (`test_document_ingestion_end_to_end`).

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
- **Phase 6 In Progress:**
    - RetrievalService implementation (`retrieve_context`, `retrieve_enriched_context`, `retrieve_private_memory`, `retrieve_related_content`, `retrieve_by_topic`).
    - Retrieval API Router (`/v1/retrieve/*`) implementation for context, private memory, related content, and topic retrieval.
    - Unit/Integration/API tests for retrieval components.
- Test isolation improvements:
    - Added `pytest.mark.xdist_group` markers for Qdrant and Neo4j tests.
    - Refactored `ensure_collection_exists` fixtures in E2E tests for better Qdrant setup/cleanup per test class.
    - Adjusted `clear_test_data` fixture in E2E `conftest.py` to run automatically (`autouse=True`) for consistent cleanup.
    - Corrected `async_client` fixture in E2E `conftest.py` using `ASGITransport`.

### What's Broken
- **`test_document_ingestion_end_to_end`:** Failing with `AssertionError: No document chunks found in Qdrant`. Needs investigation.
- **E2E Tests for Retrieval:** Need to be implemented/verified for Tasks 6.2, 6.3, 6.4, 6.5.

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
- Using `xdist_group` markers and careful fixture design to manage E2E test isolation for shared resources (Qdrant, Neo4j).

## Tech Stack
- Backend: FastAPI (Python)
- Vector DB: Qdrant 1.7.4 (via Docker)
- Graph DB: Neo4j 5.15.0 (via Docker)
- Embedding: OpenAI (text-embedding-ada-002)
- Knowledge Extraction: Gemini (planned for Phase 9)
- Testing: pytest, httpx, pytest-asyncio, pytest-mock, pytest-cov, Schemathesis
- Configuration: pydantic-settings with environment variables
- Qdrant Client: 1.7.0
- Text Processing: LangChain text splitters (SemanticChunker)

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
- E2E tests using shared resources (like databases) need careful isolation management (e.g., `xdist_group`, explicit setup/teardown fixtures).
- Relying on resources created/cleaned up by other tests is brittle; each test/test class should manage its own dependencies.
- Correctly configuring async test clients (`httpx.AsyncClient` with `ASGITransport`) is crucial for FastAPI testing.

## Next Steps
- Implement/verify E2E tests for Retrieval Endpoints (Phase 6).
- Investigate and fix the `AssertionError` in `test_document_ingestion_end_to_end`.
- Move to Phase 7: Preference Endpoint.
