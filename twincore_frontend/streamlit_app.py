import streamlit as st
import requests
import json

# --- Configuration ---
st.set_page_config(layout="wide", page_title="TwinCore Verification UI")
st.title("TwinCore Backend Verification UI 🧪")
st.markdown("""
Use this UI to simulate interactions with the TwinCore backend API endpoints.
Select a user, choose a simulation type, fill in the details, and view the API response.
""")

# --- Backend API Base URL ---
# Assuming the backend runs locally on port 8000
BACKEND_URL = "http://localhost:8000/v1"

# --- Mock Data (from backend's mock_data.py) ---
MOCK_USERS = {
    "Alice": "user_1_alice",
    "Bob": "user_2_bob",
    "Charlie": "user_3_charlie",
}
MOCK_PROJECTS = {
    "Project Alpha": "project_alpha",
    "Project Beta": "project_beta",
}
MOCK_SESSIONS = {
    "Session 1 (Alpha)": "session_1_alpha",
    "Session 2 (Alpha)": "session_2_alpha",
    "Session 3 (Beta)": "session_3_beta",
}

# --- UI Layout (Placeholder for Task 8.2) ---
st.sidebar.header("User Selection")
selected_user_name = st.sidebar.selectbox("Select User", list(MOCK_USERS.keys()))
selected_user_id = MOCK_USERS[selected_user_name]
st.sidebar.write(f"Selected User ID: `{selected_user_id}`")


st.header("Simulations")

tab_canvas, tab_group_chat, tab_twin, tab_doc, tab_transcript, tab_stats = st.tabs([
    "Canvas Agent", "Group Chat", "User <> Twin", "Document Upload", "Transcript", "DB Stats (Bonus)"
])

with tab_canvas:
    st.subheader("Canvas Agent Simulations")
    # Placeholder for Canvas Agent inputs/buttons

with tab_group_chat:
    st.subheader("Group Chat Simulation")
    # Placeholder for Group Chat inputs/buttons

with tab_twin:
    st.subheader("User <> Twin Interaction")
    # Placeholder for User/Twin inputs/buttons

with tab_doc:
    st.subheader("Document Upload Simulation")
    # Placeholder for Document Upload inputs/buttons

with tab_transcript:
    st.subheader("Transcript Simulation")
    # Placeholder for Transcript inputs/buttons

with tab_stats:
    st.subheader("Database Statistics (Bonus)")
    # Placeholder for DB Stats button


st.header("API Response")
response_placeholder = st.empty()
response_placeholder.json({})

# --- Helper Functions (Placeholder for Task 8.3) ---
def make_api_call(method, endpoint, payload=None, params=None):
    """Helper function to make API calls and display the response."""
    url = f"{BACKEND_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=payload)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return

        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        response_data = response.json()
        response_placeholder.json(response_data)
        st.success(f"{method.upper()} {endpoint} successful (Status: {response.status_code})")

    except requests.exceptions.RequestException as e:
        error_message = f"API Call Error ({method.upper()} {url}): {e}"
        try:
            # Attempt to get more detail from the response body if available
            error_detail = e.response.json() if e.response else "No response body."
            error_message += f"\nResponse: {json.dumps(error_detail, indent=2)}"
            response_placeholder.json({"error": error_message, "details": error_detail})
        except Exception:
            response_placeholder.json({"error": error_message})
        st.error(error_message) 