"""Mock data for TwinCore Prototype.

This module provides mock data entities and initial seed data for the TwinCore
prototype. It represents users, projects, sessions, and content that would
typically come from a shared data source or API in a real implementation.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# --- Entities (Mocking Postgres/Shared Service) ---
# Define constant UUIDs for predictability
USER_ALICE_ID = "a11ce000-0000-0000-0000-000000000001"
USER_BOB_ID = "b0b0b0b0-0000-0000-0000-000000000002"
USER_CHARLIE_ID = "c4a111e0-0000-0000-0000-000000000003"

USERS = {
    USER_ALICE_ID: {"name": "Alice"},
    USER_BOB_ID: {"name": "Bob"},
    USER_CHARLIE_ID: {"name": "Charlie"}
}

PROJECT_BOOK_GEN_ID = "b0000000-6e40-0000-0000-000000000001"   # Current Project: Book Generator Agent
PROJECT_PAST_WEB_ID = "web00000-0000-0000-0000-000000000002"   # Past Project: Web Development

PROJECTS = {
    PROJECT_BOOK_GEN_ID: {"name": "Book Generator Agent"},
    PROJECT_PAST_WEB_ID: {"name": "Past Web Project"}
}

SESSION_BOOK_CURRENT_ID = "5e551011-c41e-0000-0000-000000000001"  # Current Session for Book Gen
SESSION_BOOK_PAST_ID = "5e551011-a570-0000-0000-000000000002"     # Past Session for Book Gen
SESSION_WEB_PAST_ID = "5e551011-web0-0000-0000-000000000003"      # Past Session for Web project

SESSIONS = {
    SESSION_BOOK_CURRENT_ID: {"name": "Book Gen - Current", "project_id": PROJECT_BOOK_GEN_ID},
    SESSION_BOOK_PAST_ID: {"name": "Book Gen - Past", "project_id": PROJECT_BOOK_GEN_ID},
    SESSION_WEB_PAST_ID: {"name": "Web Project - Past", "project_id": PROJECT_PAST_WEB_ID}
}

# Organizations and Teams (for additional context)
ORG_TWIN_LABS_ID = "04600000-1ab5-0000-0000-000000000001"       # Organization: Twin Labs
TEAM_PRODUCT_ID = "7e410000-940d-0000-0000-000000000001"        # Team: Product

# Topic IDs for enriched examples (to be used in future phases)
TOPIC_LLM_ID = str(uuid.uuid4())           # Topic: LLM
TOPIC_EMBEDDING_ID = str(uuid.uuid4())     # Topic: Embeddings
TOPIC_BOOK_GEN_ID = str(uuid.uuid4())      # Topic: Book Generation
TOPIC_NLP_ID = str(uuid.uuid4())           # Topic: NLP

# --- Initial Data for Seeding ---
initial_data_chunks = [
    # == Alice's Personal Docs (Historical) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_ALICE_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "document_chunk", 
        "doc_name": "Alice_Personal_Ideas.txt", 
        "text": "Idea: Use stable diffusion for generating unique cover art styles based on genre.", 
        "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
        "is_private": True,
        "is_twin_interaction": False
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_ALICE_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "document_chunk", 
        "doc_name": "Alice_Meeting_Notes_Web.md", 
        "project_id": PROJECT_PAST_WEB_ID, 
        "session_id": SESSION_WEB_PAST_ID, 
        "text": "Web Project Retro: Need better task tracking. Bob suggested ClickUp.", 
        "timestamp": (datetime.now() - timedelta(days=30)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },

    # == Bob's Personal Docs (Historical) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_BOB_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "document_chunk", 
        "doc_name": "Bob_Marketing_Notes.txt", 
        "text": "Potential niche for book gen: 'Keto recipes for busy programmers'. High search volume.", 
        "timestamp": (datetime.now() - timedelta(days=5)).isoformat(),
        "is_private": True,
        "is_twin_interaction": False
    },

    # == Charlie's Personal Docs (Historical) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_CHARLIE_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "document_chunk", 
        "doc_name": "Charlie_Tech_Thoughts.md", 
        "text": "Exploring using Markov chains for generating simple plot outlines, could be a starting point before LLM refinement.", 
        "timestamp": (datetime.now() - timedelta(days=20)).isoformat(),
        "is_private": True,
        "is_twin_interaction": False
    },

    # == Project Book Gen - Shared Docs (Past Session) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_PAST_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "document_chunk", 
        "doc_name": "BookGen_Initial_Scope.md", 
        "text": "Project Goal: Create an agent that takes a niche and outline, then generates a draft ebook.", 
        "timestamp": (datetime.now() - timedelta(days=7)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_PAST_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "transcript_snippet", 
        "user_id": USER_ALICE_ID, 
        "doc_name": "BookGen_Past_Session_Transcript.txt", 
        "text": "Alice: We need to decide on the core LLM. Claude 3 Opus seems good for long-form.", 
        "timestamp": (datetime.now() - timedelta(days=7, hours=1)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_PAST_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "transcript_snippet", 
        "user_id": USER_BOB_ID, 
        "doc_name": "BookGen_Past_Session_Transcript.txt", 
        "text": "Bob: Agreed on Opus for quality. But maybe GPT-4 for brainstorming outlines?", 
        "timestamp": (datetime.now() - timedelta(days=7, hours=1, minutes=5)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },

    # == Project Book Gen - Shared Docs (Current Session - Uploaded during session) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_CURRENT_ID, 
        "doc_id": str(uuid.uuid4()), 
        "source_type": "document_chunk", 
        "doc_name": "Competitor_Analysis.pdf", 
        "user_id": USER_BOB_ID, 
        "text": "Analysis Summary: Existing tools lack robust niche research integration.", 
        "timestamp": datetime.now().isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },

    # == Chat Messages (Historical - Past Book Gen Session) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_PAST_ID, 
        "user_id": USER_CHARLIE_ID, 
        "message_id": str(uuid.uuid4()), 
        "source_type": "message", 
        "text": "How are we handling plagiarism checks?", 
        "timestamp": (datetime.now() - timedelta(days=7, hours=1, minutes=10)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },

    # == Chat Messages (Current Session - Group Chat) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_CURRENT_ID, 
        "user_id": USER_ALICE_ID, 
        "message_id": str(uuid.uuid4()), 
        "source_type": "message", 
        "text": "Okay team, let's finalize the Q3 roadmap for the Book Generator.", 
        "timestamp": (datetime.now() - timedelta(minutes=10)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_CURRENT_ID, 
        "user_id": USER_BOB_ID, 
        "message_id": str(uuid.uuid4()), 
        "source_type": "message", 
        "text": "My main priority is integrating the niche research tool.", 
        "timestamp": (datetime.now() - timedelta(minutes=9)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "project_id": PROJECT_BOOK_GEN_ID, 
        "session_id": SESSION_BOOK_CURRENT_ID, 
        "user_id": USER_CHARLIE_ID, 
        "message_id": str(uuid.uuid4()), 
        "source_type": "message", 
        "text": "I think improving the outline generation logic is critical first.", 
        "timestamp": (datetime.now() - timedelta(minutes=8)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False
    },
    
    # == Twin Interactions (Alice's private conversation with her twin) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_ALICE_ID,
        "message_id": str(uuid.uuid4()),
        "source_type": "message",
        "text": "Twin, what do you think about using GANs for cover image generation?",
        "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
        "is_private": True,
        "is_twin_interaction": True
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_ALICE_ID,
        "message_id": str(uuid.uuid4()),
        "source_type": "message",
        "text": "I remember Bob mentioned exploring Keto recipes as a niche market. Do you think that's promising?",
        "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
        "is_private": True,
        "is_twin_interaction": True
    },
    
    # == Additional Examples with Topics (for future phases) ==
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_BOB_ID,
        "project_id": PROJECT_BOOK_GEN_ID,
        "session_id": SESSION_BOOK_CURRENT_ID,
        "message_id": str(uuid.uuid4()),
        "source_type": "message",
        "text": "I prefer specialized AI models for specific tasks over general purpose models for our book generator.",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False,
        "metadata": {
            "topics": [TOPIC_LLM_ID, TOPIC_BOOK_GEN_ID],
            "preference_type": "technical",
            "sentiment": "positive"
        }
    },
    {
        "chunk_id": str(uuid.uuid4()),
        "user_id": USER_CHARLIE_ID,
        "project_id": PROJECT_BOOK_GEN_ID,
        "session_id": SESSION_BOOK_CURRENT_ID,
        "message_id": str(uuid.uuid4()),
        "source_type": "message",
        "text": "I strongly believe we should use open-source embedding models instead of OpenAI API for cost reasons.",
        "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
        "is_private": False,
        "is_twin_interaction": False,
        "metadata": {
            "topics": [TOPIC_EMBEDDING_ID, TOPIC_NLP_ID],
            "preference_type": "technical",
            "sentiment": "strong_positive"
        }
    }
]

# --- Example Search Queries (for future reference & testing) ---

example_queries = [
    {
        "description": "Get all content from the current Book Generator session",
        "filters": {
            "project_id": PROJECT_BOOK_GEN_ID,
            "session_id": SESSION_BOOK_CURRENT_ID
        }
    },
    {
        "description": "Find Alice's private content",
        "filters": {
            "user_id": USER_ALICE_ID,
            "is_private": True
        }
    },
    {
        "description": "Find all discussions about LLMs across sessions",
        "semantic_search": "LLM language model Claude GPT-4",
        "filters": {
            "project_id": PROJECT_BOOK_GEN_ID
        }
    },
    {
        "description": "Find twin interactions for user Bob",
        "filters": {
            "user_id": USER_BOB_ID,
            "is_twin_interaction": True
        }
    }
]

# --- Helper Functions ---

def get_user_name(user_id: str) -> str:
    """Get a user's name from their ID."""
    return USERS.get(user_id, {}).get("name", "Unknown User")

