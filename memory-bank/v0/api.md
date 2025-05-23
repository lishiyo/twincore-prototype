# TwinCore Digital Twin API Specification - v1

This document outlines the API endpoints provided by the Digital Twin Layer (Dev B) for interaction with the Canvas/Orchestration Layer (Dev A).

**Base URL:** `/v1` (Assumed prefix for all endpoints)

**Authentication:** All endpoints will require Bearer token authentication (details TBD).

**Data Models:** All request and response bodies should be formalized using Pydantic models defined in `twincore_backend/api/models.py`.

---

## 1. Admin Endpoints

### 1.1 Seed Data - COMPLETED

*   **Endpoint:** `POST /v1/admin/api/seed_data`
*   **Description:** Seeds the system with initial mock data for testing and demonstration purposes.
*   **Request Body:** None
*   **Responses:**
    *   `202 Accepted`: Seeding operation started.
      ```json
      {
        "status": "success",
        "message": "Successfully seeded X items",
        "data": {
          "total": 15,
          "counts_by_type": {
            "message": 8,
            "document_chunk": 7
          }
        }
      }
      ```
    *   `500 Internal Server Error`: If seeding operation fails. Details in response body.
    *   `401 Unauthorized`: Missing or invalid authentication token.

### 1.2 Clear Data - COMPLETED

*   **Endpoint:** `POST /v1/admin/api/clear_data`
*   **Description:** Clears all data from the system. This is a destructive operation useful for testing, development, or resetting the system to a clean state.
*   **Request Body:** None
*   **Responses:**
    *   `202 Accepted`: Clearing operation started.
      ```json
      {
        "status": "success",
        "message": "All data successfully cleared",
        "data": {
          "details": {
            "neo4j": {
              "nodes_deleted": 25,
              "relationships_deleted": 40
            },
            "qdrant": {
              "vectors_deleted": 30,
              "collection": "twin_memory"
            }
          }
        }
      }
      ```
    *   `500 Internal Server Error`: If clearing operation fails. Details in response body.
    *   `401 Unauthorized`: Missing or invalid authentication token.

### 1.3 Get Qdrant Statistics - COMPLETED

*   **Endpoint:** `GET /v1/admin/api/stats/qdrant`
*   **Description:** Retrieves statistics about the Qdrant vector database collection (`twin_memory`).
*   **Request Body:** None
*   **Responses:**
    *   `200 OK`: Successfully retrieved Qdrant statistics.
      ```json
      {
        "collection_name": "twin_memory",
        "vectors_count": 150,
        "points_count": 150,
        "segments_count": 1,
        "status": "green",
        "optimizer_status": "ok"
        // ... other Qdrant collection info fields
      }
      ```
    *   `500 Internal Server Error`: If retrieving stats fails. Details in response body.
    *   `401 Unauthorized`: Missing or invalid authentication token.

### 1.4 Get Neo4j Statistics - COMPLETED

*   **Endpoint:** `GET /v1/admin/api/stats/neo4j`
*   **Description:** Retrieves statistics about the Neo4j graph database, including node counts by label and relationship counts by type.
*   **Request Body:** None
*   **Responses:**
    *   `200 OK`: Successfully retrieved Neo4j statistics.
      ```json
      {
        "node_labels": {
          "User": 5,
          "Chunk": 150,
          "Document": 10,
          "Project": 2,
          "Session": 3,
          "Topic": 25
        },
        "relationship_types": {
          "PART_OF": 140,
          "BELONGS_TO": 150,
          "MENTIONS": 50,
          "CREATED_IN": 150
          // ... other relationship types and counts
        },
        "total_nodes": 195,
        "total_relationships": 490
      }
      ```
    *   `500 Internal Server Error`: If retrieving stats fails. Details in response body.
    *   `401 Unauthorized`: Missing or invalid authentication token.

---

## 2. Ingestion Endpoints

### 2.1 Ingest Message - COMPLETED

