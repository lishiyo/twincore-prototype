# TwinCore Active Context - Fri May  2 23:14:46 PDT 2025

## Current Work Focus
- Implementing TwinCore backend prototype
- Completed Task 1.1: Project Initialization
- Completed Task 1.2: Testing Setup
- Completed Task 1.3: Docker Setup for Databases
- Completed Task 2.1: Pydantic API Models
- Completed Task 2.2: Database Client Initialization
- Completed Task 2.3: Qdrant Collection Setup
- Completed Task 2.4: Neo4j Constraints Setup
- Completed Task 3.1: Embedding Service
- Completed Task 3.2: DAL Interfaces (ABCs/Protocols)
- Completed Task 3.3: Neo4j DAL Implementation
- Completed Task 3.4: Qdrant DAL Implementation
- Moving to Task 3.5: Core Ingestion Service Logic

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
- Modular database setup utilities in `core/db_setup/` directory:
  - Qdrant collection setup (`qdrant_setup.py`)
  - Neo4j constraint setup (`neo4j_setup.py`) for all entity types
- Testing environment with properly configured test databases
- OpenAI-based Embedding Service with proper error handling and tests
- DAL interfaces defined with clear method signatures for all three database types:
  - IQdrantDAL: Vector database operations interface
  - INeo4jDAL: Graph database operations interface  
  - IPostgresSharedDAL: Read-only interface for shared Postgres
- Neo4j DAL implementation with all core CRUD operations and tests
- Qdrant DAL implementation with core `upsert`, `search`, and `delete` operations and integration tests

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
- Refactored code to have smaller, more focused modules (< 500 lines)
- Removed synchronous client code in favor of fully async implementations
- Using OpenAI for embedding generation with default model "text-embedding-ada-002"
- Designed DAL interfaces as abstract base classes with clear method signatures for all database operations
- Using Cypher MERGE operations for idempotent node/relationship creation in Neo4j
- Implementing thorough error handling in all database operations
- Setting up test fixtures for clean database state between tests
- Verified Qdrant client 1.7.0 works with server 1.7.4; adjusted `delete_vectors` implementation for compatibility

## Tech Stack
- Backend: FastAPI (Python)
- Vector DB: Qdrant 1.7.4 (via Docker)
- Graph DB: Neo4j 5.15.0 (via Docker)
- Embedding: OpenAI (text-embedding-ada-002)
- Knowledge Extraction: Gemini (Phase 9)
- Testing: pytest, httpx, pytest-asyncio, pytest-mock, pytest-cov, Schemathesis
- Configuration: pydantic-settings with environment variables
- Qdrant Client: 1.7.0

## Next Steps
- Implement core ingestion logic (Task 3.5)
- Develop Ingestion Service
- Write integration tests for Ingestion Service
