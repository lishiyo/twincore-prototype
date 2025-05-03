import pytest
import pytest_asyncio
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from neo4j import Driver, GraphDatabase

from core.db_setup.qdrant_setup import setup_qdrant_collection, QDRANT_DISTANCE
from core.db_setup.neo4j_setup import setup_neo4j_constraints
from core.config import settings
from core.db_clients import get_async_qdrant_client, get_neo4j_driver, clear_all_client_caches  # Used import

# Uncomment these to use test-specific Qdrant settings
# Use the test Qdrant instance on port 7333
settings.qdrant_host = settings.qdrant_test_host
settings.qdrant_port = settings.qdrant_test_port
settings.qdrant_grpc_port = settings.qdrant_test_grpc_port
if settings.qdrant_test_api_key:
    settings.qdrant_api_key = settings.qdrant_test_api_key


@pytest_asyncio.fixture(scope="function")
async def test_qdrant_client():
    """Provides an AsyncQdrantClient connected to the test instance and handles cleanup."""
    # Clear cache to ensure we get a fresh client with test settings
    clear_all_client_caches()
    
    collection_name_to_clean = settings.qdrant_collection_name # Use setting for cleanup
    
    # Create a client explicitly connected to the test instance
    client = AsyncQdrantClient(
        host=settings.qdrant_test_host,
        port=settings.qdrant_test_port,
        api_key=settings.qdrant_test_api_key,
        prefer_grpc=settings.qdrant_prefer_grpc,
        grpc_port=settings.qdrant_test_grpc_port,
        https=False,  # Explicitly use HTTP instead of HTTPS for local development
    )

    # Ensure the collection doesn't exist before the test
    try:
        await client.delete_collection(collection_name=collection_name_to_clean)
        print(f"\nPre-test cleanup: Deleted collection '{collection_name_to_clean}'")
    except (UnexpectedResponse, ValueError) as e:
         # Ignore if collection doesn't exist (ValueError or 404)
         if not (isinstance(e, ValueError) or (isinstance(e, UnexpectedResponse) and e.status_code == 404)):
             raise e
         print(f"\nPre-test: Collection '{collection_name_to_clean}' did not exist.")


    yield client # Provide the client to the test function

    # Post-test cleanup: Ensure the collection is deleted
    print(f"\nPost-test cleanup: Attempting to delete collection '{collection_name_to_clean}'")
    try:
        await client.delete_collection(collection_name=collection_name_to_clean)
        print(f"Post-test cleanup: Successfully deleted collection '{collection_name_to_clean}'")
    except (UnexpectedResponse, ValueError) as e:
        if not (isinstance(e, ValueError) or (isinstance(e, UnexpectedResponse) and e.status_code == 404)):
            print(f"Post-test cleanup: Error deleting collection: {e}") # Log error but don't fail test run
        else:
            print(f"Post-test cleanup: Collection '{collection_name_to_clean}' was already deleted or didn't exist.")
    finally:
        await client.close() # Close the client connection
        # Clear cache to reset for next test
        clear_all_client_caches()


