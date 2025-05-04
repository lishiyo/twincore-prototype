"""Neo4j Data Access Layer implementation.

This module provides the concrete implementation of the INeo4jDAL interface,
handling interactions with the Neo4j graph database using the asynchronous driver.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from neo4j import AsyncDriver, Record, Result
from neo4j.exceptions import ClientError, DatabaseError, ServiceUnavailable

# Removed core.db_clients import as driver is now injected
from dal.interfaces import INeo4jDAL

logger = logging.getLogger(__name__)


class Neo4jDAL(INeo4jDAL):
    """Neo4j Data Access Layer implementation (Async).
    
    This class handles all interactions with the Neo4j graph database using
    an injected asynchronous driver.
    """

    def __init__(self, driver: AsyncDriver):
        """Initialize the Neo4j DAL with an existing async driver.
        
        Args:
            driver: An initialized async Neo4j driver instance.
        """
        if driver is None:
            raise ValueError("AsyncDriver must be provided to Neo4jDAL")
        self._driver = driver

    @property
    def driver(self) -> AsyncDriver:
        """Get the injected async Neo4j driver instance.
        
        Returns:
            AsyncDriver: The initialized async Neo4j driver passed during construction.
        """
        # Driver is guaranteed to be initialized by __init__
        return self._driver

    async def delete_all_data(self) -> Dict[str, Any]:
        """Delete all nodes and relationships from the database (async).
        
        This is a destructive operation that removes all nodes and relationships.
        Use with caution - generally only for testing, development, or resetting.
        
        Returns:
            Dict: Information about what was deleted
            
        Raises:
            ClientError, DatabaseError, ServiceUnavailable: If Neo4j errors occur
            Exception: For any other unexpected errors
        """
        try:
            driver = self.driver
            
            # Cypher query to get counts before deletion
            count_query = """
            MATCH (n)
            RETURN count(n) as nodeCount
            """
            
            # Cypher query to get relationship count before deletion
            rel_count_query = """
            MATCH ()-[r]->()
            RETURN count(r) as relationshipCount
            """
            
            # Cypher query to delete all relationships first, then all nodes
            delete_query = """
            MATCH (n)
            DETACH DELETE n
            """
            
            # Run the queries
            async with driver.session() as session:
                # Get current node count
                count_result = await session.run(count_query)
                node_count_record = await count_result.single()
                node_count = node_count_record["nodeCount"] if node_count_record else 0
                
                # Get current relationship count
                rel_count_result = await session.run(rel_count_query)
                rel_count_record = await rel_count_result.single()
                rel_count = rel_count_record["relationshipCount"] if rel_count_record else 0
                
                # Execute the deletion
                await session.run(delete_query)
                
                # Return information about the deletion
                return {
                    "nodes_deleted": node_count,
                    "relationships_deleted": rel_count
                }
                
        except (ServiceUnavailable, ClientError, DatabaseError) as e:
            logger.error(f"Neo4j error deleting all data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting all data: {str(e)}")
            raise

    async def create_node_if_not_exists(
        self,
        label: str,
        properties: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a node if it doesn't exist or return the existing one (async)."""
        try:
            # Use constraints or properties for the MERGE criteria
            merge_props = constraints if constraints is not None else properties
            
            # Ensure we have valid constraints to identify the node
            if not merge_props:
                raise ValueError("Must provide constraint properties to identify the node")

            # Set remaining properties if constraints were specified
            remaining_props = {}
            if constraints:
                remaining_props = {
                    k: v for k, v in properties.items() if k not in constraints
                }

            driver = self.driver # Use the property to get the driver
            
            async with driver.session() as session:
                # Build the Cypher query for MERGE
                query_parts = [
                    f"MERGE (n:{label} {{",
                    ", ".join(f"{k}: ${k}" for k in merge_props),
                    "})"
                ]
                
                # Add ON CREATE SET clause for additional properties if any
                # This prevents updating properties on existing nodes during MERGE
                if remaining_props:
                    query_parts.append("ON CREATE SET")
                    query_parts.append(
                        ", ".join(f"n.{k} = $prop_{k}" for k in remaining_props)
                    )
                
                # Return all properties of the node
                query_parts.append("RETURN n")
                cypher_query = " ".join(query_parts)
                
                # Prepare parameters - separate merge props from set props
                params = {**merge_props}
                for k, v in remaining_props.items():
                    params[f"prop_{k}"] = v
                
                # Execute the query
                result = await session.run(cypher_query, params)
                
                # Get the record
                record = await result.single()
                if record:
                    node = record["n"]
                    return dict(node.items())
                
            return {}  # This shouldn't happen with MERGE, but added for safety
                
        except (ServiceUnavailable, ClientError, DatabaseError) as e:
            logger.error(f"Neo4j error creating node: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating node: {str(e)}")
            raise

    async def create_relationship_if_not_exists(
        self,
        start_label: str,
        start_constraints: Dict[str, Any],
        end_label: str,
        end_constraints: Dict[str, Any],
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between nodes if it doesn't exist (async).
        
        Returns True if the relationship exists after the operation (either 
        newly created or previously existing). Does NOT update properties
        if the relationship already exists.
        """
        try:
            # Validate inputs
            if not start_constraints or not end_constraints:
                raise ValueError("Must provide constraints for both start and end nodes")
            
            driver = self.driver # Use the property to get the driver
            
            # Prepare parameters with distinct prefixes
            params = {}
            for k, v in start_constraints.items():
                params[f"start_{k}"] = v
            for k, v in end_constraints.items():
                params[f"end_{k}"] = v
            rel_params = {}
            if properties:
                for k, v in properties.items():
                    rel_params[f"rel_{k}"] = v
            
            # Combine all parameters for the run call
            all_params = {**params, **rel_params}
            
            # Build the Cypher query
            query_parts = [
                f"MATCH (a:{start_label}), (b:{end_label})",
                "WHERE"
            ]
            
            start_conditions = [f"a.{k} = $start_{k}" for k in start_constraints]
            end_conditions = [f"b.{k} = $end_{k}" for k in end_constraints]
            
            query_parts.append(" AND ".join(start_conditions))
            query_parts.append("AND")
            query_parts.append(" AND ".join(end_conditions))
            
            # MERGE the relationship pattern without properties initially
            query_parts.append(f"MERGE (a)-[r:{relationship_type}]->(b)")
            
            # Use ON CREATE SET for relationship properties
            if properties:
                query_parts.append("ON CREATE SET")
                query_parts.append(
                    ", ".join(f"r.{k} = $rel_{k}" for k in properties)
                )
            
            # Return the relationship to check if the operation affected anything
            query_parts.append("RETURN r") 
            
            cypher_query = " ".join(query_parts)
            
            async with driver.session() as session:
                # Execute the query
                result = await session.run(cypher_query, all_params)
                # Check if a relationship was returned (found or created)
                record = await result.single()
                return record is not None
                
        except (ServiceUnavailable, ClientError, DatabaseError) as e:
            logger.error(f"Neo4j error creating relationship: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating relationship: {str(e)}")
            raise

    async def get_session_participants(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """Get the participants of a session (async)."""
        try:
            driver = self.driver # Use the property to get the driver
            # Use sessionId as per dataSchema.md
            query = """
            MATCH (u:User)-[:PARTICIPATED_IN]->(s:Session {sessionId: $session_id})
            RETURN u
            """
            
            users = []
            async with driver.session() as session:
                result = await session.run(query, {"session_id": session_id})
                
                async for record in result:
                    user = record["u"]
                    users.append(dict(user.items()))
            
            return users
                
        except (ServiceUnavailable, ClientError, DatabaseError) as e:
            logger.error(f"Neo4j error getting session participants: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting session participants: {str(e)}")
            raise

    async def get_project_context(
        self, project_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get context information for a project (async)."""
        try:
            driver = self.driver # Use the property to get the driver
            
            # Use projectId as per dataSchema.md
            sessions_query = """
            MATCH (s:Session)-[:PART_OF]->(p:Project {projectId: $project_id})
            RETURN s
            """
            
            # Use projectId as per dataSchema.md
            documents_query = """
            MATCH (d:Document)-[:PART_OF]->(p:Project {projectId: $project_id})
            RETURN d
            """
            
            # Use projectId as per dataSchema.md
            users_query = """
            MATCH (u:User)-[:PARTICIPATED_IN]->(s:Session)-[:PART_OF]->(p:Project {projectId: $project_id})
            RETURN DISTINCT u
            """
            
            sessions = []
            documents = []
            users = []
            
            async with driver.session() as session:
                # Get sessions related to the project
                sessions_result = await session.run(sessions_query, {"project_id": project_id})
                
                async for record in sessions_result:
                    session_node = record["s"]
                    sessions.append(dict(session_node.items()))
                
                # Get documents related to the project
                documents_result = await session.run(documents_query, {"project_id": project_id})
                
                async for record in documents_result:
                    document_node = record["d"]
                    documents.append(dict(document_node.items()))
                
                # Get users involved in the project
                users_result = await session.run(users_query, {"project_id": project_id})
                
                async for record in users_result:
                    user_node = record["u"]
                    users.append(dict(user_node.items()))
            
            return {
                "sessions": sessions,
                "documents": documents,
                "users": users
            }
                
        except (ServiceUnavailable, ClientError, DatabaseError) as e:
            logger.error(f"Neo4j error getting project context: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting project context: {str(e)}")
            raise 

    async def close(self):
        """Close the Neo4j driver and release resources."""
        if self._driver:
            try:
                await self._driver.close()
                logger.info("Neo4j driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Neo4j driver: {e}") 