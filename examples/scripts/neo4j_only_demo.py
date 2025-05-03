# neo4j_only_demo.py

import os
from neo4j import GraphDatabase, basic_auth
import sys
from dotenv import load_dotenv

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import sample data
try:
    from data.sample_data import memory_chunks_data, example_queries, USER_ALICE_ID, USER_BOB_ID, SESSION_P1_KICKOFF_ID, PROJECT_F0_CANVAS_ID, PROJECT_TWIN_RND_ID
except ImportError:
    print("Error: Could not import from sample_data.py. Make sure it's in the same directory.")
    exit()

# --- Configuration ---
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password") # Will use env var if available

# --- Initialize Driver ---
print(f"Connecting to Neo4j at {NEO4J_URI}...")
try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=basic_auth(NEO4J_USERNAME, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("Neo4j connection successful.")
except Exception as e:
    print(f"Error connecting to Neo4j: {e}")
    print("Please ensure Neo4j is running and credentials are correct.")
    exit()

# --- Helper Functions for Cypher ---
def run_write_query(tx, query, **params):
    result = tx.run(query, **params)
    return result.consume() # Consume results for write queries

def run_read_query(tx, query, **params):
    result = tx.run(query, **params)
    return [record.data() for record in result] # Return list of dictionaries

# --- Ingestion Function ---
def ingest_data_neo4j():
    print("\n--- Starting Neo4j Ingestion ---")
    print("Clearing existing graph data (optional)...")
    with driver.session(database="neo4j") as session: # Use appropriate database name
        session.execute_write(run_write_query, "MATCH (n) DETACH DELETE n")
    print("Graph cleared.")

    # Create constraints for uniqueness (important for MERGE performance)
    print("Applying schema constraints...")
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.userId IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.orgId IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Team) REQUIRE t.teamId IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.projectId IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Session) REQUIRE s.sessionId IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.docId IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Message) REQUIRE m.messageId IS UNIQUE",
        # Add constraints for Vote, Preference, Topic if modeled explicitly
    ]
    with driver.session(database="neo4j") as session:
        for constraint in constraints:
            try:
                session.execute_write(run_write_query, constraint)
            except Exception as e:
                print(f"Constraint error (may already exist): {e}")
    print("Constraints applied.")

    print(f"Processing {len(memory_chunks_data)} chunks for graph relationships...")
    with driver.session(database="neo4j") as session:
        for i, chunk in enumerate(memory_chunks_data):
            meta = chunk['metadata']
            chunk_id = chunk.get('chunk_id') # Needed if creating Chunk nodes
            # Check if 'message_id' exists at the chunk level and not in metadata
            message_id = chunk.get('message_id')
            if message_id and not meta.get('message_id'):
                meta['message_id'] = message_id

            # Use execute_write for each chunk to handle potential node/relationship creation
            # This isn't the most efficient for bulk loading, but simpler for demo logic.
            # Real bulk loading might use UNWIND + MERGE with a list of chunks.
            summary = session.execute_write(create_graph_elements, meta, chunk['text'])
            if (i + 1) % 5 == 0: # Print progress
                 print(f"  Processed {i+1}/{len(memory_chunks_data)} chunks...")

    print("Neo4j ingestion complete.")

