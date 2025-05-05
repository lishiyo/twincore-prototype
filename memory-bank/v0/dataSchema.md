# Data Design (TwinCore Prototype)

For the full project, we would be using Postgres, Qdrant, and Neo4j. For the prototype, we would mock Postgres initially, and focus on Qdrant and Neo4j:

*   **Postgres (Mocked/External):** Source of truth for core entity IDs (Users, Projects, Sessions) and potentially basic metadata (names, emails). Assume these IDs are provided to the TwinCore service.
*   **Qdrant:** Handles efficient semantic search over unstructured text data (messages, document chunks). Stores text embeddings and rich metadata payload linking back to other entities.
*   **Neo4j:** Models and queries the relationships between entities (who participated where, who uploaded what, who said what, stated preferences, derived actions/decisions, etc.).

## Qdrant Schema

**Collection Name:** `twin_memory` (Example name)

**Vectors:** Embeddings of text chunks (from messages, documents, etc.).

**Payload (Metadata stored with each vector):**

```json
{
  "chunk_id": "uuid", // Unique ID for this specific text chunk/embedding (links to Neo4j Chunk node)
  "text_content": "string", // The actual text chunk corresponding to the vector
  "source_type": "string", // Enum: 'message', 'document_chunk', 'transcript_snippet', 'preference_statement', 'twin_chat_query', 'agent_log', 'diagram_element', 'plan_step', etc.
  "timestamp": "datetime", // ISO 8601 string. Timestamp of the original event/creation

  // --- Foreign Keys (UUIDs linking to Neo4j/Postgres) ---
  "user_id": "uuid | null", // Author/owner of the content, OR the user interacting with the twin. Null if system-generated/unowned.
  "session_id": "uuid | null", // Session context, if applicable
  "project_id": "uuid | null", // Project context, if applicable
  "doc_id": "uuid | null", // Source document ID, if applicable. **For transcript_snippet, this MUST be the consistent ID of the parent transcript Document.**
  "message_id": "uuid | null", // Source message ID, if applicable
  // --- IDs for future use (keep nullable for prototype) ---
  "derived_decision_id": "uuid | null", // If this chunk led to a decision
  "derived_action_id": "uuid | null",   // If this chunk led to an action item
  "derived_blocker_id": "uuid | null",  // If this chunk identified a blocker
  "derived_risk_id": "uuid | null",     // If this chunk identified a risk
  "preference_id": "uuid | null",     // If this chunk is an explicit preference statement
  "vote_id": "uuid | null",           // If this chunk is rationale for a specific vote
  "agent_action_id": "uuid | null",   // If this chunk is a log from an agent action
  "team_id": "uuid | null",
  "org_id": "uuid | null",

  // --- Prototype-Specific Flags ---
  "is_twin_interaction": "boolean | null", // TRUE if this text is part of a user<>twin chat or agent<>twin query
  "is_private": "boolean | null", // TRUE if this content (e.g., document chunk) is private to the user_id

  // --- Optional Extracted/Inferred Metadata (Populated by Knowledge Service) ---
  "topic_ids": ["uuid", ...], // List of Topic UUIDs mentioned/relevant (from NLP/Graph)
  "sentiment_score": "float | null",
  "is_action_item": "boolean | null", // Flag if NLP identified this chunk as potentially representing an action
  "is_decision": "boolean | null",    // Flag if NLP identified this chunk as potentially representing a decision
  "is_blocker": "boolean | null",     // Flag if NLP identified this chunk as potentially representing a blocker
  "is_risk": "boolean | null",        // Flag if NLP identified this chunk as potentially representing a risk
}
```
*Note: The `derived_*_id` fields in Qdrant are optional denormalizations for quick filtering. The primary relationship source is Neo4j.*

**How it's used (Example - Private Memory):**

1.  User Alice asks her twin (via Streamlit UI): "What were my ideas for cover art?"
2.  The `/v1/users/{user_id}/private_memory` endpoint is called with `user_id=Alice_ID`, `query_text="ideas for cover art"`.
3.  The endpoint *first* ingests the query: Creates a chunk with `text_content="What were my ideas for cover art?"`, `user_id=Alice_ID`, `is_twin_interaction=true`, `source_type='twin_chat_query'`, other relevant context (session/project if available). Upserts to Qdrant & adds node/relationship to Neo4j.
4.  Then, it performs retrieval: Queries Qdrant for vectors semantically similar to "ideas for cover art".
5.  Filters the Qdrant query: `must` condition `user_id == Alice_ID`. Optionally filter further by `project_id`/`session_id` if provided in the API call. Could potentially filter out `is_twin_interaction=true` results if only showing source material.
6.  Retrieves matching chunks, including the one from Alice's personal doc: `"Idea: Use stable diffusion for generating unique cover art styles based on genre."`.

