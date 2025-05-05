"""Utility functions for the TwinCore Frontend."""

import json
import requests
import streamlit as st
from .config import BACKEND_URL

def make_api_call(method, endpoint, payload=None, params=None, response_placeholder=None):
    """Helper function to make API calls and display the response.
    
    Args:
        method (str): HTTP method (GET, POST, DELETE)
        endpoint (str): API endpoint path
        payload (dict, optional): JSON payload for POST/PUT requests
        params (dict, optional): Query parameters for GET requests
        response_placeholder (streamlit.empty): Placeholder to display the response
        
    Returns:
        dict: The JSON response from the API
    """
    if response_placeholder is None:
        response_placeholder = st.session_state.get('response_placeholder')
        
    url = f"{BACKEND_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=payload)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, json=payload)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return

        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        response_data = response.json()
        
        if response_placeholder:
            response_placeholder.json(response_data)
        
        st.success(f"{method.upper()} {endpoint} successful (Status: {response.status_code})")
        return response_data

    except requests.exceptions.RequestException as e:
        error_message = f"API Call Error ({method.upper()} {url}): {e}"
        try:
            # Attempt to get more detail from the response body if available
            error_detail = e.response.json() if e.response else "No response body."
            error_message += f"\nResponse: {json.dumps(error_detail, indent=2)}"
            
            if response_placeholder:
                response_placeholder.json({"error": error_message, "details": error_detail})
        except Exception:
            if response_placeholder:
                response_placeholder.json({"error": error_message})
        
        st.error(error_message)
        return None 