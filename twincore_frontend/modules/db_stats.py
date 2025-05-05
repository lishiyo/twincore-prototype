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
            make_api_call("POST", "/admin/api/seed_data")
    
    # Clear Data 
    with db_col2:
        st.write("**Danger Zone**")
        if st.button("Clear All Data", key="clear_data", type="primary", help="WARNING: This will delete all data!"):
            make_api_call("POST", "/admin/api/clear_data")
    
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
        result = make_api_call("GET", "/admin/api/stats/qdrant")
        if result:
            # Format and display the stats
            st.metric("Points Count", result.get("points_count", 0))
            st.metric("Vectors Count", result.get("vectors_count", 0))
            st.metric("Indexed Vectors", result.get("indexed_vectors_count", 0))
            
            # Display the full response as JSON for detailed view
            with st.expander("Detailed Qdrant Stats"):
                st.json(result)
            
def render_neo4j_stats():
    """Render the Neo4j stats section."""
    st.write("**Neo4j Graph Database**")
    if st.button("Get Neo4j Stats", key="neo4j_stats"):
        result = make_api_call("GET", "/admin/api/stats/neo4j")
        if result:
            # Display top-level metrics
            st.metric("Total Nodes", result.get("total_nodes", 0))
            st.metric("Total Relationships", result.get("total_relationships", 0))
            
            # Display node counts by label
            if "node_counts" in result and result["node_counts"]:
                st.write("**Node Counts by Label:**")
                for label, count in result["node_counts"].items():
                    st.write(f"- {label}: {count}")
            
            # Display relationship counts by type
            if "relationship_counts" in result and result["relationship_counts"]:
                st.write("**Relationship Counts by Type:**")
                for rel_type, count in result["relationship_counts"].items():
                    st.write(f"- {rel_type}: {count}")
            
            # Display the full response as JSON for detailed view
            with st.expander("Detailed Neo4j Stats"):
                st.json(result) 