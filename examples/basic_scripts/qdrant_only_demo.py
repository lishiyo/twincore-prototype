# qdrant_only_demo.py

import os
import sys
import uuid
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv
from openai import OpenAI

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import sample data
try:
    from examples.basic_scripts.sample_data import memory_chunks_data, example_queries, USER_ALICE_ID, USER_BOB_ID, SESSION_P1_KICKOFF_ID, PROJECT_F0_CANVAS_ID, DOC_P1_SPEC_ID, PROJECT_TWIN_RND_ID
except ImportError:
    print("Error: Could not import from data/sample_data.py. Make sure the data directory exists and contains sample_data.py.")
    exit()

# --- Configuration ---
QDRANT_LOCATION = ":memory:" # Use in-memory for demo; or path like "./qdrant_data" or url="http://localhost:6333"
COLLECTION_NAME = "framework_zero_twin_memory"
EMBEDDING_MODEL = 'text-embedding-3-small' # OpenAI embedding model

# --- Initialize Clients ---
print(f"Initializing Qdrant client (location: {QDRANT_LOCATION})...")
qdrant = QdrantClient(location=QDRANT_LOCATION)

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    exit()

# Initialize OpenAI client
print(f"Initializing OpenAI client using model '{EMBEDDING_MODEL}'...")
openai_client = OpenAI(api_key=api_key)
vector_size = 1536  # Default for text-embedding-3-small
print(f"OpenAI embedding model initialized. Vector size: {vector_size}")

# --- Ingestion Function ---
def ingest_data_qdrant():
    print(f"\n--- Starting Qdrant Ingestion for {len(memory_chunks_data)} chunks ---")
    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    print(f"Collection '{COLLECTION_NAME}' created/recreated.")

    points_to_upsert = []
    texts_to_encode = [chunk['text'] for chunk in memory_chunks_data]

    print("Generating embeddings...")
    # Process in batches of 100 to stay within OpenAI's API limits
    batch_size = 100
    embeddings = []
    
    for i in range(0, len(texts_to_encode), batch_size):
        batch_texts = texts_to_encode[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} of {(len(texts_to_encode) + batch_size - 1)//batch_size}...")
        
        response = openai_client.embeddings.create(
            input=batch_texts,
            model=EMBEDDING_MODEL
        )
        
        batch_embeddings = [item.embedding for item in response.data]
        embeddings.extend(batch_embeddings)
    
    print("Embeddings generated.")

    for i, chunk in enumerate(memory_chunks_data):
        # Use the predefined chunk_id if available, otherwise generate one
        chunk_uuid = chunk.get('chunk_id', str(uuid.uuid4()))

        # Ensure metadata values are suitable for Qdrant (e.g., no complex objects)
        # Qdrant typically handles basic types (str, int, float, bool, lists of primitives)
        payload = chunk['metadata'].copy() # Create a copy to avoid modifying original data
        payload['text_content'] = chunk['text'] # Add the text itself to the payload for easy retrieval

        points_to_upsert.append(
            models.PointStruct(
                id=chunk_uuid,
                vector=embeddings[i],
                payload=payload
            )
        )

    print(f"Upserting {len(points_to_upsert)} points to Qdrant...")
    # Upsert in batches (Qdrant client handles batching internally, but good practice for large datasets)
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points_to_upsert, wait=True)
    print("Qdrant ingestion complete.")

# --- Retrieval Function ---
def run_qdrant_queries():
    print("\n--- Running Qdrant Retrieval Queries ---")

    # Select queries suitable for Qdrant-only filtering
    queries_to_run = [
        q for q in example_queries if q['query_description'] in [
            "GROUP: What did Bob say about the tech stack specifically in the kickoff meeting?",
            "GROUP: Summarize the F0 Canvas Core Spec document.",
            "PRIVATE: What were my (Alice's) concerns about LLM latency?",
            "PRIVATE: What did I (Alice) say about Neo4j during the Twin R&D project?",
            "CROSS-CONTEXT: Find comments from Alice mentioning Qdrant.",
        ]
    ]

    for i, query_info in enumerate(queries_to_run):
        print(f"\nQuery {i+1}: {query_info['query_description']}")
        print(f"  NL: {query_info['natural_language']}")

        # Determine search vector
        search_text = query_info['natural_language'] # Use NL query for embedding
        if query_info['semantic_search_terms']:
             # Could also average embeddings of terms, but NL is often better
             print(f"  Using NL query for semantic search vector.")
        else:
            print("  No specific semantic terms, using NL query.")

        # Generate embedding for the query
        response = openai_client.embeddings.create(
            input=[search_text],
            model=EMBEDDING_MODEL
        )
        query_vector = response.data[0].embedding

        # Build Qdrant filter from query_info['qdrant_filters']
        qdrant_filter = None
        if query_info.get('qdrant_filters'):
            filter_conditions = []
            if 'must' in query_info['qdrant_filters']:
                for condition in query_info['qdrant_filters']['must']:
                    field_condition = models.FieldCondition(
                        key=condition['key'],
                        match=models.MatchValue(**condition['match']) # Assumes 'match: {"value": ...}' structure
                        # Extend this to handle other match types (any, range, etc.) if needed
                    )
                    filter_conditions.append(field_condition)
            # Add logic for 'should', 'must_not' if needed
            if filter_conditions:
                 qdrant_filter = models.Filter(must=filter_conditions)
            print(f"  Applying Filter: {qdrant_filter}")


        search_result = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=5 # Limit results for demo
        )

        print("  Results:")
        if not search_result:
            print("    No results found.")
        for hit in search_result:
            print(f"    - Score: {hit.score:.4f}")
            # Print relevant metadata and the text
            payload = hit.payload
            text = payload.get('text_content', '[Text not in payload]')
            user = payload.get('user_id', 'N/A')
            session = payload.get('session_id', 'N/A')
            doc = payload.get('doc_id', 'N/A')
            print(f"      Text: {text[:150]}...")
            print(f"      Context: User={user}, Session={session}, Doc={doc}")
            print(f"      Payload: {payload}") # Print full payload for debugging


# --- Main Execution ---
if __name__ == "__main__":
    ingest_data_qdrant()
    run_qdrant_queries()
    print("\nQdrant Only Demo Complete.")