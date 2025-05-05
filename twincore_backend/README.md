# TwinCore Backend

Digital Twin backend service for context retrieval and user representation, using Qdrant for vector storage and Neo4j for knowledge graph representation.

## Project Overview

TwinCore is a prototype backend service that demonstrates the Digital Twin's ability to ingest diverse data (documents, chat messages) and fulfill the core API contract for context retrieval (group & private) and user representation, using Qdrant for vector database and Neo4j for knowledge graph.

### Core Features

- Ingest and process user messages and documents
- Store embeddings in Qdrant vector database
- Represent relationships in Neo4j graph database
- Retrieve relevant context based on queries
- Support private user memory and preferences

## Setup Instructions

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for running Neo4j and Qdrant)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on the example variables in `.env.example`

### Running the Database Services

#### Development Environment

Start the required databases for development using Docker Compose:

```
docker-compose up -d
```

This will start:
- Qdrant on ports 6333 (API) and 6334 (Web UI)
- Neo4j on ports 7474 (Browser UI) and 7687 (Bolt protocol)

To check the status:
```
docker-compose ps
```

To view logs:
```
docker-compose logs -f
```

To stop the services:
```
docker-compose down
```

#### Testing Environment

For testing, we use a separate docker-compose file to create isolated instances:

```
docker-compose -f docker-compose.test.yml up -d
```

This starts:
- Qdrant test instance on port 7333 (API) and 7334 (Web UI)
- Neo4j test instance on ports 8474 (Browser UI) and 8687 (Bolt protocol)

The test databases are configured to use in-memory storage for faster testing.

To stop the test services:
```
docker-compose -f docker-compose.test.yml down
```

### Running the API

Start the FastAPI application:

```
python main.py
```

Or using uvicorn directly:

```
uvicorn main:app --reload --port 8000
```

The API will be available at http://localhost:8000. API documentation is available at http://localhost:8000/docs.

### Running Tests

### Setup Test Environment

Before running tests, start the test database containers:

```bash
docker-compose -f docker-compose.test.yml up -d
```

Verify the test containers are running:

```bash
docker-compose -f docker-compose.test.yml ps
```

### Running All Tests

Run the entire test suite:

```bash
pytest
```

### Running Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests 
pytest tests/integration/

# Run only end-to-end tests
pytest tests/e2e/
```

### Database Integration Tests

```bash
# Test Qdrant collection setup
pytest tests/core/test_db_setup.py::test_setup_qdrant_collection_creates_collection

# Test Neo4j constraint setup
pytest tests/core/test_db_setup.py::test_setup_neo4j_constraints_creates_constraints

# Test idempotency
pytest tests/core/test_db_setup.py::test_setup_qdrant_collection_is_idempotent
pytest tests/core/test_db_setup.py::test_setup_neo4j_constraints_is_idempotent
```

### DAL Implementation Tests

```bash
# Neo4j DAL tests
pytest tests/dal/test_neo4j_dal.py

# Qdrant DAL tests
pytest tests/dal/test_qdrant_dal.py
```

### Service Tests

```bash
# Embedding Service tests
pytest tests/services/test_embedding_service.py

# Ingestion Service tests
pytest tests/services/test_ingestion_service.py

# Data Seeder Service tests
pytest tests/services/test_data_seeder_service.py
```

### End-to-End Tests

```bash
# Test data seeding end-to-end
pytest tests/e2e/test_seed_data_e2e.py
```

### Cleaning Up Test Environment

When finished testing, stop the test containers:

```bash
docker-compose -f docker-compose.test.yml down
```

## Project Structure

- `api/`: FastAPI endpoints and request/response models
- `core/`: Core utilities, configuration, and database setup
- `dal/`: Data Access Layer for database interactions
- `services/`: Business logic services
- `tests/`: Test suite 
- `docker-compose.yml`: Docker configuration for development databases
- `docker-compose.test.yml`: Docker configuration for isolated test databases 