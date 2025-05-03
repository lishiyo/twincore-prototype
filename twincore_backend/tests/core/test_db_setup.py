import pytest
import pytest_asyncio
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from core.db_setup import setup_qdrant_collection, QDRANT_DISTANCE
from core.config import settings
from core.db_clients import get_async_qdrant_client  # Used import

# Use the standard Qdrant instance for tests since that's what's running
# Instead of using qdrant_test_* settings, we'll leave the standard settings alone
# Comment these out so we use the regular Qdrant instance on port 6333
# settings.qdrant_host = settings.qdrant_test_host
# settings.qdrant_port = settings.qdrant_test_port
# settings.qdrant_api_key = settings.qdrant_test_api_key
# settings.qdrant_grpc_port = settings.qdrant_test_grpc_port


@pytest_asyncio.fixture(scope="function")
async def test_qdrant_client():
    """Provides an AsyncQdrantClient connected to the test instance and handles cleanup."""
    # No need to clear cache manually, the fixture in conftest.py handles it
    collection_name_to_clean = settings.qdrant_collection_name # Use setting for cleanup
    # Use the function instead of creating a new client
    client = get_async_qdrant_client()

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
        # No need to clear the cache again, the fixture will handle it for the next test


@pytest.mark.asyncio
@pytest.mark.integration
async def test_setup_qdrant_collection_creates_collection(test_qdrant_client: AsyncQdrantClient):
    """Verify setup_qdrant_collection creates the collection with correct parameters."""
    # Arrange
    expected_collection_name = settings.qdrant_collection_name
    expected_vector_size = settings.embedding_dimension

    # Act
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

@pytest.mark.asyncio
@pytest.mark.integration
async def test_setup_qdrant_collection_is_idempotent(test_qdrant_client: AsyncQdrantClient):
    """Verify calling setup_qdrant_collection twice doesn't cause errors."""
    # Arrange: Call setup once
    expected_collection_name = settings.qdrant_collection_name
    await setup_qdrant_collection()
    print("\nIdempotency Test: First call to setup_qdrant_collection completed.")

    # Act: Call setup again
    try:
        await setup_qdrant_collection()
        print("\nIdempotency Test: Second call to setup_qdrant_collection completed.")
    except Exception as e:
        pytest.fail(f"Calling setup_qdrant_collection twice raised an exception: {e}")

    # Assert: Verify collection still exists and has correct parameters (optional, covered by first test)
    try:
        collection_info = await test_qdrant_client.get_collection(collection_name=expected_collection_name)
        assert collection_info is not None
        print(f"\nIdempotency Test: Collection '{expected_collection_name}' still exists after second call.")
    except Exception as e:
        pytest.fail(f"Collection '{expected_collection_name}' verification failed after second call: {e}") 