"""Twin Interaction tab for the TwinCore Frontend.

This module handles the UI components for simulating user-twin interactions.
"""

import streamlit as st
from .config import MOCK_USERS, MOCK_PROJECTS, MOCK_SESSIONS
from .utils import make_api_call

def render_twin_interaction_tab():
    """Render the User <> Twin Interaction tab UI components."""
    st.subheader("User <> Twin Interaction")
    st.info("Simulates a user querying their Twin agent, which ingests the query and returns private memory results.")
    
    # Message input form
    with st.form("twin_interaction_form"):
        # Get current user from session state
        selected_user_name = st.session_state.get('selected_user_name', list(MOCK_USERS.keys())[0])
        selected_user_id = MOCK_USERS[selected_user_name]
        
        # User info
        st.write(f"User: **{selected_user_name}** (`{selected_user_id}`)")
        
        # Context selection (optional)
        twin_col1, twin_col2 = st.columns(2)
        
        with twin_col1:
            include_session = st.checkbox("Include Session Context", value=True)
            selected_twin_session_id = None
            if include_session:
                twin_session = st.selectbox("Session", list(MOCK_SESSIONS.keys()), key="twin_session")
                selected_twin_session_id = MOCK_SESSIONS[twin_session]
        
        with twin_col2:
            include_project = st.checkbox("Include Project Context", value=True)
            selected_twin_project_id = None
            if include_project:
                twin_project = st.selectbox("Project", list(MOCK_PROJECTS.keys()), key="twin_project")
                selected_twin_project_id = MOCK_PROJECTS[twin_project]
        
        # Query to Twin
        twin_query = st.text_area("Your Question to Twin", 
                                "What documents did I share about machine learning last week?",
                                height=120, 
                                key="twin_query")
        
        # Filters
        twin_col3, twin_col4 = st.columns(2)
        
        with twin_col3:
            # This is always true for private memory endpoint - showing for transparency
            st.checkbox("Include Messages to Twin", value=True, disabled=True, 
                      help="Private memory always includes messages to twin.")
                      
            # Max results
            twin_max_results = st.slider("Max Results", min_value=1, max_value=20, value=5, key="twin_max")
        
        with twin_col4:
            score_threshold = st.slider("Score Threshold", min_value=0.0, max_value=1.0, value=0.6, step=0.05, key="twin_threshold")
            
            include_graph = st.checkbox("Include Graph", value=False, 
                                      help="Return graph relationships for results.")
        
        # Submit button
        submitted = st.form_submit_button("Ask Twin")
        
        if submitted:
            # Prepare payload for the API call
            payload = {
                "query_text": twin_query,
                "max_results": twin_max_results,
                "score_threshold": score_threshold,
                "include_graph": include_graph
            }
            
            # Add optional context parameters if selected
            if include_session and selected_twin_session_id:
                payload["session_id"] = selected_twin_session_id
                
            if include_project and selected_twin_project_id:
                payload["project_id"] = selected_twin_project_id
            
            # Call the API - this endpoint both ingests the query and returns private memory
            make_api_call("POST", f"/users/{selected_user_id}/private_memory", payload=payload) 