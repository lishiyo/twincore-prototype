"""Transcript tab for the TwinCore Frontend.

This module handles the UI components for simulating transcript chunk ingestion.
"""

import streamlit as st
from datetime import datetime
from .config import MOCK_USERS, MOCK_PROJECTS, MOCK_SESSIONS
from .utils import make_api_call

def render_transcript_tab():
    """Render the Transcript tab UI components."""
    st.subheader("Transcript Simulation")
    st.info("Simulates real-time transcript chunk ingestion and final metadata update.")
    
    # Persistent transcript ID field at the top
    transcript_doc_id = st.text_input("Transcript Document ID", "transcript_meeting_20250506", 
                                    help="Use this as the identifier for all chunks belonging to the same transcript.")
    
    col1, col2 = st.columns(2)
    
    # --- Left column: Utterance Chunk Ingestion ---
    with col1:
        st.subheader("1. Send Utterance Chunks")
        st.write("Simulate chunks arriving in real-time during meeting.")
        
        render_chunk_ingestion_form(transcript_doc_id)
    
    # --- Right column: Finalize Transcript ---
    with col2:
        st.subheader("2. Finalize Transcript")
        st.write("Update metadata once transcript is complete.")
        
        render_metadata_update_form(transcript_doc_id)
        
def render_chunk_ingestion_form(transcript_doc_id):
    """Render the Utterance Chunk ingestion form."""
    # Chunk input form
    with st.form("utterance_chunk_form"):
        # Get current user from session state for default selection
        selected_user_name = st.session_state.get('selected_user_name', list(MOCK_USERS.keys())[0])
        
        # User selection for the speaker
        chunk_user = st.selectbox("Speaker", list(MOCK_USERS.keys()), key="chunk_user", index=list(MOCK_USERS.keys()).index(selected_user_name))
        selected_chunk_user_id = MOCK_USERS[chunk_user]
        
        # Utterance content
        utterance_text = st.text_area("Utterance Text", 
                                   "I think we should prioritize the authentication system first.",
                                   height=100, 
                                   key="utterance_text")
        
        # Context selection
        chunk_session = st.selectbox("Session", list(MOCK_SESSIONS.keys()), key="chunk_session")
        selected_chunk_session_id = MOCK_SESSIONS[chunk_session]
        
        chunk_project = st.selectbox("Project", list(MOCK_PROJECTS.keys()), key="chunk_project")
        selected_chunk_project_id = MOCK_PROJECTS[chunk_project]
        
        # Chunk metadata
        with st.expander("Chunk Metadata (Optional)", expanded=False):
            chunk_start_time = st.text_input("Start Time", "00:05:23", key="chunk_start_time")
            chunk_end_time = st.text_input("End Time", "00:05:31", key="chunk_end_time")
            chunk_index = st.number_input("Chunk Index", min_value=0, value=1, step=1, key="chunk_index")
        
        # Submit button
        submitted = st.form_submit_button("Send Utterance Chunk")
        
        if submitted:
            if not transcript_doc_id:
                st.error("Please enter a Transcript Document ID at the top.")
            else:
                # Current timestamp
                current_timestamp = datetime.now().isoformat()
                
                # Prepare payload for the API call
                payload = {
                    "doc_id": transcript_doc_id,
                    "user_id": selected_chunk_user_id,
                    "chunk_text": utterance_text,
                    "session_id": selected_chunk_session_id,
                    "project_id": selected_chunk_project_id,
                    "timestamp": current_timestamp,
                    "metadata": {
                        "start_time": chunk_start_time,
                        "end_time": chunk_end_time,
                        "chunk_index": chunk_index
                    }
                }
                
                # Call the API
                make_api_call("POST", "/ingest/chunk", payload=payload)
                
def render_metadata_update_form(transcript_doc_id):
    """Render the transcript metadata update form."""
    # Metadata update form
    with st.form("transcript_metadata_form"):
        # Final metadata
        source_uri = st.text_input("Source URI", "https://meetings.company.com/recordings/20250506-team.mp4", 
                                help="URL where the full recording/transcript is stored.")
        
        transcript_title = st.text_input("Transcript Title", "Weekly Team Sync - May 6, 2025")
        
        transcript_type = st.selectbox("Transcript Type", 
                                   ["meeting", "interview", "presentation", "conversation"], 
                                   key="transcript_type")
        
        with st.expander("Additional Metadata", expanded=False):
            meeting_duration = st.text_input("Duration", "45:32")
            participant_count = st.number_input("Participant Count", min_value=1, value=5, step=1)
            transcript_tags = st.text_input("Tags (comma-separated)", "team-sync, planning, authentication")
        
        # Submit button
        submitted = st.form_submit_button("Finalize Transcript")
        
        if submitted:
            if not transcript_doc_id:
                st.error("Please enter a Transcript Document ID at the top.")
            else:
                # Process tags
                tags_list = [tag.strip() for tag in transcript_tags.split(",") if tag.strip()]
                
                # Prepare payload for the API call
                payload = {
                    "source_uri": source_uri,
                    "metadata": {
                        "title": transcript_title,
                        "type": transcript_type,
                        "duration": meeting_duration,
                        "participant_count": participant_count,
                        "tags": tags_list,
                        "finalized": True
                    }
                }
                
                # Call the API
                make_api_call("POST", f"/documents/{transcript_doc_id}/metadata", payload=payload) 