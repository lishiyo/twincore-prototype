# qdrant_neo4j_demo.py

import os
import uuid
from qdrant_client import QdrantClient, models
from neo4j import GraphDatabase, basic_auth
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import sample data and IDs
try:
    from data.sample_data import memory_chunks_data, example_queries, USER_ALICE_ID, USER_BOB_ID, SESSION_P1_KICKOFF_ID, PROJECT_F0_CANVAS_ID, PROJECT_TWIN_RND_ID
except ImportError:
    print("Error: Could not import from sample_data.py. Make sure it's in the same directory.")
    exit()

# --- Configuration ---
QDRANT_LOCATION = ":memory:"
COLLECTION_NAME = "framework_zero_twin_memory_combined"
EMBEDDING_MODEL = 'text-embedding-3-small'

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password") # Replace with your password

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

print(f"Connecting to Neo4j at {NEO4J_URI}...")
try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USERNAME, NEO4J_PASSWORD))
    neo4j_driver.verify_connectivity()
    print("Neo4j connection successful.")
except Exception as e:
    print(f"Error connecting to Neo4j: {e}")
    exit()

# --- Neo4j Helper Functions (copied from neo4j_only_demo.py) ---
def run_write_query(tx, query, **params):
    result = tx.run(query, **params)
    return result.consume()

def run_read_query(tx, query, **params):
    result = tx.run(query, **params)
    return [record.data() for record in result]

def create_graph_elements(tx, meta, text_content):
    # Simplified version - assumes nodes exist if IDs are present
    # In production, use MERGE as in neo4j_only_demo.py for robustness
    if meta.get('org_id'): tx.run("MERGE (:Organization {orgId: $org_id})", org_id=meta['org_id'])
    if meta.get('team_id'): tx.run("MERGE (:Team {teamId: $team_id})", team_id=meta['team_id'])
    if meta.get('project_id'): tx.run("MERGE (:Project {projectId: $project_id})", project_id=meta['project_id'])
    if meta.get('session_id'): tx.run("MERGE (:Session {sessionId: $session_id})", session_id=meta['session_id'])
    if meta.get('doc_id'): tx.run("MERGE (:Document {docId: $doc_id})", doc_id=meta['doc_id'])
    if meta.get('message_id'): tx.run("MERGE (:Message {messageId: $message_id})", message_id=meta['message_id'])
    if meta.get('user_id'): tx.run("MERGE (:User {userId: $user_id})", user_id=meta['user_id'])

    # Create Relationships (Simplified - assumes nodes exist)
    if meta.get('user_id') and meta.get('session_id'):
        tx.run("MATCH (u:User {userId:$uid}), (s:Session {sessionId:$sid}) MERGE (u)-[:PARTICIPATED_IN]->(s)", uid=meta['user_id'], sid=meta['session_id'])
    if meta.get('user_id') and meta.get('message_id'):
        tx.run("MATCH (u:User {userId:$uid}), (m:Message {messageId:$mid}) MERGE (u)-[:AUTHORED]->(m)", uid=meta['user_id'], mid=meta['message_id'])
    if meta.get('message_id') and meta.get('session_id'):
        tx.run("MATCH (m:Message {messageId:$mid}), (s:Session {sessionId:$sid}) MERGE (m)-[:POSTED_IN]->(s)", mid=meta['message_id'], sid=meta['session_id'])
    if meta.get('session_id') and meta.get('project_id'):
        tx.run("MATCH (s:Session {sessionId:$sid}), (p:Project {projectId:$pid}) MERGE (s)-[:PART_OF]->(p)", sid=meta['session_id'], pid=meta['project_id'])
    
    # Add document relationships
    if meta.get('doc_id') and meta.get('session_id'):
        tx.run("MATCH (d:Document {docId:$did}), (s:Session {sessionId:$sid}) MERGE (d)-[:ATTACHED_TO]->(s)", did=meta['doc_id'], sid=meta['session_id'])
    if meta.get('doc_id') and meta.get('project_id') and not meta.get('session_id'):
        tx.run("MATCH (d:Document {docId:$did}), (p:Project {projectId:$pid}) MERGE (d)-[:RELATED_TO]->(p)", did=meta['doc_id'], pid=meta['project_id'])

