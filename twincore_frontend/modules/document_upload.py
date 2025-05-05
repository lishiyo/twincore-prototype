"""Document Upload tab for the TwinCore Frontend.

This module handles the UI components for simulating document uploads.
"""

import streamlit as st
from .config import MOCK_USERS, MOCK_PROJECTS, MOCK_SESSIONS
from .utils import make_api_call

def render_document_upload_tab():
    """Render the Document Upload tab UI components."""
    st.subheader("Document Upload Simulation")
    st.info("Simulates uploading a document to the system, with options for privacy and context.")
    
    # Document input form
    with st.form("document_upload_form"):
        # Get current user from session state
        selected_user_name = st.session_state.get('selected_user_name', list(MOCK_USERS.keys())[0])
        selected_user_id = MOCK_USERS[selected_user_name]
        
        # User info
        st.write(f"User: **{selected_user_name}** (`{selected_user_id}`)")
        
        # Document metadata
        doc_name = st.text_input("Document Name", "Project Roadmap", key="doc_name")
        
        # Document content
        doc_content = st.text_area("Document Content", 
                               """This document outlines our Q3 roadmap.
                               
Key deliverables:
1. Complete API refactoring by July 15th
2. Launch beta version to select customers by August 1st
3. Gather feedback and implement improvements by Sept 15th

We should prioritize performance optimizations and the new authentication system.""",
                               height=200, 
                               key="doc_content")
        
        # Privacy and context
        doc_col1, doc_col2 = st.columns(2)
        
        with doc_col1:
            is_private = st.checkbox("Mark as Private", value=False, 
                                  help="Private documents are only visible to the owner.")
            
            doc_session = st.selectbox("Session (Optional)", ["None"] + list(MOCK_SESSIONS.keys()), key="doc_session")
            selected_doc_session_id = None
            if doc_session != "None":
                selected_doc_session_id = MOCK_SESSIONS[doc_session]
        
        with doc_col2:
            doc_source = st.text_input("Source URI (Optional)", "https://company-drive.com/docs/roadmap.pdf", key="doc_source")
            
            doc_project = st.selectbox("Project (Optional)", ["None"] + list(MOCK_PROJECTS.keys()), key="doc_project")
            selected_doc_project_id = None
            if doc_project != "None":
                selected_doc_project_id = MOCK_PROJECTS[doc_project]
        
        # Document metadata (optional)
        with st.expander("Additional Metadata (Optional)", expanded=False):
            doc_type = st.selectbox("Document Type", ["report", "meeting_notes", "research", "email", "other"], key="doc_type")
            doc_tags = st.text_input("Tags (comma-separated)", "roadmap, planning, Q3", key="doc_tags")
            doc_importance = st.slider("Importance", min_value=1, max_value=5, value=3, key="doc_importance")
        
        # Submit button
        submitted = st.form_submit_button("Upload Document")
        
        if submitted:
            # Process tags
            tags_list = [tag.strip() for tag in doc_tags.split(",") if tag.strip()]
            
            # Prepare payload for the API call
            payload = {
                "user_id": selected_user_id,
                "doc_name": doc_name,
                "text": doc_content,
                "is_private": is_private,
                "source_type": "document",
                "metadata": {
                    "doc_type": doc_type,
                    "importance": doc_importance,
                    "tags": tags_list
                }
            }
            
            # Add optional fields if provided
            if selected_doc_session_id:
                payload["session_id"] = selected_doc_session_id
                
            if selected_doc_project_id:
                payload["project_id"] = selected_doc_project_id
                
            if doc_source:
                payload["source_uri"] = doc_source
            
            # Call the API
            make_api_call("POST", "/ingest/document", payload=payload) 