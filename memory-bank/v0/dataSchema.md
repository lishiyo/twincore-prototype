# Data Design (TwinCore Prototype)

For the full project, we would be using Postgres, Qdrant, and Neo4j. For the prototype, we would mock Postgres initially, and focus on Qdrant and Neo4j:

*   **Postgres (Mocked/External):** Source of truth for core entity IDs (Users, Projects, Sessions) and potentially basic metadata (names, emails). Assume these IDs are provided to the TwinCore service.
*   **Qdrant:** Handles efficient semantic search over unstructured text data (messages, document chunks). Stores text embeddings and rich metadata payload linking back to other entities.
*   **Neo4j:** Models and queries the relationships between entities (who participated where, who uploaded what, who said what, stated preferences).

## Qdrant Schema

**Collection Name:** `twin_memory` (Example name)

**Vectors:** Embeddings of text chunks (from messages, documents, etc.).

**Payload (Metadata stored with each vector):**

```json
{
  "chunk_id": "uuid", // Unique ID for this specific text chunk/embedding
  "text_content": "string", // The actual text chunk corresponding to the vector
  "source_type": "string", // Enum: 'message', 'document_chunk', 'transcript_snippet', 'preference_statement', 'twin_chat_query' etc.
  "timestamp": "datetime", // ISO 8601 string. Timestamp of the original event/creation

  // --- Foreign Keys (UUIDs linking to Neo4j/Postgres) ---
  "user_id": "uuid | null", // Author/owner of the content, OR the user interacting with the twin. Null if system-generated/unowned.
  "session_id": "uuid | null", // Session context, if applicable
  "project_id": "uuid | null", // Project context, if applicable
  "doc_id": "uuid | null", // Source document ID, if applicable
  "message_id": "uuid | null", // Source message ID, if applicable
  // --- IDs for future use (keep nullable for prototype) ---
  "preference_id": "uuid | null", // If this chunk is an explicit preference statement
  "vote_id": "uuid | null", // If this chunk is rationale for a specific vote
  "team_id": "uuid | null",
  "org_id": "uuid | null",

  // --- Prototype-Specific Flags ---
  "is_twin_interaction": "boolean | null", // TRUE if this text is part of a user<>twin chat or agent<>twin query
  "is_private": "boolean | null", // TRUE if this content (e.g., document chunk) is private to the user_id

  // --- Optional Extracted/Inferred Metadata (Future) ---
  "topic_ids": ["uuid", ...], // List of Topic UUIDs mentioned/relevant (from NLP/Graph)
  "sentiment_score": "float | null",
  "is_action_item": "boolean | null",
  "is_decision": "boolean | null",
  "is_blocker": "boolean | null"
}
```

**How it's used (Example - Private Memory):**

1.  User Alice asks her twin (via Streamlit UI): "What were my ideas for cover art?"
2.  The `/api/retrieve/private_memory` endpoint is called with `user_id=Alice_ID`, `query_text="ideas for cover art"`.
3.  The endpoint *first* ingests the query: Creates a chunk with `text_content="What were my ideas for cover art?"`, `user_id=Alice_ID`, `is_twin_interaction=true`, `source_type='twin_chat_query'`, other relevant context (session/project if available). Upserts to Qdrant & adds node/relationship to Neo4j.
4.  Then, it performs retrieval: Queries Qdrant for vectors semantically similar to "ideas for cover art".
5.  Filters the Qdrant query: `must` condition `user_id == Alice_ID`. Optionally filter further by `project_id`/`session_id` if provided in the API call. Could potentially filter out `is_twin_interaction=true` results if only showing source material.
6.  Retrieves matching chunks, including the one from Alice's personal doc: `"Idea: Use stable diffusion for generating unique cover art styles based on genre."`.

## Neo4j Schema (Prototype Focus)

Models relationships essential for context, authorship, and preference tracking in the prototype.

**Core Node Labels for Prototype:**

*   `User`
    *   Properties: `user_id` (UUID, primary key), `name` (from mock)
*   `Organization`
    *   Properties: `org_id` (UUID, primary key), `name`, `created_at`
*   `Team`
-    *   Properties: `team_id` (UUID, primary key), `name`, `created_at`
*   `Project`
    *   Properties: `project_id` (UUID, primary key), `name` (e.g., "Book Generator Agent")
*   `Session`
    *   Properties: `session_id` (UUID, primary key), `timestamp` (approx. start time)
*   `Document`
    *   Properties: `document_id` (UUID, primary key), `name`, `source_type`, `is_private` (boolean, mirrors Qdrant flag)
*   `Message`
    *   Properties: `message_id` (UUID, primary key), `timestamp`, `is_twin_interaction` (boolean, mirrors Qdrant flag)
*   `Preference` *(Used if explicitly modeling stated preferences)*
    *   Properties: `preference_id` (UUID, primary key), `statement` (text), `timestamp`
*   `Topic`
    *   Properties: `topic_id` (UUID, primary key), `name` (e.g., "budget", "java", "ui-design")
*   `Vote`
    *   Properties: `vote_id` (UUID, primary key), `target` (text, e.g., "Variant A"), `value` (int/string), `timestamp`

