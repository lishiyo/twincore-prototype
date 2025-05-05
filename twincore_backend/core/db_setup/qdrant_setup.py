import logging
from qdrant_client import models, AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from core.db_clients import get_async_qdrant_client
from core.config import settings

logger = logging.getLogger(__name__)

# Define Qdrant distance model (Collection name and vector size come from settings)
QDRANT_DISTANCE = models.Distance.COSINE


async def setup_qdrant_collection():
    """
    Ensures the Qdrant collection specified in settings exists and has the correct configuration.
    """
    qdrant_client = get_async_qdrant_client()
    collection_name = settings.qdrant_collection_name
    vector_size = settings.embedding_dimension

    try:
        logger.info(f"Checking if Qdrant collection '{collection_name}' exists...")
        try:
            # Check if collection exists
            collection_info = await qdrant_client.get_collection(collection_name=collection_name)
            logger.info(f"Collection '{collection_name}' already exists.")

            # Ensure required payload indexes exist
            required_indexes = {
                "user_id": models.PayloadSchemaType.KEYWORD,
                "project_id": models.PayloadSchemaType.KEYWORD,
                "session_id": models.PayloadSchemaType.KEYWORD,
                "is_private": models.PayloadSchemaType.BOOL,
                "timestamp": models.PayloadSchemaType.FLOAT,  # Added for range queries
                "source_type": models.PayloadSchemaType.KEYWORD, # document_chunk, transcript_chunk, message
            }
            existing_indexes = collection_info.payload_schema or {}

            for field, field_type in required_indexes.items():
                if field not in existing_indexes:
                    logger.info(f"Payload index for field '{field}' not found. Creating...")
                    await qdrant_client.create_payload_index(
                        collection_name=collection_name,
                        field_name=field,
                        field_schema=field_type
                    )
                    logger.info(f"Successfully created payload index for '{field}'.")
                else:
                    logger.debug(f"Payload index for field '{field}' already exists.")

        except (UnexpectedResponse, ValueError) as e:
            # ValueError can be raised for 404 Not Found, UnexpectedResponse for others
            if isinstance(e, ValueError) or (isinstance(e, UnexpectedResponse) and e.status_code == 404):
                logger.info(f"Collection '{collection_name}' not found. Creating...")
                await qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size, distance=QDRANT_DISTANCE
                    ),
                    # Add other configurations like HNSW parameters if needed later
                )
                logger.info(f"Successfully created Qdrant collection '{collection_name}'.")

                # Create indexes after creating the collection
                logger.info(f"Creating payload indexes for new collection '{collection_name}'...")
                required_indexes = {
                    "user_id": models.PayloadSchemaType.KEYWORD,
                    "project_id": models.PayloadSchemaType.KEYWORD,
                    "session_id": models.PayloadSchemaType.KEYWORD,
                    "is_private": models.PayloadSchemaType.BOOL,
                    "timestamp": models.PayloadSchemaType.FLOAT,  # Added for range queries
                    "source_type": models.PayloadSchemaType.KEYWORD, # document_chunk, transcript_chunk, message
                }
                for field, field_type in required_indexes.items():
                    await qdrant_client.create_payload_index(
                        collection_name=collection_name,
                        field_name=field,
                        field_schema=field_type
                    )
                    logger.info(f"Successfully created payload index for '{field}'.")

            else:
                # Re-raise unexpected errors
                raise e

    except Exception as e:
        logger.error(f"Failed to setup Qdrant collection '{collection_name}': {e}", exc_info=True)
        raise
    finally:
        # Ensure client is closed if created within this function (might not be the case if using cached client)
        # However, get_async_qdrant_client uses LRU cache, so closing here might affect other parts.
        # Best practice is to manage client lifecycle outside this function (e.g., FastAPI lifespan).
        # await qdrant_client.close() # Avoid closing cached client here
        pass 