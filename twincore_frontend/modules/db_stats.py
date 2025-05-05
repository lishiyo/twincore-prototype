"""DB Stats tab for the TwinCore Frontend.

This module handles the UI components for database statistics and management.
"""

import streamlit as st
from .utils import make_api_call

def render_db_stats_tab():
    """Render the DB Stats tab UI components."""
    st.subheader("Database Statistics (Bonus)")
    st.info("View and manage database content.")
    
    # Database management operations
    st.subheader("Database Management")
    db_col1, db_col2 = st.columns(2)
    
    # Seed Data
    with db_col1:
        st.write("**Initial Data Seeding**")
        if st.button("Seed Initial Data", key="seed_data"):
            make_api_call("POST", "/api/seed_data")
    
    # Clear Data 
    with db_col2:
        st.write("**Danger Zone**")
        if st.button("Clear All Data", key="clear_data", type="primary", help="WARNING: This will delete all data!"):
            make_api_call("DELETE", "/api/clear_data")
    
    # Stats section
    st.subheader("Database Statistics")
    stats_col1, stats_col2 = st.columns(2)
    
    # Qdrant Stats
    with stats_col1:
        render_qdrant_stats()
    
    # Neo4j Stats
    with stats_col2:
        render_neo4j_stats()
        
def render_qdrant_stats():
    """Render the Qdrant stats section."""
    st.write("**Qdrant Vector Database**")
    if st.button("Get Qdrant Stats", key="qdrant_stats"):
        # Since this endpoint doesn't exist yet, we're preparing for when it does
        try:
            make_api_call("GET", "/stats/qdrant")
        except Exception as e:
            st.warning("Qdrant stats endpoint not implemented yet. This is part of Task 8.4 (Bonus).")
            # Placeholder for future implementation
            st.json({
                "note": "Placeholder for actual stats",
                "vectors_count": "?",
                "collection_size": "?",
                "entities": {
                    "documents": "?",
                    "messages": "?",
                    "chunks": "?"
                }
            })
            
def render_neo4j_stats():
    """Render the Neo4j stats section."""
    st.write("**Neo4j Graph Database**")
    if st.button("Get Neo4j Stats", key="neo4j_stats"):
        # Since this endpoint doesn't exist yet, we're preparing for when it does
        try:
            make_api_call("GET", "/stats/neo4j")
        except Exception as e:
            st.warning("Neo4j stats endpoint not implemented yet. This is part of Task 8.4 (Bonus).")
            # Placeholder for future implementation
            st.json({
                "note": "Placeholder for actual stats",
                "nodes_count": {
                    "User": "?",
                    "Document": "?",
                    "Message": "?",
                    "Topic": "?",
                    "Project": "?",
                    "Session": "?"
                },
                "relationships_count": {
                    "AUTHORED": "?",
                    "PARTICIPATED_IN": "?",
                    "MENTIONS": "?",
                    "STATES_PREFERENCE": "?"
                }
            }) 