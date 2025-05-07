#!/usr/bin/env python3
"""
Script to test the "Whole Context" approach with Gemini 2.5 Pro.
This script loads all mock data from the mock_data directory, concatenates it,
and sends the entire context to Gemini along with various test queries.
"""

import os
import json
from datetime import datetime
from google import genai  # Updated import
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()  # First try to load from the current directory's .env
# Also try to load from the root project .env if in a subdirectory
root_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
if os.path.exists(root_env_path):
    load_dotenv(root_env_path)

# Constants
MOCK_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data")
PROJECT_ID = "f4f7e3c8-2f8d-4f8c-9d7f-3e1a0c7d7f00"
USER_IDS = {
    "alex": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "ben": "b2c3d4e5-f6a7-8901-2345-67890abcdef0",
    "chloe": "c3d4e5f6-a7b8-9012-3456-7890abcdef01",
    "dana": "d4e5f6a7-b8c9-0123-4567-890abcdef012",
    "ethan": "e5f6a7b8-c9d0-1234-5678-90abcdef0123",
    "fiona": "f6a7b8c9-d0e1-2345-6789-0abcdef01234"
}
SESSION_IDS = {
    "s1_kickoff": "s1a2b3c4-d5e6-f7a8-b9c0-d1e2f3a4b5c6",
    "s2_tech": "s2b3c4d5-e6f7-a8b9-c0d1-e2f3a4b5c6d7",
    "s3_client": "s3c4d5e6-f7a8-b9c0-d1e2-f3a4b5c6d7e8",
    "s4_mvp": "s4d5e6f7-a8b9-c0d1-e2f3-a4b5c6d7e8f9"
}

def setup_gemini() -> bool:
    """Configure and initialize the Gemini API client."""
    try:
        # Use the new method to configure with api_key
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY environment variable not set!")
            print("Please set it to use the Gemini API.")
            return False
        
        # Initialize the client with the API key
        genai.Client(api_key=api_key)
        print("✅ Gemini API client initialized successfully.")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Gemini API client: {e}")
        return False

def load_all_mock_data(mock_data_path: str = MOCK_DATA_PATH) -> str:
    """
    Load all mock data files from the specified directory and concatenate their contents.
    
    Args:
        mock_data_path: Path to the mock_data directory
        
    Returns:
        A string containing the concatenated contents of all files with proper separators
    """
    if not os.path.exists(mock_data_path):
        raise FileNotFoundError(f"Mock data directory not found: {mock_data_path}")
    
    all_content = []
    
    # List of supported file extensions to process
    supported_extensions = ['.txt', '.md', '.csv', '.mermaid']
    
    # Categories of data to process, matching the directory structure
    categories = ['session_transcripts', 'shared_docs', 'private_docs', 'twin_chats']
    
    for category in categories:
        category_path = os.path.join(mock_data_path, category)
        if not os.path.exists(category_path):
            print(f"Warning: Category directory not found: {category_path}")
            continue
        
        for filename in os.listdir(category_path):
            file_path = os.path.join(category_path, filename)
            _, ext = os.path.splitext(filename)
            
            if os.path.isfile(file_path) and ext.lower() in supported_extensions:
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        file_content = file.read()
                    
                    # Create a relative path for display (from mock_data onwards)
                    relative_path = os.path.join(category, filename)
                    
                    # Format the content with clear separators
                    formatted_content = f"""
--- START DOCUMENT: {relative_path} ---
{file_content}
--- END DOCUMENT: {relative_path} ---
"""
                    all_content.append(formatted_content)
                    print(f"✅ Loaded: {relative_path}")
                except Exception as e:
                    print(f"❌ Failed to read {file_path}: {e}")
    
    # Concatenate all content
    concatenated_content = "\n".join(all_content)
    
    # Report on the loaded content
    total_files = len(all_content)
    total_chars = len(concatenated_content)
    print(f"📝 Loaded {total_files} files totaling {total_chars} characters.")
    
    return concatenated_content

