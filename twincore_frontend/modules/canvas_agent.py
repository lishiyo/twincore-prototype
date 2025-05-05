"""Canvas Agent tab for the TwinCore Frontend.

This module handles all the UI components for simulating Canvas Agent interactions.
"""

import streamlit as st
from .config import MOCK_USERS, MOCK_PROJECTS, MOCK_SESSIONS
from .utils import make_api_call

def render_canvas_agent_tab():
    """Render the Canvas Agent tab UI components."""
    st.subheader("Canvas Agent Simulations")
    
    # Create columns for organizing UI elements
    canvas_col1, canvas_col2 = st.columns(2)
    
    # 1. Shared Context (GET /v1/retrieve/context)
    with canvas_col1.expander("Shared Context Retrieval", expanded=True):
        render_shared_context_section()
    
    # 2. User Context (GET /v1/users/{user_id}/context)
    with canvas_col2.expander("User Context Retrieval", expanded=True):
        render_user_context_section()
    
    # Second row of expanders
    canvas_col3, canvas_col4 = st.columns(2)
    
    # 3. User Preference (GET /v1/users/{user_id}/preferences)
    with canvas_col3.expander("User Preference Retrieval", expanded=False):
        render_user_preference_section()
    
    # 4. Group Context (GET /v1/retrieve/group)
    with canvas_col4.expander("Group Context Retrieval", expanded=False):
        render_group_context_section()

def render_shared_context_section():
    """Render the Shared Context retrieval section."""
    st.info("Simulates Canvas Agent retrieving context for a session or project.")
    
    # Context scope selection (Session or Project)
    context_scope = st.radio("Context Scope", ["Session", "Project"], horizontal=True)
    
    if context_scope == "Session":
        session_id = st.selectbox("Session", list(MOCK_SESSIONS.keys()))
        selected_session_id = MOCK_SESSIONS[session_id]
        project_id = None
    else:
        project_id = st.selectbox("Project", list(MOCK_PROJECTS.keys()))
        selected_project_id = MOCK_PROJECTS[project_id]
        session_id = None
    
    # Query text
    shared_context_query = st.text_area("Query Text", "What's the current context of this discussion?", 
                                        height=80, key="shared_context_query")
    
    # Optional filters
    include_messages_to_twin = st.checkbox("Include Messages to Twin", value=False, key="shared_context_twin_msg")
    shared_context_max_results = st.slider("Max Results", min_value=1, max_value=20, value=5, key="shared_context_max")
    
    if st.button("Get Shared Context", key="get_shared_context"):
        # Build parameters for the API call
        params = {
            "query_text": shared_context_query,
            "include_messages_to_twin": include_messages_to_twin,
            "max_results": shared_context_max_results
        }
        
        if context_scope == "Session":
            params["session_id"] = selected_session_id
        else:
            params["project_id"] = selected_project_id
            
        # Call the API
        make_api_call("GET", "/retrieve/context", params=params)

def render_user_context_section():
    """Render the User Context retrieval section."""
    st.info("Simulates Canvas Agent retrieving context specific to the selected user.")
    
    # User is already selected in the sidebar
    selected_user_name = st.session_state.get('selected_user_name', list(MOCK_USERS.keys())[0])
    selected_user_id = MOCK_USERS[selected_user_name]
    st.write(f"User: **{selected_user_name}** (`{selected_user_id}`)")
    
    # Optional scoping
    user_context_scope = st.radio("Additional Scope (Optional)", 
                                  ["None", "Session", "Project"], 
                                  horizontal=True, 
                                  key="user_context_scope")
    
    selected_user_session_id = None
    selected_user_project_id = None
    
    if user_context_scope == "Session":
        user_session_id = st.selectbox("Session", list(MOCK_SESSIONS.keys()), key="user_context_session")
        selected_user_session_id = MOCK_SESSIONS[user_session_id]
    elif user_context_scope == "Project":
        user_project_id = st.selectbox("Project", list(MOCK_PROJECTS.keys()), key="user_context_project")
        selected_user_project_id = MOCK_PROJECTS[user_project_id]
    
    # Query text
    user_context_query = st.text_area("Query Text", "What's this user's perspective on the discussion?", 
                                     height=80, key="user_context_query")
    
    # Filters
    include_user_messages_to_twin = st.checkbox("Include Messages to Twin", value=True, key="user_context_twin_msg")
    include_private = st.checkbox("Include Private Content", value=True, key="user_context_private")
    user_context_max_results = st.slider("Max Results", min_value=1, max_value=20, value=5, key="user_context_max")
    
    if st.button("Get User Context", key="get_user_context"):
        # Build parameters for the API call
        params = {
            "query_text": user_context_query,
            "include_messages_to_twin": include_user_messages_to_twin,
            "include_private": include_private,
            "max_results": user_context_max_results
        }
        
        if user_context_scope == "Session" and selected_user_session_id:
            params["session_id"] = selected_user_session_id
        elif user_context_scope == "Project" and selected_user_project_id:
            params["project_id"] = selected_user_project_id
            
        # Call the API
        make_api_call("GET", f"/users/{selected_user_id}/context", params=params)