# --- Cypher Transaction Function for Ingestion ---
def create_graph_elements(tx, meta, text_content):
    # --- Merge Core Entities ---
    if meta.get('org_id'):
        tx.run("MERGE (o:Organization {orgId: $org_id})", org_id=meta['org_id'])
    if meta.get('team_id'):
        tx.run("MERGE (t:Team {teamId: $team_id})", team_id=meta['team_id'])
        if meta.get('org_id'):
             tx.run("""
                MATCH (t:Team {teamId: $team_id})
                MATCH (o:Organization {orgId: $org_id})
                MERGE (t)-[:BELONGS_TO]->(o)
             """, team_id=meta['team_id'], org_id=meta['org_id'])
    if meta.get('project_id'):
        tx.run("MERGE (p:Project {projectId: $project_id}) ON CREATE SET p.name = $name",
               project_id=meta['project_id'], name=meta.get('project_name', 'Unknown Project')) # Add name if available
        if meta.get('team_id'):
             tx.run("""
                MATCH (p:Project {projectId: $project_id})
                MATCH (t:Team {teamId: $team_id})
                MERGE (t)-[:WORKS_ON]->(p)
             """, project_id=meta['project_id'], team_id=meta['team_id'])

    if meta.get('session_id'):
        tx.run("MERGE (s:Session {sessionId: $session_id}) ON CREATE SET s.name = $name, s.timestamp = datetime($timestamp)",
               session_id=meta['session_id'], name=meta.get('session_name', 'Unknown Session'), timestamp=meta.get('timestamp'))
        if meta.get('project_id'):
            tx.run("""
                MATCH (s:Session {sessionId: $session_id})
                MATCH (p:Project {projectId: $project_id})
                MERGE (s)-[:PART_OF]->(p)
            """, session_id=meta['session_id'], project_id=meta['project_id'])

    # --- Merge User and Participation/Authorship ---
    if meta.get('user_id'):
        tx.run("MERGE (u:User {userId: $user_id}) ON CREATE SET u.name = $name",
               user_id=meta['user_id'], name=meta.get('user_name', f"User {meta['user_id'][:4]}")) # Add name if available
        if meta.get('team_id'):
             tx.run("""
                MATCH (u:User {userId: $user_id})
                MATCH (t:Team {teamId: $team_id})
                MERGE (u)-[:MEMBER_OF]->(t)
             """, user_id=meta['user_id'], team_id=meta['team_id'])
        if meta.get('session_id'):
            tx.run("""
                MATCH (u:User {userId: $user_id})
                MATCH (s:Session {sessionId: $session_id})
                MERGE (u)-[:PARTICIPATED_IN]->(s)
            """, user_id=meta['user_id'], session_id=meta['session_id'])

        # Link user based on source type
        source_type = meta.get('source_type')
        if source_type == 'message' and meta.get('message_id'):
             tx.run("""
                MERGE (m:Message {messageId: $message_id})
                    ON CREATE SET m.timestamp = datetime($timestamp)
                WITH m
                MATCH (u:User {userId: $user_id})
                MERGE (u)-[:AUTHORED]->(m)
                RETURN m
             """, message_id=meta['message_id'], timestamp=meta.get('timestamp'), user_id=meta['user_id'])
             if meta.get('session_id'):
                  tx.run("""
                     MATCH (m:Message {messageId: $message_id})
                     MATCH (s:Session {sessionId: $session_id})
                     MERGE (m)-[:POSTED_IN]->(s)
                  """, message_id=meta['message_id'], session_id=meta['session_id'])

        elif source_type in ['document_chunk', 'transcript_snippet'] and meta.get('doc_id'):
             tx.run("""
                MERGE (d:Document {docId: $doc_id})
                    ON CREATE SET d.name = $name, d.sourceType = $source_type
                WITH d
                MATCH (u:User {userId: $user_id})
                // Use different relationships based on source? PARTICIPATED_IN_DOC? CONTRIBUTED_TO?
                // For now, simple AUTHORSHIP for transcript snippets where user is known
                MERGE (u)-[:CONTRIBUTED_TO]->(d)
             """, doc_id=meta['doc_id'], name=meta.get('doc_name', 'Unknown Document'),
                  source_type=meta.get('source_type'), user_id=meta['user_id'])
             # Link document to session/project if context available
             if meta.get('session_id'):
                 tx.run("""
                    MATCH (d:Document {docId: $doc_id})
                    MATCH (s:Session {sessionId: $session_id})
                    MERGE (d)-[:ATTACHED_TO]->(s)
                 """, doc_id=meta['doc_id'], session_id=meta['session_id'])
             if meta.get('project_id') and not meta.get('session_id'): # Avoid duplicate links if session implies project
                 tx.run("""
                     MATCH (d:Document {docId: $doc_id})
                     MATCH (p:Project {projectId: $project_id})
                     MERGE (d)-[:RELATED_TO]->(p)
                 """, doc_id=meta['doc_id'], project_id=meta['project_id'])

    # --- Handle Document without specific user author (e.g., spec doc) ---
    elif meta.get('doc_id') and not meta.get('user_id'):
         tx.run("MERGE (d:Document {docId: $doc_id}) ON CREATE SET d.name = $name, d.sourceType = $source_type",
                doc_id=meta['doc_id'], name=meta.get('doc_name', 'Unknown Document'), source_type=meta.get('source_type'))
         if meta.get('session_id'):
             tx.run("""
                MATCH (d:Document {docId: $doc_id})
                MATCH (s:Session {sessionId: $session_id})
                MERGE (d)-[:ATTACHED_TO]->(s)
             """, doc_id=meta['doc_id'], session_id=meta['session_id'])
         if meta.get('project_id') and not meta.get('session_id'):
             tx.run("""
                 MATCH (d:Document {docId: $doc_id})
                 MATCH (p:Project {projectId: $project_id})
                 MERGE (d)-[:RELATED_TO]->(p)
             """, doc_id=meta['doc_id'], project_id=meta['project_id'])