# --- Combined Ingestion Function ---
def ingest_data_combined():
    print("\n--- Starting Combined Qdrant & Neo4j Ingestion ---")

    # 1. Qdrant Ingestion
    print("Ingesting into Qdrant...")
    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    
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
    
    points_to_upsert = []
    for i, chunk in enumerate(memory_chunks_data):
        chunk_uuid = chunk.get('chunk_id', str(uuid.uuid4()))
        payload = chunk['metadata'].copy()
        
        # Check if message_id exists at the chunk level
        message_id = chunk.get('message_id')
        if message_id and not payload.get('message_id'):
            payload['message_id'] = message_id
            
        payload['text_content'] = chunk['text']
        points_to_upsert.append(
            models.PointStruct(id=chunk_uuid, vector=embeddings[i], payload=payload)
        )
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points_to_upsert, wait=True)
    print("Qdrant ingestion complete.")

    # 2. Neo4j Ingestion
    print("Ingesting relationships into Neo4j...")
    print("Clearing existing Neo4j graph data...")
    with neo4j_driver.session(database="neo4j") as session:
        session.execute_write(run_write_query, "MATCH (n) DETACH DELETE n")
        # Apply constraints (essential for performance and correctness with MERGE)
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.userId IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.projectId IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.sessionId IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Message) REQUIRE m.messageId IS UNIQUE",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.docId IS UNIQUE",
            # Add others...
        ]
        for constraint in constraints:
            try: session.execute_write(run_write_query, constraint)
            except Exception: pass # Ignore if exists
        print("Neo4j constraints applied.")

        print("Processing chunks for Neo4j graph...")
        # Use simplified create_graph_elements for demo speed
        # Replace with robust MERGE logic from neo4j_only_demo for production
        for i, chunk in enumerate(memory_chunks_data):
             meta = chunk['metadata'].copy()
             # Check if message_id exists at the chunk level
             message_id = chunk.get('message_id')
             if message_id and not meta.get('message_id'):
                 meta['message_id'] = message_id
             session.execute_write(create_graph_elements, meta, chunk['text'])
             if (i + 1) % 5 == 0: print(f"  Processed {i+1}/{len(memory_chunks_data)} chunks for Neo4j...")
    print("Neo4j ingestion complete.")