@pytest_asyncio.fixture(scope="function")
async def test_neo4j_driver():
    """Provides a Neo4j driver connected to the test instance and handles cleanup."""
    # Clear cache to ensure we get a fresh instance
    clear_all_client_caches()
    
    # For tests, we need to directly create the driver instead of using get_neo4j_driver
    # This ensures we can use test-specific credentials
    try:
        # Use test-specific Neo4j settings
        neo4j_test_uri = settings.neo4j_test_uri
        neo4j_test_user = settings.neo4j_test_user
        neo4j_test_password = settings.neo4j_test_password
        
        # Print connection details for debugging
        print(f"\nConnecting to Neo4j test instance: {neo4j_test_uri}")
        
        # Create driver with test credentials
        driver = GraphDatabase.driver(
            neo4j_test_uri,
            auth=(neo4j_test_user, neo4j_test_password)
        )
        
        # Test connection with simple query
        with driver.session() as session:
            result = session.run("RETURN 1 as n")
            value = result.single()["n"]
            print(f"Successfully connected to Neo4j test instance. Test query result: {value}")
        
        yield driver  # Provide the driver to the test function
    except Exception as e:
        print(f"Error setting up Neo4j test driver: {e}")
        raise
    finally:
        # Close the driver when done
        if 'driver' in locals():
            driver.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_setup_qdrant_collection_creates_collection(test_qdrant_client: AsyncQdrantClient):
    """Verify setup_qdrant_collection creates the collection with correct parameters."""
    # Arrange
    expected_collection_name = settings.qdrant_collection_name
    expected_vector_size = settings.embedding_dimension

    # Act - Need to temporarily override the Qdrant client setup
    # Store original settings
    original_host = settings.qdrant_host
    original_port = settings.qdrant_port
    original_grpc_port = settings.qdrant_grpc_port
    original_api_key = settings.qdrant_api_key
    
    try:
        # Set to test settings so setup_qdrant_collection uses test instance
        settings.qdrant_host = settings.qdrant_test_host
        settings.qdrant_port = settings.qdrant_test_port
        settings.qdrant_grpc_port = settings.qdrant_test_grpc_port
        settings.qdrant_api_key = settings.qdrant_test_api_key
        
        # Clear cache to ensure new settings are used
        clear_all_client_caches()
        
        # Run the setup function that will now use test settings
        await setup_qdrant_collection()
        
        # Assert
        # Verify the collection exists using the test client directly
        try:
            collection_info = await test_qdrant_client.get_collection(collection_name=expected_collection_name)
            print(f"\nTest Assertion: Found collection '{expected_collection_name}'")
            
            # Debug: Print collection info structure
            print(f"Collection info structure: {dir(collection_info)}")
            print(f"Collection info: {collection_info}")
        except (UnexpectedResponse, ValueError) as e:
            pytest.fail(f"Collection '{expected_collection_name}' was not found after setup: {e}")

        # Verify parameters based on Qdrant client response structure
        # The actual attribute name may be different from vectors_config
        assert hasattr(collection_info, 'config'), "Collection should have a config attribute"
        
        # Check vector configuration in the correct location
        if hasattr(collection_info, 'config') and hasattr(collection_info.config, 'params'):
            # New structure
            assert collection_info.config.params.vectors.size == expected_vector_size, f"Expected vector size {expected_vector_size}"
            assert collection_info.config.params.vectors.distance == QDRANT_DISTANCE.value, f"Expected distance {QDRANT_DISTANCE.value}"
        elif hasattr(collection_info, 'config') and hasattr(collection_info.config, 'vectors'):
            # Alternative structure
            if isinstance(collection_info.config.vectors, dict):
                vector_name = next(iter(collection_info.config.vectors)) 
                vector_params = collection_info.config.vectors[vector_name]
                assert vector_params.size == expected_vector_size, f"Expected vector size {expected_vector_size}"
                assert vector_params.distance == QDRANT_DISTANCE.value, f"Expected distance {QDRANT_DISTANCE.value}"
            else:
                # Yet another possible structure
                assert collection_info.config.vectors.size == expected_vector_size, f"Expected vector size {expected_vector_size}"
                assert collection_info.config.vectors.distance == QDRANT_DISTANCE.value, f"Expected distance {QDRANT_DISTANCE.value}"
        else:
            # If structure can't be determined, print the structure for debugging
            pytest.fail(f"Couldn't find vector configuration in the collection info: {collection_info}")

        print(f"Test Assertion: Collection '{expected_collection_name}' has correct parameters.")
    finally:
        # Restore original settings
        settings.qdrant_host = original_host
        settings.qdrant_port = original_port
        settings.qdrant_grpc_port = original_grpc_port
        settings.qdrant_api_key = original_api_key
        
        # Clear the cache again to ensure original settings are used after test
        clear_all_client_caches()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_setup_qdrant_collection_is_idempotent(test_qdrant_client: AsyncQdrantClient):
    """Verify calling setup_qdrant_collection twice doesn't cause errors."""
    # Arrange - Store original settings
    original_host = settings.qdrant_host
    original_port = settings.qdrant_port
    original_grpc_port = settings.qdrant_grpc_port
    original_api_key = settings.qdrant_api_key
    
    try:
        # Set to test settings
        settings.qdrant_host = settings.qdrant_test_host
        settings.qdrant_port = settings.qdrant_test_port
        settings.qdrant_grpc_port = settings.qdrant_test_grpc_port
        settings.qdrant_api_key = settings.qdrant_test_api_key
        
        # Clear cache to ensure new settings are used
        clear_all_client_caches()
        
        # Call setup once
        expected_collection_name = settings.qdrant_collection_name
        await setup_qdrant_collection()
        print("\nIdempotency Test: First call to setup_qdrant_collection completed.")

        # Act: Call setup again
        try:
            await setup_qdrant_collection()
            print("\nIdempotency Test: Second call to setup_qdrant_collection completed.")
        except Exception as e:
            pytest.fail(f"Calling setup_qdrant_collection twice raised an exception: {e}")

        # Assert: Verify collection still exists and has correct parameters
        try:
            collection_info = await test_qdrant_client.get_collection(collection_name=expected_collection_name)
            assert collection_info is not None
            print(f"\nIdempotency Test: Collection '{expected_collection_name}' still exists after second call.")
        except Exception as e:
            pytest.fail(f"Collection '{expected_collection_name}' verification failed after second call: {e}")
    finally:
        # Restore original settings
        settings.qdrant_host = original_host
        settings.qdrant_port = original_port
        settings.qdrant_grpc_port = original_grpc_port
        settings.qdrant_api_key = original_api_key
        
        # Clear the cache again to ensure original settings are used after test
        clear_all_client_caches()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_setup_neo4j_constraints_creates_constraints(test_neo4j_driver: Driver):
    """Verify setup_neo4j_constraints creates all specified constraints."""
    # Arrange - List of expected constraints (node label and property)
    expected_constraints = [
        ("User", "user_id"),
        ("Session", "session_id"),
        ("Message", "message_id"),
        ("Chunk", "chunk_id"),
        ("Document", "document_id"),
        ("Topic", "name"),
        ("Organization", "org_id"),
        ("Team", "team_id"),
        ("Project", "project_id"),
        ("Preference", "preference_id"),
        ("Vote", "vote_id")
    ]

    # Act - Use the test driver directly instead of overriding settings
    await setup_neo4j_constraints(driver=test_neo4j_driver, database=settings.neo4j_test_database)
    print("\nSetup complete: Neo4j constraints should be created.")

    # Assert - Check that each constraint exists in Neo4j
    # We'll run a cypher query to get all constraints and verify our expected ones exist
    with test_neo4j_driver.session() as session:
        # Query to get all constraints
        result = session.run("SHOW CONSTRAINTS")
        constraints = list(result)
        print(f"\nFound {len(constraints)} constraints in Neo4j.")
        
        # Debug: Print first constraint to see structure
        if constraints:
            print(f"Sample constraint structure: {constraints[0].data()}")
        
        # Format will vary by Neo4j version, we need to extract label and property
        # This handles Neo4j 4.x and 5.x formats
        existing_constraints = []
        for constraint in constraints:
            data = constraint.data()
            if 'labelsOrTypes' in data and 'properties' in data:
                # Neo4j 5.x format
                label = data['labelsOrTypes'][0] if data['labelsOrTypes'] else None
                property = data['properties'][0] if data['properties'] else None
                existing_constraints.append((label, property))
            elif 'description' in data:
                # Neo4j 4.x format - parse the description string
                desc = data['description']
                # Example: "CONSTRAINT ON ( user:User ) ASSERT (user.user_id) IS UNIQUE"
                # Extract label and property from the description
                import re
                label_match = re.search(r'\( \w+:(\w+) \)', desc)
                property_match = re.search(r'\w+\.(\w+)', desc)
                if label_match and property_match:
                    label = label_match.group(1)
                    property = property_match.group(1)
                    existing_constraints.append((label, property))
        
        print(f"Parsed constraints: {existing_constraints}")
        
        # Check that all our expected constraints exist
        missing = []
        existing_prop_names = [property for _, property in existing_constraints]
        print(f"\nActual property names in database: {existing_prop_names}")
        
        for expected_label, expected_property in expected_constraints:
            if not any(label == expected_label and property == expected_property 
                    for label, property in existing_constraints):
                missing.append((expected_label, expected_property))
        
        assert not missing, f"Missing constraints: {missing}"
        print("All expected constraints were found in Neo4j.")


@pytest.mark.asyncio
@pytest.mark.integration  
async def test_setup_neo4j_constraints_is_idempotent(test_neo4j_driver: Driver):
    """Verify calling setup_neo4j_constraints twice doesn't cause errors."""
    # Arrange/Act - Call setup once with the test driver
    await setup_neo4j_constraints(driver=test_neo4j_driver, database=settings.neo4j_test_database)
    print("\nIdempotency Test: First call to setup_neo4j_constraints completed.")

    # Act - Call setup again
    try:
        await setup_neo4j_constraints(driver=test_neo4j_driver, database=settings.neo4j_test_database)
        print("\nIdempotency Test: Second call to setup_neo4j_constraints completed.")
    except Exception as e:
        pytest.fail(f"Calling setup_neo4j_constraints twice raised an exception: {e}")
    
    # Assert - No explicit verification needed beyond no exceptions
    print("\nIdempotency Test: Neo4j constraints can be applied multiple times without errors.") 