## Neo4j Schema (Expanded Prototype)

Models relationships essential for context, authorship, preferences, and derived knowledge/actions.

**Core Node Labels (Additions/Updates Marked):**

*   `User`
    *   Properties: `user_id` (UUID, primary key), `name` (string)
*   `Organization` *(Future)*
    *   Properties: `org_id` (UUID, primary key), `name`, `created_at`
*   `Team` *(Future)*
    *   Properties: `team_id` (UUID, primary key), `name`, `created_at`
*   `Project`
    *   Properties: `project_id` (UUID, primary key), `name` (string)
*   `Session`
    *   Properties: `session_id` (UUID, primary key), `timestamp` (datetime, approx. start time)
*   `Document` *(Base label for structured/unstructured docs)*
    *   Properties: `document_id` (UUID, primary key), `name` (string), `source_type` (string), `is_private` (boolean), `source_uri` (string, nullable)
*   `Diagram:Document` *(NEW - Subtype via multi-label)*
    *   Properties: Inherits `Document`, adds `diagram_type` (string, e.g., 'flowchart', 'mindmap')
*   `Plan:Document` *(NEW - Subtype via multi-label)*
    *   Properties: Inherits `Document`, adds `plan_status` (string, e.g., 'Draft', 'Active')
*   `Message`
    *   Properties: `message_id` (UUID, primary key), `timestamp` (datetime), `is_twin_interaction` (boolean)
*   `Chunk` *(NEW - Represents text segments indexed in Qdrant)*
    *   Properties: `chunk_id` (UUID, primary key), `qdrant_point_id` (string, optional), `source_type` (string), `timestamp` (datetime), `is_twin_interaction` (boolean)
*   `Topic`
    *   Properties: `topic_id` (UUID, primary key), `name` (string, e.g., "budget", "java", "ui-design")
*   `Preference`
    *   Properties: `preference_id` (UUID, primary key), `statement` (text), `timestamp` (datetime)
*   `Decision` *(NEW)*
    *   Properties: `decision_id` (UUID, primary key), `text` (string), `timestamp` (datetime), `status` (string, e.g., 'Proposed', 'Agreed', 'Implemented')
*   `ActionItem` *(Consolidated - covers user tasks & potentially simple agent tasks)*
    *   Properties: `action_id` (UUID, primary key), `text` (string), `status` (string, e.g., 'Open', 'In Progress', 'Done'), `due_date` (datetime, nullable), `timestamp` (datetime created)
*   `Blocker` *(NEW)*
    *   Properties: `blocker_id` (UUID, primary key), `text` (string), `status` (string, e.g., 'Identified', 'Resolved'), `timestamp` (datetime identified)
*   `Risk` *(NEW)*
    *   Properties: `risk_id` (UUID, primary key), `text` (string), `severity` (string, e.g., 'Low', 'Medium', 'High'), `status` (string, e.g., 'Identified', 'Mitigated'), `timestamp` (datetime identified)
*   `Agent` *(NEW)*
    *   Properties: `agent_id` (UUID, primary key), `name` (string), `type` (string, e.g., 'Summarizer', 'Planner')
*   `AgentAction` *(NEW - Log of agent activity)*
    *   Properties: `action_id` (UUID, primary key), `agent_id` (UUID), `action_type` (string, e.g., 'summarize_chunk', 'create_action_item'), `timestamp` (datetime), `status` (string, e.g., 'Success', 'Failure'), `details` (string, optional JSON/text payload)
*   `Vote` *(Future)*
    *   Properties: `vote_id` (UUID, primary key), `target` (text), `value` (int/string), `timestamp` (datetime)

**Core Relationship Types (Additions/Updates Marked):**

