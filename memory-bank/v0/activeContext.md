# TwinCore Active Context - Fri May  2 19:39:49 PDT 2025

## Current Work Focus
- Implementing TwinCore backend prototype
- Completed Task 1.1: Project Initialization
- Completed Task 1.2: Testing Setup
- Completed Task 1.3: Docker Setup for Databases
- Completed Task 2.1: Pydantic API Models
- Completed Task 2.2: Database Client Initialization
- Completed Task 2.3: Qdrant Collection Setup (fixed test issue)
- Completed Task 2.4: Neo4j Constraints Setup
- Moving to Task 3.1: Embedding Service

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
- Database client initialization for Qdrant and Neo4j with proper error handling
- Qdrant collection setup utility (`core/db_setup.py`) and integration test
- Neo4j constraint setup utility with complete constraint set for all entity types
- Testing environment with properly configured test databases

### What's Broken
- Nothing currently broken

## Active Decisions & Considerations
- Following the layered architecture defined in systemPatterns.md
- Implementing strict typing with Pydantic models
- Using Test-Driven Development approach consistently
- Using Docker Compose to containerize Qdrant and Neo4j databases
- Separate development and testing database instances to ensure test isolation
- Using LRU cache for database clients to implement singleton pattern
- Defined Qdrant collection `twin_memory` with vector size 384 and Cosine distance
- Added flexible CollectionInfo attribute checking to handle potential Qdrant API changes
- Implementing dependency injection pattern for better testability (e.g., optional driver parameter)
- Using latest Neo4j 5.15.0 with proper configuration parameters

## Tech Stack
- Backend: FastAPI (Python)
- Vector DB: Qdrant (configured via Docker)
- Graph DB: Neo4j (configured via Docker)
- Embedding: Sentence Transformers (not yet implemented - assumed size 384 for Qdrant)
- Knowledge Extraction: Gemini (Phase 9)
- Testing: pytest, httpx, pytest-asyncio, pytest-mock, pytest-cov, Schemathesis
- Configuration: pydantic-settings with environment variables

## Next Steps
- Set up Embedding Service (Task 3.1)
- Start implementing core ingestion logic