*   **Endpoint:** `POST /v1/ingest/message`
*   **Description:** Ingests a single message into the user's memory within a specific session context. The service handles embedding and storage.
*   **Request Body:**
    ```json
    {
      "user_id": "string (uuid)", // REQUIRED: ID of the user who sent the message
      "session_id": "string (uuid)", // REQUIRED: ID of the session the message belongs to
      "project_id": "string (uuid), optional", // Optional: Project ID, can often be derived from session_id
      "message_id": "string (uuid), optional", // Optional: ID of the message from the source system (e.g., Canvas chat)
      "message_text": "string", // REQUIRED: The actual text content of the message
      "timestamp": "string (isoformat)", // REQUIRED: Time the message was created/sent
      "metadata": "object, optional" // Optional: Any additional source-specific metadata
    }
    ```
*   **Responses:**
    *   `202 Accepted`: Message accepted for processing. (Processing happens asynchronously).
      ```json
      {
        "status": "accepted",
        "message": "Message received and queued for ingestion."
      }
      ```
    *   `400 Bad Request`: Invalid request body (e.g., missing required fields, invalid format). Details in response body.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `422 Unprocessable Entity`: Validation error (FastAPI default).

### 2.2 Ingest Document (Text Content) - COMPLETED

*   **Endpoint:** `POST /v1/ingest/document`
*   **Description:** Ingests **pre-extracted text content** of a document. The service handles chunking, embedding, and storage, associating it with the user and appropriate context (project/session). Use this when the calling service already has the document's text. 
*   **Request Body (application/json):**
    ```json
    {
      "user_id": "string (uuid)", // REQUIRED: ID of the user associated with the document (e.g., owner/uploader)
      "doc_id": "string (uuid)", // REQUIRED: Unique ID for this document (can be generated by caller or service)
      "project_id": "string (uuid), optional", // Context: Project ID, required if session_id is null
      "session_id": "string (uuid), optional", // Context: Session ID, required if project_id is null
      "text": "string", // REQUIRED: Full text content of the document.
      "source_uri": "string, optional", // Optional: URI or identifier for the original document location.
      "timestamp": "string (isoformat)", // REQUIRED: Time the document was created/uploaded/modified
      "metadata": "object, optional" // Optional: Additional metadata (e.g., original filename, permissions)
    }
    ```
    *Note: At least one of `project_id` or `session_id` must be provided.*
*   **Responses:**
    *   `202 Accepted`: Document text accepted for processing.
      ```json
      {
        "status": "accepted",
        "message": "Document text received and queued for ingestion."
      }
      ```
    *   `400 Bad Request`: Invalid request body.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `422 Unprocessable Entity`: Validation error (FastAPI default).

### 2.3 Ingest Document (File Upload)

*   **Endpoint:** `POST /ingest/document/upload`
*   **Description:** Ingests a document by **direct file upload**. The service handles file reading, text extraction (if necessary, e.g., for PDF), chunking, embedding, and storage.
*   **Request Body (multipart/form-data):**
    *   `file`: The document file itself (e.g., `.txt`, `.md`, `.pdf`). REQUIRED.
    *   `user_id`: `string (uuid)`. REQUIRED: ID of the user uploading the document.
    *   `doc_id`: `string (uuid), optional`. Optional: Provide if you have a specific ID; otherwise, the service can generate one.
    *   `project_id`: `string (uuid), optional`. Context: Project ID.
    *   `session_id`: `string (uuid), optional`. Context: Session ID.
    *   `timestamp`: `string (isoformat), optional`. Optional: Time associated with the document; defaults to now if omitted.
    *   `metadata`: `string (JSON encoded), optional`. Optional: JSON string containing additional metadata.
    *Note: At least one of `project_id` or `session_id` must be provided for context.*
*   **Responses:**
    *   `202 Accepted`: File accepted for processing.
      ```json
      {
        "status": "accepted",
        "message": "File received and queued for ingestion.",
        "doc_id": "string (uuid)" // The ID used for the document (either provided or generated)
      }
      ```
    *   `400 Bad Request`: Missing required form fields (`file`, `user_id`, context ID), invalid metadata JSON.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `413 Payload Too Large`: File exceeds maximum allowed size.
    *   `415 Unsupported Media Type`: File type is not supported for text extraction (e.g., image without OCR).
    *   `422 Unprocessable Entity`: Validation error.

