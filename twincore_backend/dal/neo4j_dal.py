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
            # Use session_id (snake_case) as per our schema
            query = """
            MATCH (u:User)-[:PARTICIPATED_IN]->(s:Session {session_id: $session_id})
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
            
            # Use project_id (snake_case) as per our schema
            sessions_query = """
            MATCH (s:Session)-[:PART_OF]->(p:Project {project_id: $project_id})
            RETURN s
            """
            
            # Use project_id (snake_case) as per our schema
            documents_query = """
            MATCH (d:Document)-[:PART_OF]->(p:Project {project_id: $project_id})
            RETURN d
            """
            
            # Use project_id (snake_case) as per our schema
            users_query = """
            MATCH (u:User)-[:PARTICIPATED_IN]->(s:Session)-[:PART_OF]->(p:Project {project_id: $project_id})
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
            
    async def get_related_content(
        self,
        chunk_id: str,
        relationship_types: Optional[List[str]] = None,
        limit: int = 10,
        include_private: bool = False,
        max_depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Get content related to a specific chunk through graph relationships.
        
        This method traverses the graph to find content related to the specified
        chunk through various relationships, up to the specified depth.
        
        Args:
            chunk_id: The ID of the content chunk to find related content for
            relationship_types: Optional list of relationship types to traverse
            limit: Maximum number of results to return
            include_private: Whether to include private content
            max_depth: Maximum relationship traversal depth
            
        Returns:
            List of related content with relationship information
        """
        try:
            driver = self.driver
            
            # Build relationship filter based on provided types or use all relationships
            if relationship_types and len(relationship_types) > 0:
                # Join relationship types with the OR operator and place the variable length pattern inside the brackets
                rel_types = "|".join([f":{rel_type}" for rel_type in relationship_types])
                rel_filter = f"[{rel_types}*1..{max_depth}]"  # Asterisk INSIDE the brackets
            else:
                # For any relationship type, still keep the asterisk inside the brackets
                rel_filter = f"[*1..{max_depth}]"  # Asterisk INSIDE the brackets
            
            # Build privacy filter
            privacy_filter = ""
            if not include_private:
                privacy_filter = "WHERE NOT c2.is_private"
            
            # Build the Cypher query for variable depth traversal
            # This finds content nodes connected to our starting node through relationships
            query = f"""
            MATCH (c1:Content {{chunk_id: $chunk_id}})
            MATCH (c1)-{rel_filter}-(c2:Content)
            {privacy_filter}
            RETURN c2, 
                   [(c2)-[r]->(n) | {{type: type(r), target_id: n.chunk_id, target_type: labels(n)[0]}}] as outgoing_rels,
                   [(n)-[r]->(c2) | {{type: type(r), source_id: n.chunk_id, source_type: labels(n)[0]}}] as incoming_rels
            LIMIT $limit
            """
            
            related_content = []
            
            async with driver.session() as session:
                result = await session.run(
                    query, 
                    {
                        "chunk_id": chunk_id,
                        "limit": limit
                    }
                )
                
                async for record in result:
                    content_node = record["c2"]
                    outgoing_rels = record["outgoing_rels"]
                    incoming_rels = record["incoming_rels"]
                    
                    content_data = dict(content_node.items())
                    content_data["outgoing_relationships"] = outgoing_rels
                    content_data["incoming_relationships"] = incoming_rels
                    
                    related_content.append(content_data)
            
            return related_content
                
        except (ServiceUnavailable, ClientError, DatabaseError) as e:
            logger.error(f"Neo4j error getting related content: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting related content: {str(e)}")
            raise
            
    async def get_content_by_topic(
        self,
        topic_name: str,
        limit: int = 10,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        include_private: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get content related to a specific topic using graph relationships.
        
        This method finds content that mentions or is related to the specified topic.
        
        Args:
            topic_name: The name of the topic to find related content for
            limit: Maximum number of results to return
            user_id: Optional filter by user ID
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            include_private: Whether to include private content
            
        Returns:
            List of content related to the specified topic
        """
        try:
            driver = self.driver
            
            # Build filter conditions
            filters = []
            params = {"topic_name": topic_name, "limit": limit}
            
            if not include_private:
                filters.append("NOT c.is_private")
                
            if user_id:
                filters.append("c.user_id = $user_id")
                params["user_id"] = user_id
                
            if project_id:
                filters.append("c.project_id = $project_id")
                params["project_id"] = project_id
                
            if session_id:
                filters.append("c.session_id = $session_id")
                params["session_id"] = session_id
            
            # Combine filters
            filter_clause = " AND ".join(filters)
            if filter_clause:
                filter_clause = f"WHERE {filter_clause}"
            
            # Build the Cypher query
            # This finds content nodes related to the topic node
            query = f"""
            MATCH (t:Topic {{name: $topic_name}})<-[:MENTIONS]-(c:Content)
            {filter_clause}
            RETURN c, t
            LIMIT $limit
            """
            
            topic_related_content = []
            
            async with driver.session() as session:
                result = await session.run(query, params)
                
                async for record in result:
                    content_node = record["c"]
                    topic_node = record["t"]
                    
                    content_data = dict(content_node.items())
                    content_data["topic"] = dict(topic_node.items())
                    
                    topic_related_content.append(content_data)
            
            return topic_related_content
                
        except (ServiceUnavailable, ClientError, DatabaseError) as e:
            logger.error(f"Neo4j error getting content by topic: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting content by topic: {str(e)}")
            raise

    async def close(self):
        """Close the Neo4j driver and release resources."""
        if self._driver:
            try:
                await self._driver.close()
                logger.info("Neo4j driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Neo4j driver: {e}") 