*Existing Relationships (Confirm usage or adjust direction/name as needed):*
*   `(User)-[:MEMBER_OF {role: string, joined_at: datetime}]->(Team)`
*   `(Team)-[:BELONGS_TO]->(Organization)`
*   `(Project)-[:OWNED_BY]->(Organization)`
*   `(Team)-[:WORKS_ON]->(Project)`
*   `(User)-[:WORKS_ON]->(Project)`
*   `(User)-[:PARTICIPATED_IN]->(Session)`
*   `(Session)-[:PART_OF]->(Project)`
*   `(User)-[:UPLOADED {timestamp: datetime}]->(Document)`
*   `(Document)-[:ATTACHED_TO]->(Session)`
*   `(Document)-[:RELATED_TO]->(Project)`
*   `(User)-[:AUTHORED {timestamp: datetime}]->(Message)`
*   `(Message)-[:POSTED_IN]->(Session)`
*   `(Message)-[:REPLY_TO]->(Message)`
*   `(Topic)-[:MENTIONED_IN]->(Message)` *(Changed direction)*
*   `(Topic)-[:MENTIONED_IN]->(Document)` *(Changed direction)*
*   `(User)-[:CAST_VOTE {timestamp: datetime}]->(Vote)`
*   `(Vote)-[:APPLIES_TO]->(Session)`
*   `(Vote)-[:APPLIES_TO]->(Project)`
*   `(Vote)-[:ABOUT_TOPIC]->(Topic)`
*   `(Vote)-[:HAS_RATIONALE]->(Message)`

*New/Updated Relationships:*
*   `(Chunk)-[:PART_OF_DOCUMENT]->(Document)`
*   `(Chunk)-[:PART_OF_MESSAGE]->(Message)`
*   `(Chunk)-[:PART_OF_SESSION]->(Session)`
*   `(Chunk)-[:CONTEXT_PROJECT]->(Project)`
*   `(Chunk)-[:AUTHORED_BY]->(User)`
*   `(Topic)-[:MENTIONED_IN]->(Chunk)`
*   `(Preference)-[:DERIVED_FROM]->(Chunk)`
*   `(User)-[:STATED]->(Preference)`
*   `(Preference)-[:APPLIES_TO]->(Project)`
*   `(Preference)-[:RELATED_TO]->(Topic)`
*   `(Decision)-[:DERIVED_FROM]->(Chunk)`
*   `(Decision)-[:APPLIES_TO]->(Project)`
*   `(Decision)-[:MADE_IN]->(Session)`
*   `(Decision)-[:MADE_BY]->(User)`
*   `(ActionItem)-[:DERIVED_FROM]->(Chunk)`
*   `(ActionItem)-[:ASSIGNED_TO]->(User)`
*   `(ActionItem)-[:ASSIGNED_TO]->(Agent)`
*   `(ActionItem)-[:APPLIES_TO]->(Project)`
*   `(ActionItem)-[:CREATED_IN]->(Session)`
*   `(ActionItem)-[:PART_OF]->(Plan)`
*   `(Blocker)-[:IDENTIFIED_IN]->(Chunk)`
*   `(Blocker)-[:RELATES_TO]->(Project)`
*   `(Blocker)-[:REPORTED_BY]->(User)`
*   `(Risk)-[:IDENTIFIED_IN]->(Chunk)`
*   `(Risk)-[:RELATES_TO]->(Project)`
*   `(Risk)-[:REPORTED_BY]->(User)`
*   `(User)-[:MANAGES]->(Project)`
*   `(Session)-[:ASSOCIATED_WITH]->(Document)`
*   `(Agent)-[:PERFORMED]->(AgentAction)`
*   `(AgentAction)-[:TRIGGERED_BY]->(User)`
*   `(AgentAction)-[:TRIGGERED_BY]->(Session)`
*   `(AgentAction)-[:AFFECTED]->(Chunk)`
*   `(AgentAction)-[:CREATED]->(ActionItem)`
*   `(AgentAction)-[:CREATED]->(Decision)`
*   `(AgentAction)-[:USED_TOOL]->(Tool)`


**How it's used (Example - Knowledge Extraction):**

