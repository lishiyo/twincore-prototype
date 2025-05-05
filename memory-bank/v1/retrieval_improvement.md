# Advanced Retrieval Strategies (v1)

This document outlines strategies to enhance the retrieval capabilities of the TwinCore backend by more effectively combining the strengths of Qdrant (semantic search) and Neo4j (graph relationships). These strategies aim to improve relevance, provide richer context, and enable more sophisticated querying.

## 1. Graph-Enhanced RAG (Retrieval-Augmented Generation)

*   **Concept:** Augment initial semantic search results from Qdrant with structured graph context from Neo4j before returning them. This provides a richer foundation for downstream tasks like summarization or question-answering performed by the Orchestration Layer (Dev A).
*   **Implementation Strategy:**
    1.  **Initial Semantic Search:** Perform a standard vector search in Qdrant using `RetrievalService.retrieve_context` (or similar) based on the user query and filters. Get the top N `ContentChunk` results.
    2.  **Graph Neighbor Query:** For each (or a subset) of the top N Qdrant results:
        *   Extract the `chunk_id`.
        *   Query Neo4j using a new `Neo4jDAL` method (e.g., `get_neighbors(chunk_id, depth=1)`). This query should find nodes directly connected to the chunk node (e.g., `MENTIONS` Topic, `PART_OF` Document, `AUTHORED_BY` User, potentially other related `Content` chunks via shared entities).
        *   The query should return the neighboring node properties and the relationship type connecting them.
    3.  **Enrichment:** Add the retrieved graph context (list of neighbors and relationships) to the `metadata` field of the corresponding `ContentChunk` object from the initial Qdrant results.
    4.  **Return:** Return the list of enriched `ContentChunk` objects.
*   **Target Endpoint:** Could be implemented in `RetrievalService.retrieve_enriched_context` (replacing the current basic enrichment) or a new endpoint like `/v1/retrieve/graph_rag_context`.
*   **Benefits:** Provides deeper, structured context beyond simple semantic similarity. Helps understand *why* certain chunks are related.

## 2. Graph-Aware Re-ranking

*   **Concept:** Refine the ranking of semantic search results from Qdrant by incorporating scores derived from the graph structure. Results that are highly connected or linked to important graph entities are boosted.
*   **Implementation Strategy:**
    1.  **Initial Semantic Search:** Perform vector search in Qdrant (`qdrant_dal.search_vectors`) to get an initial list of top K results (where K > final desired limit N, e.g., K=50 for N=10).
    2.  **Graph Analysis Query:** For the set of K `chunk_id`s retrieved:
        *   Execute a Neo4j query that assesses the interconnectedness *within* this set and their connections to *important external nodes* (e.g., specific topics, the current project/session node).
        *   Calculate graph-based scores for each chunk. Examples:
            *   **Connectivity Score:** How many other chunks *in the result set* is this chunk connected to (within 1-2 hops)?
            *   **Centrality Score:** Does this chunk connect to central nodes (e.g., a `Topic` node mentioned by many results)?
            *   **Recency Boost:** (Can be combined) Give higher weight to more recent chunks.
    3.  **Combined Scoring:** Develop a formula that combines the initial Qdrant `score` with the calculated graph score(s) and potentially a time decay factor. `final_score = w1 * qdrant_score + w2 * graph_score + w3 * recency_score`. Weights `w1, w2, w3` need tuning.
    4.  **Re-rank & Trim:** Re-sort the K results based on the `final_score` and return the top N.
*   **Target Endpoint:** Can be integrated into existing methods like `RetrievalService.retrieve_context` and `retrieve_private_memory`. The underlying Qdrant call would fetch more results initially (e.g., limit 50), the re-ranking happens in the service, and then the final top N are returned.
*   **Benefits:** Improves relevance by prioritizing results that are both semantically similar and structurally significant within the knowledge graph context.

## 3. Query Expansion using Graph

*   **Concept:** Use the knowledge graph to expand the user's initial query with related terms or concepts before performing the semantic search in Qdrant.
*   **Implementation Strategy:**
    1.  **Entity Linking:** Attempt to identify key entities (Topics, People, specific Documents mentioned by name/ID) in the `query_text`. This might require a simple NLP step or potentially another LLM call in future phases.
    2.  **Graph Expansion Query:** If entities are identified, query Neo4j to find directly related entities (e.g., if "Book Generator Agent" project is identified, find associated `Topic` nodes like "LLM Selection" or "Niche Research").
    3.  **Get Expansion Embeddings:** Retrieve embeddings for the text associated with these related entities (e.g., topic names/descriptions, document titles). Use the `EmbeddingService`.
    4.  **Modify Query Vector:** Combine the original `query_embedding` with the embeddings of the related entities. Strategies:
        *   **Averaging:** Simple average of all vectors.
        *   **Weighted Average:** Give higher weight to the original query embedding.
        *   **Multiple Queries:** Perform separate Qdrant searches for the original query and key related entities, then merge and de-duplicate the results (e.g., using Reciprocal Rank Fusion - RRF).
    5.  **Semantic Search:** Perform the Qdrant search using the expanded/modified query vector(s).
*   **Target Endpoint:** Can be added as an optional pre-processing step within `RetrievalService.retrieve_context` or `retrieve_private_memory`, potentially triggered by a flag in the API request.
*   **Benefits:** Increases recall by finding relevant items that might use different terminology but are conceptually linked according to the graph. Helps bridge vocabulary gaps.

These strategies represent increasing levels of complexity and integration between the vector and graph databases. Starting with Graph-Enhanced RAG might be the most straightforward, while Graph-Aware Re-ranking and Query Expansion offer more sophisticated relevance tuning. 