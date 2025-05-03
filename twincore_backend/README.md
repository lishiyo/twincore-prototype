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

Start the required databases using Docker Compose:

```
docker-compose up -d
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