1.  A new message chunk arrives and is processed by the Knowledge Extraction Service.
2.  NLP identifies a potential `ActionItem` within the `Chunk`.
3.  **Neo4j Step:**
    *   `MERGE` the `Chunk` node (using `chunk_id` from Qdrant payload).
    *   Create a new `ActionItem` node with properties (text, status='Open', timestamp).
    *   Create the `(ActionItem)-[:DERIVED_FROM]->(Chunk)` relationship.
    *   If NLP identified an assignee, find the `User` (or potentially `Agent`) node and create `(ActionItem)-[:ASSIGNED_TO]->(Assignee)`.
    *   Link context: Find parent `Session`/`Project` via the `Chunk` and create `(ActionItem)-[:CREATED_IN]->(Session)` and `(ActionItem)-[:APPLIES_TO]->(Project)`.
4.  **Qdrant Step (Optional Denormalization):** Update the payload of the source `Chunk` with `derived_action_id = new_action_item_id`.

## Summary of Integration (Expanded)

1.  **Ingestion:**
    *   Service layer coordinates embedding and Neo4j node creation.
    *   **Neo4j:** `MERGE` core nodes (`User`, `Project`, `Session`, `Document`, `Message`, **`Chunk`**) and create structural relationships (`PART_OF_*`, `AUTHORED_BY`, etc.).
    *   **Qdrant:** Store chunk embeddings with payloads containing all relevant UUIDs.
2.  **Knowledge Extraction Service:**
    *   Processes new `Chunk` nodes (or listens to events).
    *   Uses NLP/rules to identify potential Decisions, ActionItems, Blockers, Risks, Topics.
    *   **Neo4j:** Creates corresponding new nodes (`Decision`, `ActionItem`, etc.) and links them via `DERIVED_FROM` / `IDENTIFIED_IN` to the source `Chunk`(s). Creates context links (`APPLIES_TO`, `CREATED_IN`).
    *   **Qdrant (Optional):** Updates source chunk payloads with `derived_*_id` flags/UUIDs.
3.  **Querying:**
    *   Services query Qdrant for semantic similarity (e.g., "show risks for project X").
    *   Services query Neo4j for relationships (e.g., "find action items assigned to Bob", "show decisions derived from chunks in session Y", "find chunks related to project Z managed by Alice"). Use indexes heavily.
    *   Combine results: Use Neo4j to filter/enrich Qdrant results (using `chunk_id`) or use Neo4j results to inform Qdrant queries.

## Clarification: `is_twin_interaction` Flag

The `is_twin_interaction` boolean flag in the Qdrant payload serves a critical role in distinguishing the origin and nature of the text content:

*   **`is_twin_interaction: False` (or null/absent):** Represents **Source Content**. This is the raw material ingested from external user activities, such as messages sent in a chat application (`source_type: 'message'`), uploaded documents (`source_type: 'document_chunk'`), or transcript utterances (`source_type: 'transcript_snippet'`). It forms the basis of the twin's knowledge.

*   **`is_twin_interaction: True`:** Represents **Interaction Content**. This data is generated *specifically* during a direct interaction loop between a user and their digital twin. This typically includes:
    *   The user's query or prompt directed *to* the twin (e.g., when calling `/v1/users/{user_id}/private_memory` which yields `source_type: 'twin_chat_query'`).

**Usage Pattern:**

1.  **Setting the Flag:**
    *   Standard ingestion endpoints (`/v1/ingest/message`, `/v1/ingest/document`, `/v1/ingest/chunk`) typically result in chunks with `is_twin_interaction: False`.
    *   Endpoints simulating a direct user-twin interaction (like `/v1/users/{user_id}/private_memory`, which ingests the user's query) should set `is_twin_interaction: True` for the ingested query chunk.
2.  **Filtering during Retrieval:**
    *   Retrieval endpoints that perform vector searches can control whether to include Interaction Content using an `include_messages_to_twin` (or similarly named) parameter.
    *   **Default Behavior:**
        *   General context retrieval (e.g., `/v1/retrieve/context`, `/v1/retrieve/group`, `/v1/retrieve/timeline`) typically defaults to `include_messages_to_twin: False` to focus on original source material.
        *   User-specific retrieval like preferences (`/v1/retrieve/preferences`) and private memory (`/v1/users/{user_id}/private_memory`) typically defaults to `include_messages_to_twin: True`, as the user's direct statements to the twin are often crucial for these tasks.
    *   The DAL methods (`QdrantDAL.search_vectors`, `QdrantDAL.search_user_preferences`) accept a corresponding boolean flag to implement this filtering.

This distinction, controlled by the API parameter, allows retrieval endpoints to fetch the appropriate type of information based on the specific use case.
