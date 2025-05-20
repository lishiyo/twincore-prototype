# Implementation Plan: Whole Context vs. RAG with TwinCore

This plan outlines the steps to create two Python scripts for testing different approaches to providing context to Gemini 2.5 Pro for answering queries based on the mock data in `examples/framework_zero/mock_data`. The goal is to compare sending all document content versus using the TwinCore backend for RAG.

**Target Queries:** The queries will be based on those listed in `memory-bank/v0/mainUseCases.md`.

**Mock IDs (to be defined and used consistently across scripts):**
*   `PROJECT_ID = "f4f7e3c8-2f8d-4f8c-9d7f-3e1a0c7d7f00"`
*   `USER_IDS = {
        "alex": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "ben": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
        "chloe": "c3d4e5f6-a7b8-9012-3456-7890abcdef01",
        "dana": "d4e5f6a7-b8c9-0123-4567-890abcdef012",
        "ethan": "e5f6a7b8-c9d0-1234-5678-90abcdef0123",
        "fiona": "f6a7b8c9-d0e1-2345-6789-0abcdef01234"
    }`
*   `SESSION_IDS = {
        "s1_kickoff": "s1a2b3c4-d5e6-f7a8-b9c0-d1e2f3a4b5c6",
        "s2_tech": "s2b3c4d5-e6f7-a8b9-c0d1-e2f3a4b5c6d7",
        "s3_client": "s3c4d5e6-f7a8-b9c0-d1e2-f3a4b5c6d7e8",
        "s4_mvp": "s4d5e6f7-a8b9-c0d1-e2f3-a4b5c6d7e8f9"
    }`

---

## Phase 1: Script for "Whole Context" Approach

**Script Name:** `examples/framework_zero/whole_context_script.py`

1.  **Setup:**
    - [ ] Import necessary libraries: `os`, `google.generativeai`.
    - [ ] Configure Gemini API key (e.g., from an environment variable `GEMINI_API_KEY`).
    - [ ] Initialize the Gemini client (`genai.GenerativeModel('gemini-2.5-pro')`).

2.  **Data Loading and Concatenation Function:**
    - [ ] Create a function `load_all_mock_data(mock_data_path)`:
        - [ ] Takes the path to the `mock_data` directory as input.
        - [ ] Recursively iterates through all `.txt`, `.md`, `.csv`, and `.mermaid` files within its subdirectories (`session_transcripts/`, `shared_docs/`, `private_docs/`, `twin_chats/`).
        - [ ] Reads the content of each file.
        - [ ] Prepends each file's content with a clear separator and its relative path. Example:
            ```
            --- START DOCUMENT: session_transcripts/transcript_session1_kickoff.txt ---
            [Content of transcript_session1_kickoff.txt]
            --- END DOCUMENT: session_transcripts/transcript_session1_kickoff.txt ---

            --- START DOCUMENT: shared_docs/shared_doc_framework_zero_prd.md ---
            [Content of shared_doc_framework_zero_prd.md]
            --- END DOCUMENT: shared_docs/shared_doc_framework_zero_prd.md ---
            ```
        - [ ] Concatenates all formatted content into a single large string.
        - [ ] Returns the concatenated string.

3.  **Querying Gemini Function:**
    - [ ] Create a function `query_gemini_with_whole_context(full_context, user_query)`:
        - [ ] Takes the concatenated `full_context` string and a `user_query` string.
        - [ ] Constructs a prompt for Gemini. This prompt should instruct Gemini to answer the `user_query` based *only* on the provided `full_context`.
            - [ ] Example prefix: `"Based on the following collection of documents, transcripts, and chat logs for the Framework Zero project, please answer the question."`
            - [ ] For user-specific queries, the prompt needs to guide Gemini: `"Given all the following documents and chat logs for project Framework Zero, paying close attention to information related to [User Name (e.g., Alice)], please answer the following question: [user_query]"`
        - [ ] Sends the combined prompt (context + query instructions) to the Gemini API.
        - [ ] Prints the Gemini's response.
        - [ ] Handles potential API errors gracefully (e.g., print error message).

4.  **Main Script Logic:**
    - [ ] Define a list of test queries from `mainUseCases.md`.
    - [ ] Call `load_all_mock_data()` to get the `full_context`.
    - [ ] Loop through each test query:
        - [ ] Print the query being asked.
        - [ ] Call `query_gemini_with_whole_context()` with the `full_context` and the current test query.
        - [ ] Add a separator before the next query's output.

---

## Phase 2: Script for "RAG with TwinCore" Approach

**Script Name:** `examples/framework_zero/rag_script.py`

**Prerequisite:** The TwinCore backend (FastAPI application) must be running and accessible. All mock data needs to be ingested into TwinCore.

### 2.A. One-Time Data Ingestion into TwinCore

This can be a separate utility script (`examples/framework_zero/ingest_mock_data_to_twincore.py`) or done manually via API calls (e.g., using `curl` or Postman). This step populates Qdrant and Neo4j.

- [ ] **Setup for Ingestion Script:**
    - [ ] Import `requests`, `os`, `json`, `uuid`.
    - [ ] Define TwinCore API base URL (e.g., `http://localhost:8000/v1`).