def render_user_preference_section():
    """Render the User Preference retrieval section."""
    st.info("Simulates Canvas Agent retrieving user's preferences on a specific topic.")
    
    # User is already selected in the sidebar
    selected_user_name = st.session_state.get('selected_user_name', list(MOCK_USERS.keys())[0])
    selected_user_id = MOCK_USERS[selected_user_name]
    st.write(f"User: **{selected_user_name}** (`{selected_user_id}`)")
    
    # Decision topic (required)
    decision_topic = st.text_input("Decision Topic", "meeting schedule", key="preference_topic")
    
    # Optional scoping
    pref_scope = st.radio("Additional Scope (Optional)", 
                          ["None", "Project"], 
                          horizontal=True, 
                          key="pref_scope")
    
    selected_pref_project_id = None
    if pref_scope == "Project":
        pref_project_id = st.selectbox("Project", list(MOCK_PROJECTS.keys()), key="pref_project")
        selected_pref_project_id = MOCK_PROJECTS[pref_project_id]
    
    # Additional filters
    score_threshold = st.slider("Score Threshold", min_value=0.0, max_value=1.0, value=0.7, step=0.05, key="pref_threshold")
    
    if st.button("Get User Preferences", key="get_preferences"):
        # Build parameters for the API call
        params = {
            "decision_topic": decision_topic,
            "score_threshold": score_threshold
        }
        
        if pref_scope == "Project" and selected_pref_project_id:
            params["project_id"] = selected_pref_project_id
            
        # Call the API
        make_api_call("GET", f"/users/{selected_user_id}/preferences", params=params)

def render_group_context_section():
    """Render the Group Context retrieval section."""
    st.info("Simulates Canvas Agent retrieving context across all participants in a group.")
    
    # Group scope selection (Session, Project, or Team)
    group_scope = st.radio("Group Scope", ["Session", "Project", "Team"], horizontal=True, key="group_scope")
    
    if group_scope == "Session":
        group_session_id = st.selectbox("Session", list(MOCK_SESSIONS.keys()), key="group_session")
        selected_group_id = MOCK_SESSIONS[group_session_id]
        scope_param = "session_id"
    elif group_scope == "Project":
        group_project_id = st.selectbox("Project", list(MOCK_PROJECTS.keys()), key="group_project")
        selected_group_id = MOCK_PROJECTS[group_project_id]
        scope_param = "project_id"
    else:  # Team scope
        team_id = st.text_input("Team ID", "team_product_design", key="group_team")
        selected_group_id = team_id
        scope_param = "team_id"
    
    # Query text
    group_query = st.text_area("Query Text", "What's everyone working on?", 
                              height=80, key="group_query")
    
    # Filters
    group_twin_messages = st.checkbox("Include Messages to Twin", value=False, key="group_twin_msg")
    group_max_results = st.slider("Max Results Per User", min_value=1, max_value=10, value=3, key="group_max")
    
    if st.button("Get Group Context", key="get_group_context"):
        # Build parameters for the API call
        params = {
            "query_text": group_query,
            "include_messages_to_twin": group_twin_messages,
            "max_results_per_user": group_max_results,
            scope_param: selected_group_id
        }
            
        # Call the API
        make_api_call("GET", "/retrieve/group", params=params) 