def get_all_users() -> List[Dict[str, Any]]:
    """Get all users with their IDs and names."""
    return [{"id": user_id, "name": user_data["name"]} for user_id, user_data in USERS.items()]

def get_current_project_info() -> Dict[str, Any]:
    """Get information about the current project."""
    return {
        "id": PROJECT_BOOK_GEN_ID,
        "name": "Book Generator Agent",
        "current_session_id": SESSION_BOOK_CURRENT_ID,
        "participants": [
            {"id": USER_ALICE_ID, "name": "Alice"},
            {"id": USER_BOB_ID, "name": "Bob"},
            {"id": USER_CHARLIE_ID, "name": "Charlie"}
        ]
    }

def normalize_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all chunks have consistent fields by adding defaults for missing fields."""
    normalized = chunk.copy()
    
    # Ensure required fields
    normalized.setdefault("chunk_id", str(uuid.uuid4()))
    normalized.setdefault("project_id", None)
    normalized.setdefault("session_id", None)
    normalized.setdefault("user_id", None)
    normalized.setdefault("doc_id", None)
    normalized.setdefault("message_id", None)
    normalized.setdefault("source_type", "unknown")
    normalized.setdefault("text", "")
    normalized.setdefault("timestamp", datetime.now().isoformat())
    normalized.setdefault("is_private", False)
    normalized.setdefault("is_twin_interaction", False)
    normalized.setdefault("metadata", {})
    
    return normalized

# Normalize all chunks to ensure they have consistent structure
initial_data_chunks = [normalize_chunk(chunk) for chunk in initial_data_chunks]


# --- Display Helper (For Debug/Testing) ---
if __name__ == "__main__":
    print("=== TwinCore Mock Data ===")
    
    print("\n--- Core Entity IDs ---")
    print(f"USER_ALICE_ID: {USER_ALICE_ID}")
    print(f"USER_BOB_ID: {USER_BOB_ID}")
    print(f"USER_CHARLIE_ID: {USER_CHARLIE_ID}")
    print(f"PROJECT_BOOK_GEN_ID: {PROJECT_BOOK_GEN_ID}")
    print(f"SESSION_BOOK_CURRENT_ID: {SESSION_BOOK_CURRENT_ID}")
    
    print("\n--- Sample Data Chunks (First 3) ---")
    for i, chunk in enumerate(initial_data_chunks[:3]):
        print(f"\nChunk {i+1}:")
        print(f"  Text: {chunk['text']}")
        print(f"  User: {get_user_name(chunk['user_id']) if chunk['user_id'] else 'None'}")
        print(f"  Source: {chunk['source_type']}")
        print(f"  Private: {chunk['is_private']}")
        print(f"  Twin Interaction: {chunk['is_twin_interaction']}")
        
    print(f"\nTotal chunks: {len(initial_data_chunks)}")
    
    print("\n--- Example Queries ---")
    for i, query in enumerate(example_queries):
        print(f"\nQuery {i+1}: {query['description']}")
        print(f"  Filters: {query['filters']}")
        if "semantic_search" in query:
            print(f"  Semantic Search: {query['semantic_search']}") 