### 2.4 Ingest Chunk (e.g., Transcript Snippet) - COMPLETED

*   **Endpoint:** `POST /v1/ingest/chunk`
*   **Description:** Ingests a single chunk of text, typically a transcript snippet, associated with a parent document (like a full transcript). Handles embedding and storage. Designed for streaming individual utterances or small text pieces belonging to a larger logical document.
*   **Request Body (application/json):**
    ```json
    {
      "user_id": "string (uuid)", // REQUIRED: Speaker of the utterance or author of the chunk
      "session_id": "string (uuid)", // REQUIRED: Session context
      "doc_id": "string (uuid)", // REQUIRED: The consistent ID of the parent Document this chunk belongs to
      "project_id": "string (uuid), optional", // Optional project context
      "chunk_id": "string (uuid), optional", // Optional: Unique ID for this specific chunk from source system
      "text": "string", // REQUIRED: The text content of the chunk/utterance
      "timestamp": "string (isoformat)", // REQUIRED: Time the chunk/utterance occurred or was created
      "metadata": "object, optional" // Optional: Any additional source-specific metadata (e.g., sequence number)
    }
    ```
*   **Responses:**
    *   `202 Accepted`: Chunk accepted for processing.
      ```json
      {
        "status": "accepted",
        "message": "Chunk received and queued for ingestion."
      }
      ```
    *   `400 Bad Request`: Invalid request body (e.g., missing required fields, invalid format).
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `422 Unprocessable Entity`: Validation error (FastAPI default).

---

## 3. Retrieval Endpoints

### 3.1 Retrieve Context (Shared Scope) - COMPLETED

*   **Endpoint:** `GET /v1/retrieve/context`
*   **Description:** Retrieves relevant text chunks based on a semantic query within a **shared scope** (project or session). This endpoint focuses on the collective *public* content within that scope. By default, this excludes content generated during direct user-twin interactions (use the `include_messages_to_twin` parameter to include them) and the user's private docs. Can optionally enrich results with related graph context. **Note**: For user-specific context including their private docs and interactions, use `GET /user/{user_id}/context`. For multiple users, use `GET /retrieve/group`.
*   **Query Parameters:**
    *   `query_text`: `string` - REQUIRED: The natural language query for semantic search.
    *   `session_id`: `string (uuid), optional` - Scope: Filter by session. **One of `session_id` or `project_id` must be provided.**
    *   `project_id`: `string (uuid), optional` - Scope: Filter by project. **One of `session_id` or `project_id` must be provided.**
    *   `limit`: `integer, optional (default: 10)` - Maximum number of chunks to return.
    *   `include_messages_to_twin`: `boolean, optional (default: False)` - If true, results will include chunks where `is_twin_interaction` is true.
    *   `include_graph`: `boolean, optional (default: False)` - If true, results will be enriched with related graph context (e.g., project details, participants). This may increase response time.
*   **Responses:**
    *   `200 OK`: Successfully retrieved context chunks.
      ```json
      {
        "chunks": [
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "score": "float",
            "metadata": {
              "source_type": "string (e.g., 'message', 'document')",
              "user_id": "string (uuid)",
              "session_id": "string (uuid), optional",
              "project_id": "string (uuid), optional",
              "doc_id": "string (uuid), optional",
              "message_id": "string (uuid), optional",
              "timestamp": "string (isoformat)",
              "project_context": { /* ... */ },
              "session_participants": [ /* ... */ ]
            }
          }
        ],
        "total": "integer"
      }
      ```
    *   `400 Bad Request`: Missing required query parameters (`query_text`, scope ID) or invalid parameters.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If specified scope IDs do not exist (optional check).

### 3.2 Retrieve Preferences - MOVED
*   **This endpoint has been moved to `GET /v1/users/{user_id}/preferences` (see Section 3.x below).**

