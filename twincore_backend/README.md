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
4. Create a `.env` file based on the example variables in `core/config.py`

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
uvicorn main:app --reload
```

The API will be available at http://localhost:8000. API documentation is available at http://localhost:8000/docs.

### Running Tests

```
pytest
```

## Project Structure

- `api/`: FastAPI endpoints and request/response models
- `core/`: Core utilities, configuration, and database setup
- `dal/`: Data Access Layer for database interactions
- `services/`: Business logic services
- `tests/`: Test suite 
- `docker-compose.yml`: Docker configuration for development databases
- `docker-compose.test.yml`: Docker configuration for isolated test databases 