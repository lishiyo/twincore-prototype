# TwinCore Active Context - Sat May  3 18:17:49 PDT 2025

## Current Work Focus
- Implementing TwinCore backend prototype
- Completed Task 1.1 through Task 4.4
- Fixed critical backend framework issues:
  - Async function caching
  - Database client connection management
  - Dependency injection configuration
  - Test failures and fixtures
  - API model validation
- Moving to Phase 5: Ingestion Endpoints (`/api/ingest/*`)

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
- End-to-end tests verifying the full data seeding pipeline
- Comprehensive test running documentation in README.md
- Fixed async function caching with proper singleton pattern
- Proper async dependency functions in router files
- Corrected FastAPI dependency injection throughout the app
- Comprehensive test fixtures for both sync and async tests

### What's Broken
- Nothing currently broken - all tests passing

## Active Decisions & Considerations
- Following the layered architecture defined in systemPatterns.md
- Implementing strict typing with Pydantic models
- Using Test-Driven Development approach consistently
- Using Docker Compose to containerize Qdrant and Neo4j databases
- Separate development and testing database instances to ensure test isolation
- Using proper singleton patterns for database clients instead of LRU cache for async functions
- Providing both sync and async test fixtures for different test scenarios
- Ensuring all API models have proper validation with complete required fields
- Using factory functions for dependency injection rather than direct class dependencies
- Maintaining clear cleanup mechanisms for test resources
- Standardized API path convention to use `/v1` prefix for all endpoints
- Standardized on snake_case for all database property names

## Tech Stack
- Backend: FastAPI (Python)
- Vector DB: Qdrant 1.7.4 (via Docker)
- Graph DB: Neo4j 5.15.0 (via Docker)
- Embedding: OpenAI (text-embedding-ada-002)
- Knowledge Extraction: Gemini (planned for Phase 9)
- Testing: pytest, httpx, pytest-asyncio, pytest-mock, pytest-cov, Schemathesis
- Configuration: pydantic-settings with environment variables
- Qdrant Client: 1.7.0

## Learnings and Insights
- Standard `@lru_cache` doesn't work correctly with async functions - a custom singleton pattern is required
- FastAPI's dependency injection system requires careful handling of async/sync boundaries
- Test fixtures should be designed to handle both synchronous and asynchronous testing needs
- API model validation requires complete test data with all required fields
- Proper test documentation improves contributor experience and code quality
- Clear initialization and cleanup mechanisms are essential for reliable tests

## Next Steps
- Implement Task 5.1: Ingest Message Endpoint
- Implement Task 5.2: Ingest Document Endpoint