### 3.3 Retrieve Group Context - COMPLETED

*   **Endpoint:** `GET /v1/retrieve/group`
*   **Description:** Retrieves relevant information (experiences, preferences, or memories) from **multiple participants** associated with a defined group scope (session, project, or team) based on a query. This endpoint aims to gather context reflecting the perspectives of individuals within the group. By default, this *includes* content marked as private to those users and messages generated during direct user-twin interactions for those users within the scope.
*   **Query Parameters:**
    *   `session_id`: `string (uuid), optional` - Scope: Required if `project_id` and `team_id` are not provided.
    *   `project_id`: `string (uuid), optional` - Scope: Required if `session_id` and `team_id` are not provided.
    *   `team_id`: `string (uuid), optional` - Scope: Required if `session_id` and `project_id` are not provided.
    *   `query_text`: `string` - REQUIRED: The natural language query for semantic search across the group participants' relevant data.
    *   `limit_per_user`: `integer, optional (default: 5)` - Maximum results per user included in the response.
    *   `include_messages_to_twin`: `boolean, optional (default: True)` - If true, results for each user will include chunks where `is_twin_interaction` is true.
    *   `include_private`: `boolean, optional (default: True)` - If true, include chunks marked as private associated with the users in the scope.
    *   `metadata`: `dict, optional` - Advanced filtering options (TBD - e.g., filter for explicit votes within the group).
*   **Responses:**
    *   `200 OK`: Successfully retrieved group context, grouped by user.
      ```json
      {
        "group_results": [
          {
            "user_id": "string (uuid)",
            "results": [ // Array of context chunks for this user
              {
                "chunk_id": "string (uuid)",
                "text": "string",
                "score": "float",
                "metadata": { ... } // Similar to context retrieval metadata
              }
              // ... up to limit_per_user
            ]
          }
          // ... entry for each relevant user in the group
        ]
      }
      ```
    *   `400 Bad Request`: Missing required query parameter (`query_text`), missing scope ID, or more than one scope ID provided.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If the specified scope ID (`session_id`, `project_id`, `team_id`) does not exist or has no participants.

### 3.4 Retrieve Related Content (Graph Traversal) - COMPLETED

*   **Endpoint:** `GET /retrieve/related_content`
*   **Description:** Retrieves content chunks related to a specific starting chunk by traversing the Neo4j graph based on relationship types. This method does **not** use Qdrant vector similarity search.
*   **Query Parameters:**
    *   `chunk_id`: `string` - REQUIRED: The ID of the starting chunk for traversal.
    *   `limit`: `integer, optional (default: 10)` - Maximum number of related chunks to return.
    *   `include_private`: `boolean, optional (default: False)` - Whether to include chunks marked as private.
    *   `max_depth`: `integer, optional (default: 2)` - Maximum number of relationship hops to traverse.
    *   `relationship_types`: `List[str], optional` - A list of relationship types (e.g., `MENTIONS`, `PART_OF`) to follow during traversal. If omitted, all relationship types are considered.
*   **Responses:**
    *   `200 OK`: Successfully retrieved related context chunks. The response format follows the `ChunksResponse` model, similar to `/retrieve/context`, but without relevance scores. The `metadata` within each chunk may contain `outgoing_relationships` and `incoming_relationships` lists detailing how it's connected.
      ```json
      {
        "chunks": [
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "source_type": "string",
            "timestamp": "string (isoformat)",
            "user_id": "string (uuid), optional",
            // ... other standard chunk fields
            "metadata": {
              // ... other metadata
              "outgoing_relationships": [
                {"type": "MENTIONS", "target_id": "...", "target_type": "Topic"}
              ],
              "incoming_relationships": [
                 {"type": "PART_OF", "source_id": "...", "source_type": "Document"}
              ]
            }
          }
          // ... more results
        ],
        "total": "integer"
      }
      ```
    *   `400 Bad Request`: Missing required query parameter (`chunk_id`).
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If the starting `chunk_id` does not exist.