- [ ] **Ingestion Logic:**
    - [ ] Iterate through files in `mock_data` similar to `load_all_mock_data`.
    - [ ] For each file, construct the appropriate JSON payload and make a POST request to the relevant TwinCore ingestion endpoint:
        - [ ] **`session_transcripts/*.txt`**:
            - [ ] Can be ingested as a single document per file using `POST /ingest/document`.
            - [ ] `doc_id`: Generate a consistent UUID for each transcript file.
            - [ ] `project_id`: `PROJECT_ID`.
            - [ ] `session_id`: Relevant `SESSION_IDS` value.
            - [ ] `user_id`: Can be a generic "transcriber" ID or null if the endpoint allows.
            - [ ] `text`: Content of the transcript file.
            - [ ] `timestamp`: Use a fixed past timestamp or derive one.
            - [ ] Alternatively, parse utterances and use `POST /ingest/chunk` for each, linking them with a common `doc_id`, `session_id`, `project_id`, and assigning `user_id` per speaker if identifiable. (Single document per transcript is simpler for this test).
        - [ ] **`shared_docs/*`**:
            - [ ] Use `POST /ingest/document`.
            - [ ] `doc_id`: Generate a UUID.
            - [ ] `project_id`: `PROJECT_ID`.
            - [ ] `user_id`: Null or a generic "system_user".
            - [ ] `text`: File content.
            - [ ] `timestamp`: Fixed past timestamp.
        - [ ] **`private_docs/*_private_*.txt/md`**:
            - [ ] Use `POST /ingest/document`.
            - [ ] `doc_id`: Generate a UUID.
            - [ ] `user_id`: Extract from filename (e.g., `USER_IDS["alex"]` for `alex_private_...`).
            - [ ] `project_id`: `PROJECT_ID`.
            - [ ] `text`: File content.
            - [ ] `timestamp`: Fixed past timestamp.
            - [ ] *Note on privacy*: The ingestion endpoint itself might not have an `is_private` flag. Privacy is typically handled by associating the `doc_id` with the `user_id` and then using user-specific retrieval endpoints that respect this ownership.
        - [ ] **`twin_chats/*_twin_chat_log.txt`**:
            - [ ] Parse the log file (e.g., line by line, or by speaker turns).
            - [ ] For each message, use `POST /ingest/message`.
            - [ ] `user_id`: Extract from filename.
            - [ ] `project_id`: `PROJECT_ID`.
            - [ ] `session_id`: Can be null, or associate with a general "twin_chat_session" if desired.
            - [ ] `message_text`: The content of the chat message.
            - [ ] `timestamp`: Increment timestamps for ordering.
            - [ ] `metadata`: Could include `{"is_twin_interaction": true}` if the schema/API supports it clearly through this endpoint.
    - [ ] Print status of each ingestion attempt.

### 2.B. RAG Script (`rag_script.py`)

- [ ] **Setup:**
    - [ ] Import `requests`, `json`, `google.generativeai`.
    - [ ] Configure Gemini API key and TwinCore API base URL.
    - [ ] Initialize Gemini client.
- [ ] **TwinCore Retrieval Function:**
    - [ ] Create a function `get_relevant_chunks_from_twincore(user_query, project_id, user_id=None, session_id=None)`:
        - [ ] Determines the appropriate TwinCore retrieval endpoint based on whether `user_id` is provided and the nature of the query.
            - [ ] If `user_id` and query relates to general user context: `GET /v1/users/{user_id}/context` with `query_text`, `project_id`, optional `session_id`.
            - [ ] If query is for shared project/session context: `GET /v1/retrieve/context` with `query_text`, `project_id` or `session_id`.
            - [ ] If query is about user preferences: `GET /v1/users/{user_id}/preferences` with `decision_topic` (extracted from query) and `project_id`.
            - [ ] If simulating direct twin chat: `POST /v1/users/{user_id}/private_memory` (this also ingests the query).
        - [ ] Makes the API request to TwinCore.
        - [ ] Parses the response, extracts the `text` from each chunk in `response.json()['chunks']`.
        - [ ] Concatenates these text chunks into a single context string.
        - [ ] Returns the concatenated context string.
- [ ] **Querying Gemini Function (with RAG context):**
    - [ ] Create a function `query_gemini_with_rag_context(rag_context, user_query)`:
        - [ ] Similar to `query_gemini_with_whole_context`, but uses `rag_context`.
        - [ ] Prompt: `"Based on the following relevant snippets retrieved from a larger knowledge base for the Framework Zero project, please answer the question: [user_query]

Snippets:
[rag_context]"`
        - [ ] Sends to Gemini and prints the response.
- [ ] **Main Script Logic:**
    - [ ] Define the same list of test queries from `mainUseCases.md`.
    - [ ] Loop through each test query:
        - [ ] Print the query.
        - [ ] Determine appropriate parameters for `get_relevant_chunks_from_twincore` (e.g., which `user_id` if it's a user-specific query, the `project_id`, etc.).
        - [ ] Call `get_relevant_chunks_from_twincore()` to get `rag_context`.
        - [ ] Print the retrieved `rag_context` (for verification/interest).
        - [ ] Call `query_gemini_with_rag_context()` with `rag_context` and the test query.
        - [ ] Add a separator.

---

## Phase 3: Comparison and Analysis

1.  **Execute Both Scripts:**
    - [ ] Run `whole_context_script.py` and `rag_script.py` (after ingesting data for the RAG script).
2.  **Collect Outputs:**
    - [ ] Save the printed outputs from both scripts for each query.
3.  **Analyze Results:**
    - [ ] **Quality of Answers:** Relevance, completeness, correctness.
    - [ ] **Conciseness:** How direct are the answers?
    - [ ] **Hallucinations:** Does either method produce incorrect information?
    - [ ] **Context Utilization:** Does the "whole context" approach seem to leverage distant information effectively, or does it get overwhelmed? Does RAG miss crucial context?
    - [ ] **Attribution (for RAG):** How well do the retrieved chunks support the final answer?
    - [ ] **Ease of Prompting:** Was one method easier to get good answers from via prompt engineering?
    - [ ] **(Subjective) Latency:** Note any significant differences in response time.

This structured comparison will provide valuable insights into which approach is more effective for the defined use cases and current data scale.