*(Nodes like `Organization`, `Team`, `Topic`, `Vote` can be defined in the schema for future use but are not strictly required or populated by the prototype's initial data/features).*

**Core Relationship Types for Prototype:**

*   `(User)-[:MEMBER_OF {role: string, joined_at: datetime}]->(Team)`
*   `(Team)-[:BELONGS_TO]->(Organization)`
*   `(Project)-[:OWNED_BY]->(Organization)` // Or potentially linked via Team
*   `(Team)-[:WORKS_ON]->(Project)`
*   `(User)-[:WORKS_ON]->(Project)` // Direct assignment or derived via team
*   `(User)-[:PARTICIPATED_IN]->(Session)`
*   `(Session)-[:PART_OF]->(Project)`
*   `(User)-[:UPLOADED {timestamp: datetime}]->(Document)` *(For associating the uploader)*
*   `(Document)-[:ATTACHED_TO]->(Session)` *(If uploaded during a specific session)*
*   `(Document)-[:RELATED_TO]->(Project)` *(General project association)*
*   `(User)-[:AUTHORED {timestamp: datetime}]->(Message)`
*   `(Message)-[:POSTED_IN]->(Session)`
*   `(Message)-[:REPLY_TO]->(Message)` // Threading
*   `(User)-[:STATED {timestamp: datetime}]->(Preference)` *(If modeling explicit preferences)*
*   `(Preference)-[:APPLIES_TO]->(Project)` *(Context)*
*   `(Preference)-[:SOURCE_MESSAGE]->(Message)` *(Link preference to where it was said)*
*   `(Preference)-[:SOURCE_DOCUMENT]->(Document)` *(Link preference to where it was written)*
*   `(Preference)-[:RELATED_TO]->(Topic)` // Subject of preference
*   `(Message)-[:REPLY_TO]->(Message)` // Threading
*   `(Message)-[:MENTIONS {relevance: float}]->(Topic)` // Identified via NLP
*   `(Document)-[:MENTIONS {relevance: float}]->(Topic)` // Identified via NLP
*   `(User)-[:CAST_VOTE {timestamp: datetime}]->(Vote)`
*   `(Vote)-[:APPLIES_TO]->(Session)` // Context
*   `(Vote)-[:APPLIES_TO]->(Project)` // Context
*   `(Vote)-[:ABOUT_TOPIC]->(Topic)` // What was voted on
*   `(Vote)-[:HAS_RATIONALE]->(Message)` // Link to justifying message(s)

*(Relationships like `MENTIONS`, `REPLY_TO`, `MEMBER_OF`, `WORKS_ON`, vote relationships etc., are for future extension).*

**How it's used (Example - Session Context Retrieval):**

1.  Canvas Agent asks (via API call `/api/retrieve/context`): "What was discussed about the roadmap in the current Book Gen session?" (`session_id=SESSION_BOOK_CURRENT_ID`, `project_id=PROJECT_BOOK_GEN_ID`, `query_text="roadmap"`)
2.  **Neo4j Step:** Query to find participants (optional but good practice):
    ```cypher
    MATCH (s:Session {session_id: $session_id})<-[:PARTICIPATED_IN]-(u:User)
    RETURN u.user_id AS participantId
    ```
    (Result: Alice_ID, Bob_ID, Charlie_ID)
3.  **Qdrant Step:** Query Qdrant for vectors semantically similar to "roadmap".
4.  Filter the Qdrant query using `must` conditions:
    *   `session_id == SESSION_BOOK_CURRENT_ID`
    *   Optionally add `project_id == PROJECT_BOOK_GEN_ID`
    *   *(Could also filter by participant IDs found in step 2 if strict participation is needed, but session_id filter might be sufficient)*
5.  Retrieve matching chunks from Qdrant payload, including:
    *   Alice: "Okay team, let's finalize the Q3 roadmap for the Book Generator."
    *   Bob: "My main priority is integrating the niche research tool." (Relevant if embedding understands it relates to roadmap priorities)
    *   Charlie: "I think improving the outline generation logic is critical first." (Also relevant)

## Summary of Integration (Prototype)

1.  **Ingestion:** Mock data or data from prototype UI (uploads, chats) comes into the API.
    *   Service layer coordinates embedding.
    *   **Neo4j:** `MERGE` core nodes (`User`, `Project`, `Session`, `Document`, `Message`) and create core relationships (`PARTICIPATED_IN`, `UPLOADED`, `AUTHORED`, `POSTED_IN`, etc.) using provided UUIDs. Set `is_private`/`is_twin_interaction` properties on nodes.
    *   **Qdrant:** Store text chunk embeddings with payloads containing all relevant UUIDs and the `is_private`/`is_twin_interaction` flags.
2.  **Querying:** API endpoints trigger service layer.
    *   Services may query Neo4j first for context IDs (e.g., session participants).
    *   Services query Qdrant using semantic vectors and filters derived from API parameters and potentially Neo4j results (`user_id`, `session_id`, `project_id`, `is_private`, `is_twin_interaction`).
    *   Results from Qdrant (text + metadata) are returned.
