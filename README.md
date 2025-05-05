# TwinCore Prototype

A backend prototype for the TwinCore memory and context retrieval system.

## Project Overview

This project consists of two main components:
- **TwinCore Backend**: A FastAPI application that provides API endpoints for ingesting, storing, and retrieving context data using vector and graph databases.
- **TwinCore Frontend**: A Streamlit verification UI that simulates client interactions with the backend API.

## Prerequisites

- Python 3.9+ 
- Docker and Docker Compose
- Git

## Setup and Running

### 1. Clone the Repository

```bash
git clone [repository-url]
cd twincore-backend-prototype
```

### 2. Backend Setup

#### Database Setup with Docker

The backend requires Qdrant (vector database) and Neo4j (graph database) instances. Use Docker Compose to start them:

```bash
cd twincore_backend
docker-compose up -d
```

This will start:
- Qdrant on port 6333 (HTTP) and 6334 (gRPC)
- Neo4j on port 7474 (HTTP), 7687 (Bolt), and 7473 (HTTPS)

#### Python Environment Setup

```bash
cd twincore_backend

# Create and activate a virtual environment
python -m venv .venv

# On Linux/Mac
source .venv/bin/activate 

# On Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Environment Variables

Create a `.env` file in the `twincore_backend` directory with your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key
```

#### Running the Backend

```bash
cd twincore_backend

# Make sure your virtual environment is activated
# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

The backend API will be available at http://localhost:8000, and the API documentation at http://localhost:8000/docs.

#### Seeding Data (Optional)

To seed the database with initial test data:

```bash
curl -X POST http://localhost:8000/api/seed_data
```

Or use the "Seed Data" button in the Streamlit frontend.

### 3. Frontend Setup

```bash
cd twincore_frontend

# Create and activate a virtual environment (optional but recommended)
python -m venv venv

# On Linux/Mac
source venv/bin/activate

# On Windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the Streamlit app
streamlit run streamlit_app.py
```

The Streamlit app will be available at http://localhost:8501.

## Using the Application

1. Ensure both the backend server and the frontend Streamlit app are running.
2. Open the Streamlit app in your browser (http://localhost:8501).
3. Select a user from the dropdown in the sidebar.
4. Use the different tabs to simulate various API interactions:
   - **Canvas Agent**: Simulate context and preference retrieval requests
   - **Group Chat**: Simulate sending messages in a group chat
   - **User <> Twin**: Simulate user-twin interactions via private memory
   - **Document Upload**: Simulate document uploads
   - **Transcript**: Simulate transcript chunk ingestion
   - **DB Stats**: View database statistics 

## Common Issues and Troubleshooting

- **Connection Refused Errors**: Ensure that the backend API is running on port 8000 before attempting to use the Streamlit frontend.
- **Database Connection Errors**: Make sure Docker is running and the database containers are up. Check with `docker-compose ps`.
- **Missing Data in Responses**: If you've just started the backend, you may need to seed the database first via the `/api/seed_data` endpoint.
- **OpenAI API Errors**: Ensure your OpenAI API key is correctly set in the `.env` file.

## Running Tests

```bash
cd twincore_backend

# Run all tests
pytest

# Run with coverage report
pytest --cov=twincore_backend

# Run specific test file
pytest tests/path/to/test_file.py
```

## Project Structure

```
twincore-backend-prototype/
├── twincore_backend/    # Backend FastAPI application
│   ├── api/             # API endpoints
│   ├── core/            # Core utilities
│   ├── dal/             # Data Access Layer
│   ├── ingestion/       # Ingestion connectors
│   ├── services/        # Business logic
│   └── tests/           # Test suite
└── twincore_frontend/   # Frontend Streamlit app
    ├── streamlit_app.py # Main Streamlit application
    └── requirements.txt # Frontend dependencies
```

## License

[License information] 