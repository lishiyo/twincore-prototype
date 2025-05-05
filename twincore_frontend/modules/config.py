"""Configuration module for the TwinCore Frontend.

Contains the API base URL, mock data, and other constants.
"""

# --- Backend API Base URL ---
# Assuming the backend runs locally on port 8000
BACKEND_URL = "http://localhost:8000/v1"

# --- Mock Data (Consistent with backend core/mock_data.py) ---
# Use the same predefined UUIDs as the backend mock data
MOCK_USERS = {
    "Alice": "a11ce000-0000-0000-0000-000000000001",
    "Bob": "b0b0b0b0-0000-0000-0000-000000000002",
    "Charlie": "c4a111e0-0000-0000-0000-000000000003",
}

MOCK_PROJECTS = {
    "Book Generator Agent": "b0000000-6e40-0000-0000-000000000001",
    "Past Web Project": "web00000-0000-0000-0000-000000000002",
}

MOCK_SESSIONS = {
    "Book Gen - Current": "5e551011-c41e-0000-0000-000000000001",
    "Book Gen - Past": "5e551011-a570-0000-0000-000000000002",
    "Web Project - Past": "5e551011-web0-0000-0000-000000000003",
} 