### 3.5 Retrieve by Topic - COMPLETED

*   **Endpoint:** `GET /retrieve/topic`
*   **Description:** Retrieves content chunks related to a specific topic name. Primarily uses Neo4j graph relationships (e.g., `MENTIONS`), potentially falling back to vector search if no direct graph connections are found.
*   **Query Parameters:**
    *   `topic_name`: `string` - REQUIRED: The name of the topic to query for.
    *   `limit`: `integer, optional (default: 10)` - Maximum number of chunks to return.
    *   `user_id`: `string (uuid), optional` - Filter results by user ID.
    *   `project_id`: `string (uuid), optional` - Filter results by project ID.
    *   `session_id`: `string (uuid), optional` - Filter results by session ID.
    *   `include_private`: `boolean, optional (default: False)` - Whether to include private content.
*   **Responses:**
    *   `200 OK`: Successfully retrieved topic-related context chunks. The response format follows the `ChunksResponse` model. Chunks retrieved via graph match might include a `topic` object in their metadata. Chunks retrieved via fallback vector search will have a `score`.
      ```json
      {
        "chunks": [
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "source_type": "string",
            "timestamp": "string (isoformat)",
            // ... other standard chunk fields
            "score": "float, optional", // Present if fallback vector search was used
            "metadata": {
              // ... other metadata
              "topic": { // Present if retrieved via graph relationship
                "name": "string", 
                "description": "string, optional" 
                // ... other topic properties
              } 
            }
          }
          // ... more results
        ],
        "total": "integer"
      }
      ```
    *   `400 Bad Request`: Missing required query parameter (`topic_name`).
    *   `401 Unauthorized`: Missing or invalid authentication token.

### 3.6 Retrieve Private Memory (User Interaction) - MOVED

*   **This endpoint is deprecated and will be removed. Use `POST /v1/users/{user_id}/private_memory` instead.**
*   **Endpoint:** `POST /v1/retrieve/private_memory`
*   **Description:** Retrieves a user's private memory based on semantic search **AND ingests the query itself** as a twin interaction (marked with `is_twin_interaction: true`). This endpoint is designed specifically for the user's direct interaction loop with their twin simulation. By default, the retrieval **includes** previous user messages to the twin. Set `include_messages_to_twin` to false in the request body to exclude them. **Note:** For read-only queries *about* a user without ingestion, use `GET /v1/users/{user_id}/context`.
*   **Request Body:**
    ```json
    {
      "user_id": "string (uuid)", // REQUIRED (Deprecated - will be moved to path parameter)
      "query_text": "string", // REQUIRED: The query for semantic search
      "project_id": "string (uuid), optional", // Optional context filter
      "session_id": "string (uuid), optional", // Optional context filter
      "limit": "integer, optional (default: 10)",
      "include_messages_to_twin": "boolean, optional (default: True)" // Control inclusion of interaction history
    }
    ```
*   **Query Parameters:**
    *   `include_graph`: `boolean, optional (default: False)` - If true, results will be enriched with related graph context.
*   **Responses:**
    *   `200 OK`: Successfully retrieved private memory chunks.
      ```json
      {
        "chunks": [
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "score": "float", // Relevance score from Qdrant
            "metadata": {
              "source_type": "string (e.g., 'message', 'document')",
              "user_id": "string (uuid)",
              "session_id": "string (uuid), optional",
              "project_id": "string (uuid), optional",
              "doc_id": "string (uuid), optional",
              "message_id": "string (uuid), optional",
              "timestamp": "string (isoformat)",
              "outgoing_relationships": [ /* ... */ ],
              "incoming_relationships": [ /* ... */ ]
            }
          }
        ],
        "total": "integer"
      }
      ```
    *   `400 Bad Request`: Invalid request body.
    *   `401 Unauthorized`: Missing or invalid authentication token.

### 3.7 Retrieve Entity Connections (Graph Traversal)

