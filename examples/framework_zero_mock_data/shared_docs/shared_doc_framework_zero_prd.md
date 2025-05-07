# Framework Zero - Product Requirements Document (PRD) - DRAFT

**Version:** 0.3 (Updated 2025-04-01 based on Session 4 Decisions)
**Authors:** Alex (PM)
**Status:** Draft

## 1. Introduction

Framework Zero (F0) is a collaborative platform designed to enhance human-AI cooperation within organizations. It combines a real-time multiplayer canvas with personalized digital twins to capture discussions, streamline workflows, track decisions, and surface relevant context, aiming to create more efficient, transparent, and autonomous organizational processes.

## 2. Goals

*   Reduce meeting time and improve meeting outcomes.
*   Combat knowledge silos and improve institutional memory.
*   Provide a transparent and auditable record of discussions, decisions, and action items.
*   Enable seamless context retrieval for users via personalized digital twins.
*   Lay the foundation for more complex human-AI agent collaboration in the future.

## 3. User Personas

*   **Primary:** Project Managers, Team Leads, Startup Founders, Product Managers within tech-focused teams (esp. AI-native).
*   **Secondary:** Individual Contributors (Engineers, Designers, Marketers), Researchers, Consultants.

## 4. MVP Scope (Targeting End of April 2025)

The Minimum Viable Product focuses on demonstrating the core loop of live capture -> AI processing -> structured output -> personalized retrieval.

**Core Features:**

1.  **Real-time Transcription & Diarization:**
    *   Ingest audio stream from active session.
    *   Use AssemblyAI to transcribe and identify speakers in real-time.
    *   Display live, auto-scrolling transcript in a dedicated UI panel.
    *   Persist transcript snippets with metadata (speaker, timestamp, session_id) in backend (Qdrant, Neo4j).

2.  **Basic Collaborative Canvas:**
    *   Multiplayer canvas using Yjs for real-time sync.
    *   Allow users to manually add/edit basic text notes.
    *   Allow users to manually add/edit basic shapes (rectangles, circles).
    *   Persist canvas state via Yjs snapshots to Postgres.

3.  **User-Triggered "Make Diagram" Feature:**
    *   Allow users to select a portion of the live transcript text.
    *   Provide a 'Make Diagram' button.
    *   On click, send selected text and context to backend orchestration (LangGraph).
    *   Use LLM (Anthropic Claude 3 Opus) to analyze text and generate a concept map (identifying key entities and relationships).
    *   Parse LLM response and render the concept map as editable objects (nodes, edges using React Flow) on the canvas.
    *   Maintain links between diagram elements and source transcript snippets.
    *   *Deferred Post-MVP:* Proactive AI suggestions (auto-detecting AIs/Decisions).

4.  **Basic Digital Twin Q&A:**
    *   Provide a private chat interface for each user with their "Twin".
    *   Allow users to ask questions (e.g., "Summarize this meeting", "What were my action items from Session 2?", "What was decided about Yjs?", "What were Fiona's privacy concerns?").
    *   Backend embeds the query and performs RAG search over relevant data sources using Qdrant.
    *   **Crucially:** Search MUST respect user permissions. Twin can only access:
        *   User's private notes/documents (uploaded with 'private' flag).
        *   User's twin chat history.
        *   Shared project documents for projects the user is a member of.
        *   Transcripts from sessions the user participated in.
    *   Retrieved context is passed to LLM (Anthropic Claude 3 Sonnet/Opus) with prompt instructing it to answer based *only* on the provided context.
    *   Display the Twin's response in the chat interface.
    *   *Deferred Post-MVP:* Twin acting as representative ("What would Ben think?").
    *   *Deferred Post-MVP:* Proactive surfacing of relevant historical context during live conversation.

5.  **Document Upload:**
    *   Provide UI for users to upload documents (.txt, .md, basic .pdf text extraction).
    *   Allow user to flag document as 'private' (only accessible to their Twin) or shared with the current project.
    *   Backend ingestion pipeline processes uploaded documents (chunking, embedding, storing in Qdrant/Neo4j) respecting the privacy flag.

## 5. Technical Stack (High Level)

*   Frontend: React + Vite, Yjs, React Flow
*   Realtime Backend: Supabase (Postgres, Realtime for notifications if needed)
*   Voice Ingest: AssemblyAI Streaming API
*   LLM Interface: LangGraph orchestrator calling Anthropic Claude 3 API (Opus & Sonnet)
*   Vector Store: Qdrant
*   Graph DB: Neo4j
*   Backend API: Python (FastAPI)

## 6. Design Principles (MVP Focus)

*   **Clarity:** User understands what the AI is doing and where information comes from.
*   **Control:** User initiates core AI actions and can edit generated content.
*   **Simplicity:** Focus on core functionality, avoid overwhelming UI.
*   **Transparency:** Link generated content back to source data.

## 7. Data & Privacy

*   Strict access control based on user roles and project membership (enforced via Supabase RLS and backend filtering).
*   Clear separation between private user data and shared project data.
*   Encryption in transit and at rest (details TBD).
*   Develop clear user-facing policies on data usage, retention, and deletion (especially for Twin data).
*   *Deferred Post-MVP:* SOC 2 Compliance planning.

## 8. Future Considerations (Post-MVP / V.next)

*   Proactive AI suggestions (AIs, Decisions, related topics) with user confirmation UI.
*   More sophisticated diagram types (flowcharts, sequence diagrams).
*   Twin representation capabilities (preference modeling).
*   Integrations (Slack, Google Workspace, Jira, etc.).
*   Advanced canvas editing features.
*   Robust versioning and history for documents and canvas states.
*   Knowledge extraction into Neo4j graph (Topics, Sentiment, etc.).
*   Guest access / external sharing controls.
*   Analytics and reporting.

## 9. Open Questions / Risks

*   Ensuring quality/reliability of 'Make Diagram' output. (Mitigation: Prompt engineering, testing)
*   Scalability of real-time sync and backend processing. (Mitigation: Start simple, monitor performance)
*   Handling edits/deletions of source data. (Decision: V0 policy TBD, likely limited mutability)
*   User trust in Twin accuracy and privacy. (Mitigation: Rigorous permission checks, transparency)
*   Performance/cost of LLM calls. (Mitigation: Use smaller models where possible, caching)