# --- Retrieval Function ---
def run_neo4j_queries():
    print("\n--- Running Neo4j Retrieval Queries ---")

    queries_to_run = [
        {
            "description": "GRAPH: Who participated in the F0 Canvas Core kickoff session?",
            "query": """
                MATCH (s:Session {sessionId: $session_id})<-[:PARTICIPATED_IN]-(u:User)
                RETURN u.userId AS participant_id, u.name AS participant_name
            """,
            "params": {"session_id": SESSION_P1_KICKOFF_ID}
        },
        {
            "description": "GRAPH: What projects is Alice involved in (via sessions or teams)?",
             "query": """
                MATCH (u:User {userId: $user_id})-[:PARTICIPATED_IN]->(:Session)-[:PART_OF]->(p:Project)
                RETURN DISTINCT p.projectId AS project_id, p.name AS project_name
                UNION
                MATCH (u:User {userId: $user_id})-[:MEMBER_OF]->(:Team)-[:WORKS_ON]->(p:Project)
                RETURN DISTINCT p.projectId AS project_id, p.name AS project_name
            """,
            "params": {"user_id": USER_ALICE_ID}
        },
         {
            "description": "GRAPH: What messages were posted by Bob in the F0 Canvas project?",
            "query": """
                MATCH (u:User {userId: $user_id})-[:AUTHORED]->(m:Message)-[:POSTED_IN]->(:Session)-[:PART_OF]->(p:Project {projectId: $project_id})
                RETURN m.messageId AS message_id, m.timestamp AS timestamp // Add message text if stored
            """,
             "params": {"user_id": USER_BOB_ID, "project_id": PROJECT_F0_CANVAS_ID}
        },
        {
            "description": f"GRAPH: Find documents related to Project {PROJECT_F0_CANVAS_ID}",
            "query": """
                MATCH (p:Project {projectId: $project_id})<-[:PART_OF]-(:Session)<-[:ATTACHED_TO]-(d:Document)
                RETURN DISTINCT d.docId AS doc_id, d.name AS doc_name
                UNION
                MATCH (p:Project {projectId: $project_id})<-[:RELATED_TO]-(d:Document)
                RETURN DISTINCT d.docId AS doc_id, d.name AS doc_name
            """,
            "params": {"project_id": PROJECT_F0_CANVAS_ID}
        }
    ]

    with driver.session(database="neo4j") as session:
        for i, query_info in enumerate(queries_to_run):
            print(f"\nQuery {i+1}: {query_info['description']}")
            print(f"  Cypher: {query_info['query'].strip()}")
            print(f"  Params: {query_info['params']}")
            results = session.execute_read(run_read_query, query_info['query'], **query_info['params'])
            print("  Results:")
            if not results:
                print("    No results found.")
            for record in results:
                print(f"    - {record}")


# --- Main Execution ---
if __name__ == "__main__":
    ingest_data_neo4j()
    run_neo4j_queries()
    print("\nClosing Neo4j driver.")
    driver.close()
    print("Neo4j Only Demo Complete.")