*   **Endpoint:** `GET /retrieve/entity_connections`
*   **Description:** Provides a snapshot of how a specific entity (identified by its primary ID) is connected within the Neo4j knowledge graph. Useful for visualization or exploration. This does NOT include Qdrant vector search.
*   **Query Parameters:**
    *   `entity_id`: `string` - REQUIRED: The primary ID of the starting entity (e.g., a `chunk_id`, `doc_id`, `user_id`, `topic_name`).
    *   `max_depth`: `integer, optional (default: 1)` - Maximum number of relationship hops to traverse from the starting entity.
    *   `limit`: `integer, optional (default: 25)` - Maximum number of connections (nodes + relationships) to return.
*   **Responses:**
    *   `200 OK`: Successfully retrieved graph connections.
      ```json
      {
        "start_node": { "id": "string", "labels": ["string"], "properties": { ... } },
        "connections": [
          {
            "node": { "id": "string", "labels": ["string"], "properties": { ... } },
            "relationship": { "type": "string", "direction": "string ('outgoing'|'incoming')", "properties": { ... } },
            "depth": "integer"
          }
          // ... more connections
        ],
        "total_connections": "integer"
      }
      ```
    *   `400 Bad Request`: Missing required query parameter (`entity_id`).
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If the starting `entity_id` does not exist in Neo4j.

### 3.8 Retrieve Timeline

*   **Endpoint:** `GET /v1/retrieve/timeline`
*   **Description:** Retrieves a chronologically sorted list of content chunks (messages, document chunks) within a specified context. By default, this excludes content generated during direct user-twin interactions. Use the `include_messages_to_twin` parameter to include them.
*   **Query Parameters:**
    *   `user_id`: `string (uuid), optional` - Filter by user.
    *   `project_id`: `string (uuid), optional` - Filter by project.
    *   `session_id`: `string (uuid), optional` - Filter by session.
    *   `start_time`: `string (isoformat), optional` - Filter items created after this time.
    *   `end_time`: `string (isoformat), optional` - Filter items created before this time.
    *   `limit`: `integer, optional (default: 50)` - Maximum number of items to return.
    *   `sort_order`: `string ('asc'|'desc'), optional (default: 'desc')` - Sort by timestamp ascending or descending.
    *   `include_messages_to_twin`: `boolean, optional (default: False)` - If true, results will include chunks where `is_twin_interaction` is true.
*   **Responses:**
    *   `200 OK`: Successfully retrieved timeline chunks. The response format follows the `ChunksResponse` model, sorted by timestamp. Relevance scores are typically not applicable here.
      ```json
      {
        "chunks": [ // Sorted by timestamp
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "source_type": "string",
            "timestamp": "string (isoformat)",
            "user_id": "string (uuid), optional",
            // ... other standard chunk fields
            "metadata": { ... }
          }
        ],
        "total": "integer"
      }
      ```
    *   `400 Bad Request`: Invalid time format or filter combination.
    *   `401 Unauthorized`: Missing or invalid authentication token.

### 3.9 Suggest Related Entities

*   **Endpoint:** `GET /suggest/related_entities`
*   **Description:** Suggests related entities (Topics, Documents, Users) based on either a specific content chunk or a natural language query, leveraging graph connections.
*   **Query Parameters:**
    *   `chunk_id`: `string, optional` - Context: ID of a specific chunk to find related entities for.
    *   `query_text`: `string, optional` - Context: A natural language query to find related entities for (performs semantic search first).
    *   `limit_topics`: `integer, optional (default: 5)` - Max number of suggested topics.
    *   `limit_docs`: `integer, optional (default: 3)` - Max number of suggested documents.
    *   `limit_users`: `integer, optional (default: 3)` - Max number of suggested users.
    *Note: Exactly one of `chunk_id` or `query_text` must be provided.*