def query_gemini_with_whole_context(full_context: str, user_query: str, user_name: Optional[str] = None) -> str:
    """
    Send a query to Gemini 2.5 Pro with the entire context.
    
    Args:
        full_context: The concatenated content of all documents
        user_query: The user's query
        user_name: Optional name of the user if the query is user-specific
        
    Returns:
        Gemini's response text
    """
    try:
        # Get the client
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        # Get the model name from environment variable
        model_name = os.environ.get("GEMINI_MODEL")
        if not model_name:
            return "Error: GEMINI_MODEL environment variable not set."
        
        # Construct the prompt based on query type
        if user_name:
            prompt_content = f"""
Based on the following collection of documents, transcripts, and chat logs for the Framework Zero project, 
paying close attention to information related to {user_name}, please answer the question:

QUESTION: {user_query}

DOCUMENTS:
{full_context}
"""
        else:
            prompt_content = f"""
Based on the following collection of documents, transcripts, and chat logs for the Framework Zero project, 
please answer the question:

QUESTION: {user_query}

DOCUMENTS:
{full_context}
"""
        
        # Send the prompt to Gemini
        # The generate_content method is on client.models and takes the model name as an argument
        response = client.models.generate_content(model=model_name, contents=prompt_content)
        
        return response.text
    except Exception as e:
        return f"Error querying Gemini: {str(e)}"

def main():
    """Main function to run the whole context script."""
    # Check that Gemini API is properly configured
    if not setup_gemini():
        return
    
    # Load all mock data
    try:
        print("\n🔄 Loading all mock data...")
        full_context = load_all_mock_data()
    except Exception as e:
        print(f"❌ Failed to load mock data: {e}")
        return
    
    # Define test queries based on mainUseCases.md
    test_queries = [
        # General project context queries
        {"query": "Did I forget someone's feedback?", "user_name": None},
        {"query": "What should the agenda for this meeting be?", "user_name": None},
        {"query": "What are the most important action items from the last meeting to cover?", "user_name": None},
        {"query": "What decisions have we made so far, and what do we still need to decide?", "user_name": None},
        
        # User-specific queries
        {"query": "What would Alex want in this scenario?", "user_name": "Alex"},
        {"query": "What does everyone think about using S3 for storage?", "user_name": None},
        {"query": "What are everyone's pain points from previous sessions that we haven't spoken about yet?", "user_name": None},
        
        # Private twin chat queries
        {"query": "Did I forget to bring up something I mentioned before in a previous session?", "user_name": "Ben"},
        {"query": "What are all the action items that I still need to do?", "user_name": "Chloe"},
        {"query": "Is there something I should bring up?", "user_name": "Dana"},
        {"query": "What do other people think about the new company logo?", "user_name": "Ethan"}
    ]
    
    # Process each query and store results
    results = []
    
    print("\n🔍 Processing queries with Gemini 2.5 Pro...\n")
    
    for idx, query_info in enumerate(test_queries, 1):
        query = query_info["query"]
        user_name = query_info["user_name"]
        
        print(f"\n{'='*80}")
        print(f"QUERY {idx}: {query}")
        if user_name:
            print(f"USER CONTEXT: {user_name}")
        print(f"{'='*80}\n")
        
        # Time the query for latency comparison
        start_time = datetime.now()
        response_text = query_gemini_with_whole_context(full_context, query, user_name)
        end_time = datetime.now()
        
        # Calculate time taken
        time_taken = (end_time - start_time).total_seconds()
        
        print(f"\nGEMINI RESPONSE:\n{response_text}")
        print(f"\nTime taken: {time_taken:.2f} seconds")
        
        # Store the result
        results.append({
            "query": query,
            "user_name": user_name,
            "response": response_text,
            "time_taken": time_taken
        })
    
    # Save results to a file for later comparison
    output_file = "./examples/framework_zero/whole_context_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")

if __name__ == "__main__":
    main() 