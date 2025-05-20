# Chloe - Personal Notes - Conference / Learning Ideas (April 2025)

Things I want to learn more about / conferences to maybe attend later this year, relevant to F0 or just general interest:

**Technical Topics:**

*   **Advanced RAG Techniques:** Beyond basic retrieve-then-read. Things like query transformations, reranking, HyDE, self-querying, smaller models for retrieval pre-processing. How to make RAG more robust and less prone to missing context or pulling irrelevant info. (Maybe relevant for Twin Q&A V2).
*   **LLM Evaluation & Monitoring:** How to systematically evaluate the quality of LLM outputs (diagrams, summaries, Q&A)? Metrics beyond BLEU/ROUGE? Tools for monitoring prompts, responses, costs, latency in production. (Essential post-MVP).
*   **Event Sourcing / CQRS:** Could this pattern help manage the complexity of keeping Postgres, Qdrant, and Neo4j in sync? Seems complex to implement but might be more robust long-term than dual writes or complex sync logic. Worth understanding the trade-offs.
*   **Advanced Neo4j / Graph Data Science:** Using graph algorithms (community detection, centrality, pathfinding) on our knowledge graph. Could we automatically identify key influencers in discussions, find related but unlinked concepts, etc.? (Future feature potential).
*   **Real-time Data Pipelines:** Best practices for building and managing resilient pipelines like our ingestion flow (AssemblyAI -> Embed -> Qdrant -> Neo4j). Kafka? Pulsar? Or just robust error handling in FastAPI background tasks for now?
*   **WebAssembly (WASM):** Could parts of our heavier client-side logic (e.g., complex canvas interactions, maybe even light embedding models?) run in WASM for better performance? Niche, but interesting.

**Conferences / Events:**

*   **Knowledge Graph Conference:** Usually in May? Good for Neo4j/graph DB deep dives.
*   **AI Engineer Summit:** Covers practical LLM application development, RAG, agents, etc.
*   **Scale By The Bay / Strange Loop (if it returns):** Broader software engineering, distributed systems, data pipelines. Good for fundamentals.
*   **Local Python / AI Meetups:** Good for networking and seeing what others are building.

**Other Learning:**

*   Read more papers on arXiv related to RAG, agent architectures, LLM eval.
*   Do some hands-on tutorials with Event Sourcing frameworks.
*   Experiment with graph algorithms in Neo4j using dummy data.

**Priority for F0:** Need to focus on LLM Eval/Monitoring and robust RAG techniques first, as those are critical for improving the core product post-MVP. The data pipeline / sync problem is also immediate. Graph Data Science is more futuristic.