*   **Responses:**
    *   `200 OK`: Successfully generated suggestions.
      ```json
      {
        "suggestions": {
          "topics": [
            { "id": "string", "name": "string", "relevance_score": "float, optional" }
          ],
          "documents": [
            { "id": "string (uuid)", "name": "string, optional", "relevance_score": "float, optional" }
          ],
          "users": [
            { "id": "string (uuid)", "name": "string, optional", "relevance_score": "float, optional" }
          ]
        }
      }
      ```
    *   `400 Bad Request`: Missing context parameter, or both `chunk_id` and `query_text` provided.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If `chunk_id` is provided but not found.

---

## User-Specific Retrieval Endpoints

### 3.10 Retrieve User Context (Read-Only) - COMPLETED

*   **Endpoint:** `GET /v1/users/{user_id}/context`
*   **Description:** Retrieves relevant text chunks associated **specifically with a given user** based on a semantic query. This searches across all user's relevant data (private docs, group messages, twin interactions, etc.), optionally filtered by project/session scope. This endpoint is **read-only** and performs **no ingestion**. Ideal for external agents (like the Canvas Agent) querying *about* a user's perspective or knowledge.
*   **Path Parameters:**
    *   `user_id`: `string (uuid)` - REQUIRED: The ID of the user whose context is being queried.
*   **Query Parameters:**
    *   `query_text`: `string` - REQUIRED: The natural language query for semantic search.
    *   `session_id`: `string (uuid), optional` - Scope: Further filter results by session.
    *   `project_id`: `string (uuid), optional` - Scope: Further filter results by project.
    *   `limit`: `integer, optional (default: 10)` - Maximum number of chunks to return.
    *   `include_messages_to_twin`: `boolean, optional (default: True)` - If true, results will include chunks where `is_twin_interaction` is true (i.e., user queries to the twin). Set to false to exclude these interactions.
    *   `include_private`: `boolean, optional (default: True)` - If true, include user's private docs in the query.
*   **Responses:**
    *   `200 OK`: Successfully retrieved user context chunks. Response format follows the `ChunksResponse` model (similar to `GET /v1/retrieve/context`).
      ```json
      // Example (Structure defined by ChunksResponse model)
      {
        "chunks": [
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "score": "float",
            "metadata": { ... } // Standard chunk metadata
          }
        ],
        "total": "integer"
      }
      ```
    *   `400 Bad Request`: Missing required query parameter (`query_text`).
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If the specified `user_id` does not exist.


### 3.11 Retrieve User Preferences - COMPLETED

*   **Endpoint:** `GET /v1/users/{user_id}/preferences`
*   **Description:** Retrieves known preferences for a specific user, filtered by a required decision topic and optionally by project/session scope. Combines explicit statements, inferred preferences, and relevant chat history. Private docs are always included. By default, this **includes** content generated during direct user-twin interactions. Use `include_messages_to_twin=false` to exclude them.
*   **Path Parameters:**
    *   `user_id`: `string (uuid)` - REQUIRED: The user whose preferences are being queried.
*   **Query Parameters:**
    *   `decision_topic`: `string` - REQUIRED: The topic to find preferences for (e.g., "frontend framework choice").
    *   `project_id`: `string (uuid), optional` - Scope: Filter preferences relevant to a specific project.
    *   `session_id`: `string (uuid), optional` - Scope: Filter preferences relevant to a specific session.
    *   `limit`: `integer, optional (default: 5)` - Maximum number of relevant statements/items to return.
    *   `score_threshold`: `float, optional (default: 0.6)` - Minimum score for vector search results (relevant statements) to be considered.
    *   `include_messages_to_twin`: `boolean, optional (default: True)` - If false, results from the vector search portion will exclude chunks where `is_twin_interaction` is true.
*   **Responses:**
    *   `200 OK`: Successfully retrieved preference information.
      ```json
      {
        // Structure TBD based on how preferences are modeled in Neo4j/Qdrant
        "explicit_preferences": [
          { "preference_id": "string", "statement": "string", "topic": "string, optional", "source": "string" }
        ],
        "inferred_from_votes": [
          { "vote_id": "string", "decision": "string", "topic": "string", "user_stance": "string (e.g., 'for', 'against')" }
        ],
        "relevant_statements": [ // Context chunks potentially indicating preference
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "score": "float", // Relevance score if applicable
            "metadata": { ... } // Similar to context retrieval metadata
          }
        ]
      }
      ```
    *   `400 Bad Request`: Missing required query parameter (`decision_topic`).
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If the specified `user_id` does not exist.

