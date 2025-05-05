"""Configuration module for the TwinCore Frontend.

Contains the API base URL, mock data, and other constants.
"""

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