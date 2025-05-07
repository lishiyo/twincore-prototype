# Ben's Private Notes: LLM Evaluation Deep Dive (March 2025)

## Goal: Select Primary LLM Provider for F0 V0 Core Features

Core tasks needing LLM:
1.  **Diagram Generation:** Input: Transcript snippet(s). Output: Structured representation (e.g., JSON) of a concept map (entities, relationships). Requires reasoning, summarization, structure generation.
2.  **Twin Q&A:** Input: User query + Retrieved context chunks (RAG). Output: Answer based *only* on context. Requires context comprehension, summarization, natural language generation, instruction following (staying within context).
3.  **(Future)** Proactive Suggestions: Input: Live transcript stream + history. Output: Potential AIs, Decisions, related past topics. Requires continuous processing, entity recognition, relevance assessment.
4.  **(Future)** Twin Representation: Input: Topic + User History. Output: Simulated user preference/opinion. Requires deep preference modeling.

## Candidates Evaluated:

### 1. OpenAI (GPT-4 Turbo / GPT-4o)

*   **Pros:** High capability, generally good instruction following, fast (Turbo/4o), large community/tooling (LangChain/LangGraph integration is mature), potentially cheaper than Opus for some tasks. Vision capabilities (GPT-4V/4o) might be useful later for canvas understanding.
*   **Cons:** Context window (128k) smaller than Opus/Gemini 1.5. Less predictable release cycle/API changes historically? Can sometimes be "too creative" / ignore constraints like "answer only from context" if not prompted carefully.
*   **Testing:** Good results on diagramming task structure, reasonable on RAG Q&A but needed careful prompting to avoid outside knowledge.

### 2. Anthropic (Claude 3 Opus / Sonnet / Haiku)

*   **Pros:** Opus has *excellent* long context performance (200k window) and reported strength in reasoning, complex instructions, and coding/structured output - seems ideal for Diagram Generation. Strong focus on safety/alignment might help with instruction following (e.g., staying in context for RAG). Sonnet offers a good speed/cost/capability tradeoff for less demanding tasks (maybe initial RAG pass?). Haiku is very fast/cheap for simple tasks.
*   **Cons:** Opus is expensive. Newer than OpenAI, slightly smaller tooling ecosystem (though catching up fast, LangGraph support is good).
*   **Testing:** Opus performed *very* well on the Diagram Generation mock task, providing well-structured output. Sonnet handled basic RAG Q&A competently and quickly. Seemed to adhere well to "answer from context" constraints.

### 3. Google (Gemini 1.5 Pro)

*   **Pros:** Massive context window (1 Million tokens!) is theoretically perfect for feeding extensive history to the Twin or for analyzing entire projects. Multimodal capabilities are strong. Potentially competitive pricing. Google's infra is solid.
*   **Cons:** Still relatively new compared to GPT-4/Claude 3. Real-world performance reports on the 1M token window are still emerging (latency? cost? effective use?). LangChain/LangGraph integration might be slightly less mature than for OpenAI/Anthropic, requiring more custom work. Some early reports mentioned occasional issues with following negative constraints.
*   **Testing:** Limited hands-on testing due to API availability/timing. Potential is huge, but feels like a slightly higher integration risk/unknown performance characteristics for V0 compared to Anthropic.

## V0 Decision Rationale (Anthropic):

*   **Opus for Core Quality:** The 'Make Diagram' feature is a key differentiator. Opus seems best suited for this complex reasoning and structured output task based on current evals and benchmarks. Its large context window is also beneficial.
*   **Sonnet for Efficiency:** Using Sonnet for potentially more frequent, less complex tasks like basic Twin Q&A (retrieval-focused) offers a good cost/performance balance.
*   **Maturity/Integration:** Anthropic's API and integration with tools like LangGraph feel mature enough for V0 production use.
*   **Strategic Bet:** Betting on Anthropic's strengths in careful reasoning and instruction following feels aligned with our needs for reliable AI components, especially regarding RAG constraints and potentially future preference modeling.
*   **Fallback:** If costs become prohibitive or limitations emerge, OpenAI is a very close second and relatively easy to switch to within LangGraph. Gemini 1.5 Pro is worth revisiting post-MVP, especially if ultra-long context becomes a critical need.

## Action Item Follow-up:

*   [Done] Set up Anthropic API keys and basic LangGraph chain targeting Claude 3 Opus/Sonnet.
*   [In Progress] Develop robust prompt engineering for 'Make Diagram' using Opus.
*   [Todo] Develop RAG chain for Twin Q&A using Sonnet (or Opus if needed), focusing on context stuffing and strict instruction following.