### 3.12 Create + Retrieve Private Memory (User Interaction) - COMPLETED

*   **Endpoint:** `POST /v1/users/{user_id}/private_memory`
*   **Description:** Retrieves a user's private memory based on semantic search **AND ingests the query itself** as a twin interaction (marked with `is_twin_interaction: true`). This endpoint is designed specifically for the user's direct interaction loop with their twin simulation. By default, the retrieval **includes** previous user messages to the twin. Set `include_messages_to_twin` to false in the request body to exclude them. **Note:** For read-only queries *about* a user without ingestion, use `GET /v1/users/{user_id}/context`.
*   **Path Parameters:**
    *   `user_id`: `string (uuid)` - REQUIRED: The ID of the user whose memory is being queried and whose query is being ingested.
*   **Request Body:**
    ```json
    {
      "query_text": "string", // REQUIRED: The query for semantic search
      "project_id": "string (uuid), optional", // Optional context filter
      "session_id": "string (uuid), optional", // Optional context filter
      "limit": "integer, optional (default: 10)",
      "include_messages_to_twin": "boolean, optional (default: True)" // Control inclusion of interaction history
    }
    ```
*   **Query Parameters:**
    *   `include_graph`: `boolean, optional (default: False)` - If true, results will be enriched with related graph context.
*   **Responses:**
    *   `200 OK`: Successfully retrieved private memory chunks.
      ```json
      {
        "chunks": [
          {
            "chunk_id": "string (uuid)",
            "text": "string",
            "score": "float", // Relevance score from Qdrant
            "metadata": {
              "source_type": "string (e.g., 'message', 'document')",
              "user_id": "string (uuid)",
              "session_id": "string (uuid), optional",
              "project_id": "string (uuid), optional",
              "doc_id": "string (uuid), optional",
              "message_id": "string (uuid), optional",
              "timestamp": "string (isoformat)",
              "outgoing_relationships": [ /* ... */ ],
              "incoming_relationships": [ /* ... */ ]
            }
          }
        ],
        "total": "integer"
      }
      ```
    *   `400 Bad Request`: Invalid request body.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If the specified `user_id` does not exist.
    *   `422 Unprocessable Entity`: Validation error (e.g., missing `query_text`).

---

## 4. Metadata Update Endpoints

### 4.1 Update Document Metadata - COMPLETED

*   **Endpoint:** `POST /v1/documents/{doc_id}/metadata`
*   **Description:** Updates metadata for an existing document identified by `doc_id`. Primarily used to add or update the `source_uri` for a completed transcript document after its raw file has been stored elsewhere, but can update other metadata fields.
*   **Path Parameters:**
    *   `doc_id`: `string (uuid)` - REQUIRED: The ID of the document to update.
*   **Request Body (application/json):**
    ```json
    {
      "user_id": "string (uuid)", // REQUIRED: User performing the update action (e.g., system user)
      "source_uri": "string, optional", // Optional: The URI of the raw document file (e.g., completed transcript)
      "timestamp": "string (isoformat), optional", // Optional: Timestamp of the update or completion (defaults to now if omitted)
      "metadata": "object, optional" // Optional: Other metadata fields to add or update (e.g., final participant list, duration)
    }
    ```
    *Note: At least one field (`source_uri` or `metadata`) should typically be provided for the update to be meaningful.*
*   **Responses:**
    *   `200 OK`: Metadata successfully updated.
      ```json
      {
        "status": "success",
        "message": "Document metadata updated successfully.",
        "doc_id": "string (uuid)"
      }
      ```
    *   `400 Bad Request`: Invalid request body or missing required fields.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `404 Not Found`: If the specified `doc_id` does not exist.
    *   `422 Unprocessable Entity`: Validation error (FastAPI default).