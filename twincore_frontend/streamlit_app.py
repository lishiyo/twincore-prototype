"""TwinCore Backend Verification UI.

This is the main entry point for the Streamlit app.
"""

import streamlit as st
from modules import (
    MOCK_USERS,
    MOCK_PROJECTS,
    MOCK_SESSIONS,
    make_api_call,
    render_canvas_agent_tab,
    render_group_chat_tab,
    render_twin_interaction_tab,
    render_document_upload_tab,
    render_transcript_tab,
    render_db_stats_tab
)

# --- Configuration ---
st.set_page_config(layout="wide", page_title="TwinCore Verification UI")
st.title("TwinCore Backend Verification UI 🧪")
st.markdown("""
Use this UI to simulate interactions with the TwinCore backend API endpoints.
Select a user, choose a simulation type, fill in the details, and view the API response.
""")

# --- UI Layout ---

# User selection sidebar
st.sidebar.header("User Selection")
selected_user_name = st.sidebar.selectbox("Select User", list(MOCK_USERS.keys()))
selected_user_id = MOCK_USERS[selected_user_name]
st.sidebar.write(f"Selected User ID: `{selected_user_id}`")

# Store the selected user in session state for other components to access
st.session_state['selected_user_name'] = selected_user_name
st.session_state['selected_user_id'] = selected_user_id

# Quick Access Actions
st.sidebar.header("Quick Actions")
seed_col1, seed_col2 = st.sidebar.columns(2)

with seed_col1:
    if st.button("🌱 Seed Data", key="sidebar_seed"):
        make_api_call("POST", "/api/seed_data")
        
with seed_col2:
    if st.button("🧹 Clear Data", key="sidebar_clear"):
        make_api_call("DELETE", "/api/clear_data")

st.sidebar.markdown("---")
st.sidebar.info("Remember to seed data first if you've just started the backend!")

# Main content area
st.header("Simulations")

# Create tabs for different simulation types
tab_canvas, tab_group_chat, tab_twin, tab_doc, tab_transcript, tab_stats = st.tabs([
    "Canvas Agent", "Group Chat", "User <> Twin", "Document Upload", "Transcript", "DB Stats (Bonus)"
])

# Response area (at the bottom of the page, but defined here so components can use it)
st.header("API Response")
response_placeholder = st.empty()
response_placeholder.json({})

# Store the response placeholder in session state for components to access
st.session_state['response_placeholder'] = response_placeholder

# Render each tab's content
with tab_canvas:
    render_canvas_agent_tab()

with tab_group_chat:
    render_group_chat_tab()

with tab_twin:
    render_twin_interaction_tab()

with tab_doc:
    render_document_upload_tab()

with tab_transcript:
    render_transcript_tab()

with tab_stats:
    render_db_stats_tab() 