"""Group Chat tab for the TwinCore Frontend.

This module handles the UI components for simulating group chat messages.
"""

import streamlit as st
from .config import MOCK_USERS, MOCK_PROJECTS, MOCK_SESSIONS
from .utils import make_api_call

def render_group_chat_tab():
    """Render the Group Chat tab UI components."""
    st.subheader("Group Chat Simulation")
    st.info("Simulates sending a message within a group context (session and project).")
    
    # Message input form
    with st.form("group_chat_form"):
        # Get current user from session state
        selected_user_name = st.session_state.get('selected_user_name', list(MOCK_USERS.keys())[0])
        selected_user_id = MOCK_USERS[selected_user_name]
        
        st.write(f"Sender: **{selected_user_name}** (`{selected_user_id}`)")
        
        # Session and project context
        group_chat_col1, group_chat_col2 = st.columns(2)
        
        with group_chat_col1:
            chat_session = st.selectbox("Session", list(MOCK_SESSIONS.keys()), key="chat_session")
            selected_chat_session_id = MOCK_SESSIONS[chat_session]
        
        with group_chat_col2:
            chat_project = st.selectbox("Project", list(MOCK_PROJECTS.keys()), key="chat_project")
            selected_chat_project_id = MOCK_PROJECTS[chat_project]
        
        # Message content
        message_text = st.text_area("Message Content", 
                                  "Here's my update for the team...",
                                  height=120, 
                                  key="group_message_text")
        
        # Optional metadata
        st.write("Optional Message Metadata:")
        chat_col3, chat_col4 = st.columns(2)
        
        with chat_col3:
            message_type = st.selectbox("Message Type", 
                                      ["text", "question", "decision", "action_item"], 
                                      key="message_type")
            
        with chat_col4:
            importance = st.slider("Importance", min_value=1, max_value=5, value=3, key="message_importance")
        
        # Submit button
        submitted = st.form_submit_button("Send Group Message")
        
        if submitted:
            # Prepare payload for the API call
            payload = {
                "user_id": selected_user_id,
                "text": message_text,
                "source_type": "message",
                "session_id": selected_chat_session_id,
                "project_id": selected_chat_project_id,
                "metadata": {
                    "message_type": message_type,
                    "importance": importance
                }
            }
            
            # Call the API
            make_api_call("POST", "/ingest/message", payload=payload) 