# --- Combined Retrieval Function ---
def run_combined_queries():
    print("\n--- Running Combined Neo4j + Qdrant Retrieval Queries ---")

    # Define additional combined queries
    combined_queries = [
        # Existing query
        next((q for q in example_queries if q['query_description'] == "RELATIONSHIP + SEMANTIC: Who participated in the F0 Canvas Core kickoff? And what did they say about the MVP scope?"), None),
        
        # New query 1: Find document content about vector search related to F0 Canvas project
        {
            "query_description": "RELATIONSHIP + SEMANTIC: What do F0 Canvas project documents say about vector search technology?",
            "natural_language": "What information is available about vector search in the F0 Canvas project documents?",
            "neo4j_query_part": """
                MATCH (d:Document)-[:ATTACHED_TO]->(:Session)-[:PART_OF]->(p:Project {projectId: $PROJECT_ID})
                RETURN d.docId as document_id
                UNION
                MATCH (d:Document)-[:RELATED_TO]->(p:Project {projectId: $PROJECT_ID})
                RETURN d.docId as document_id
            """,
            "semantic_search_terms": ["vector search", "Qdrant", "embeddings", "similarity search"],
            "qdrant_filters": None  # Will be constructed dynamically based on Neo4j results
        },
        
        # New query 2: Find what Alice said about technology and who else was in those sessions
        {
            "query_description": "RELATIONSHIP + SEMANTIC: What did Alice say about technology across sessions, and who else was in those sessions?",
            "natural_language": "Find Alice's technical comments and who else participated in those discussions",
            "neo4j_query_part": """
                MATCH (u:User {userId: $USER_ID})-[:PARTICIPATED_IN]->(s:Session)
                RETURN s.sessionId as session_id
            """,
            "semantic_search_terms": ["technology", "tech stack", "database", "frontend", "backend"],
            "qdrant_filters": None  # Will be constructed dynamically based on Neo4j results
        }
    ]

    # Process each query
    for query_info in combined_queries:
        if not query_info:
            continue  # Skip if query not found
            
        print(f"\nExecuting Query: {query_info['query_description']}")
        print(f"  NL: {query_info['natural_language']}")

        # Step 1: Query Neo4j for context
        neo4j_cypher = query_info.get('neo4j_query_part')
        neo4j_results = []
        params = {}
        
        # Setup parameters based on query
        if "F0 Canvas project documents" in query_info['query_description']:
            params["PROJECT_ID"] = PROJECT_F0_CANVAS_ID
            filter_field = "doc_id"
            print(f"  Neo4j Step: Finding documents for project {PROJECT_F0_CANVAS_ID}")
        elif "Alice" in query_info['query_description']:
            params["USER_ID"] = USER_ALICE_ID
            filter_field = "session_id"
            print(f"  Neo4j Step: Finding sessions where Alice (USER_ID: {USER_ALICE_ID}) participated")
        else:
            # Original query with participants
            params["SESSION_P1_KICKOFF_ID"] = SESSION_P1_KICKOFF_ID
            filter_field = "user_id"
            print(f"  Neo4j Step: Finding participants for session {SESSION_P1_KICKOFF_ID}")
        
        # Execute Neo4j query
        if neo4j_cypher:
            print(f"    Cypher: {neo4j_cypher}")
            with neo4j_driver.session(database="neo4j") as session:
                results = session.execute_read(run_read_query, neo4j_cypher, **params)
                
                # Extract the relevant IDs based on the query type
                if "F0 Canvas project documents" in query_info['query_description']:
                    neo4j_results = [r['document_id'] for r in results if 'document_id' in r]
                    print(f"    Neo4j Result: Found documents = {neo4j_results}")
                elif "Alice" in query_info['query_description']:
                    neo4j_results = [r['session_id'] for r in results if 'session_id' in r]
                    print(f"    Neo4j Result: Found sessions = {neo4j_results}")
                else:
                    # Original query
                    neo4j_results = [r['participant_id'] for r in results if 'participant_id' in r]
                    print(f"    Neo4j Result: Found participants = {neo4j_results}")
        else:
            print("  Skipping Neo4j step as 'neo4j_query_part' is not defined for this query.")

        # Step 2: Construct Qdrant Filter using Neo4j results
        final_qdrant_filter_list = []
        
        # For the original query about kickoff session
        if "kickoff" in query_info['query_description'].lower():
            target_session_id = SESSION_P1_KICKOFF_ID
            if target_session_id:
                final_qdrant_filter_list.append(
                    models.FieldCondition(key="session_id", match=models.MatchValue(value=target_session_id))
                )
                
            # Add participant filter if participants were found
            if neo4j_results:
                final_qdrant_filter_list.append(
                    models.FieldCondition(key="user_id", match=models.MatchAny(any=neo4j_results))
                )
        # For the document query    
        elif "F0 Canvas project documents" in query_info['query_description']:
            # Add document ID filter if documents were found
            if neo4j_results:
                final_qdrant_filter_list.append(
                    models.FieldCondition(key="doc_id", match=models.MatchAny(any=neo4j_results))
                )
            else:
                print("    Warning: No documents found. Falling back to project-based search.")
                final_qdrant_filter_list.append(
                    models.FieldCondition(key="project_id", match=models.MatchValue(value=PROJECT_F0_CANVAS_ID))
                )
        # For Alice's tech comments query
        elif "Alice" in query_info['query_description']:
            # Filter by Alice's user ID
            final_qdrant_filter_list.append(
                models.FieldCondition(key="user_id", match=models.MatchValue(value=USER_ALICE_ID))
            )
            
            # Add session filter if sessions were found
            if neo4j_results:
                final_qdrant_filter_list.append(
                    models.FieldCondition(key="session_id", match=models.MatchAny(any=neo4j_results))
                )
                
        # Combine filters using 'must'
        qdrant_filter = models.Filter(must=final_qdrant_filter_list) if final_qdrant_filter_list else None
        print(f"  Qdrant Step: Searching for semantic terms with filter:")
        print(f"    Filter: {qdrant_filter}")

        # Step 3: Perform Qdrant Semantic Search with Filter
        search_text = query_info['natural_language'] # Or use semantic_search_terms
        
        # Generate embedding for the query
        response = openai_client.embeddings.create(
            input=[search_text],
            model=EMBEDDING_MODEL
        )
        query_vector = response.data[0].embedding

        search_result = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=5
        )

        # Step 4: Display Results
        print("  Combined Results (Qdrant Hits Filtered by Neo4j Context):")
        if not search_result:
            print("    No relevant content found matching the criteria.")
        for hit in search_result:
            payload = hit.payload
            text = payload.get('text_content', '[Text not in payload]')
            print(f"    - Score: {hit.score:.4f} | Text: {text[:500]}...")
            print(f"      Context: User={payload.get('user_id')}, Session={payload.get('session_id')}")
            
        # Step 5: For Alice's tech comments query, find other participants in those sessions
        if "Alice" in query_info['query_description'] and search_result:
            found_sessions = set()
            for hit in search_result:
                session_id = hit.payload.get('session_id')
                if session_id:
                    found_sessions.add(session_id)
                    
            if found_sessions:
                print("\n  Finding other participants in these sessions:")
                for session_id in found_sessions:
                    other_participants_cypher = """
                        MATCH (s:Session {sessionId: $session_id})<-[:PARTICIPATED_IN]-(u:User)
                        WHERE u.userId <> $alice_id
                        RETURN u.userId as user_id
                    """
                    with neo4j_driver.session(database="neo4j") as session:
                        others = session.execute_read(
                            run_read_query, 
                            other_participants_cypher, 
                            session_id=session_id, 
                            alice_id=USER_ALICE_ID
                        )
                        other_ids = [r['user_id'] for r in others if 'user_id' in r]
                        print(f"    Session {session_id}: Other participants = {other_ids}")


# --- Main Execution ---
if __name__ == "__main__":
    ingest_data_combined()
    run_combined_queries()
    print("\nClosing Neo4j driver.")
    neo4j_driver.close()
    print("Qdrant + Neo4j Combined Demo Complete.")