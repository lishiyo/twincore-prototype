import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.embedding_service import (
    EmbeddingService, 
    ModelConfigurationError, 
    EmbeddingProcessError
)

# Sample embeddings for mocking responses
MOCK_EMBEDDING = [0.1, 0.2, 0.3, 0.4, 0.5]

# Create mock embedding data objects that match the new client response structure
class MockEmbeddingData:
    def __init__(self, embedding):
        self.embedding = embedding

class MockEmbeddingResponse:
    def __init__(self, data):
        self.data = data

# Single embedding mock response
MOCK_RESPONSE = MockEmbeddingResponse([MockEmbeddingData(MOCK_EMBEDDING)])

# Multiple embeddings for testing list input
MOCK_EMBEDDINGS = [
    [0.1, 0.2, 0.3, 0.4, 0.5],
    [0.6, 0.7, 0.8, 0.9, 1.0]
]
MOCK_MULTIPLE_RESPONSE = MockEmbeddingResponse([
    MockEmbeddingData(MOCK_EMBEDDINGS[0]),
    MockEmbeddingData(MOCK_EMBEDDINGS[1])
])


class TestEmbeddingService:
    """Unit tests for the EmbeddingService class."""

    @patch('services.embedding_service.settings.openai_api_key', None)
    def test_init_missing_api_key(self):
        """Test initialization fails when API key is missing."""
        with pytest.raises(ModelConfigurationError, match="API key is required"):
            EmbeddingService(api_key=None)

    @patch('services.embedding_service.AsyncOpenAI')
    def test_init_success(self, mock_async_openai):
        """Test successful initialization."""
        # Arrange & Act
        service = EmbeddingService(api_key="test_key")
        
        # Assert
        assert service.api_key == "test_key"
        assert service.model_name == "text-embedding-ada-002"
        mock_async_openai.assert_called_once_with(api_key="test_key")

    @patch('services.embedding_service.AsyncOpenAI')
    def test_init_custom_model(self, mock_async_openai):
        """Test initialization with custom model name."""
        # Arrange & Act
        service = EmbeddingService(api_key="test_key", model_name="custom-model")
        
        # Assert
        assert service.model_name == "custom-model"

    @pytest.mark.asyncio
    async def test_get_embedding_single_text(self):
        """Test getting embeddings for a single text."""
        # Arrange
        service = EmbeddingService(api_key="test_key")
        
        # Mock the client and embeddings.create method
        mock_embeddings = AsyncMock()
        mock_embeddings.create.return_value = MOCK_RESPONSE
        service.client = AsyncMock()
        service.client.embeddings = mock_embeddings
        
        # Act
        embedding = await service.get_embedding("Test text")
        
        # Assert
        service.client.embeddings.create.assert_called_once_with(
            model="text-embedding-ada-002",
            input=["Test text"]
        )
        assert embedding == MOCK_EMBEDDING

    @pytest.mark.asyncio
    async def test_get_embedding_multiple_texts(self):
        """Test getting embeddings for multiple texts."""
        # Arrange
        service = EmbeddingService(api_key="test_key")
        
        # Mock the client and embeddings.create method
        mock_embeddings = AsyncMock()
        mock_embeddings.create.return_value = MOCK_MULTIPLE_RESPONSE
        service.client = AsyncMock()
        service.client.embeddings = mock_embeddings
        
        # Act
        embeddings = await service.get_embedding(["Text 1", "Text 2"])
        
        # Assert
        service.client.embeddings.create.assert_called_once_with(
            model="text-embedding-ada-002",
            input=["Text 1", "Text 2"]
        )
        assert embeddings == MOCK_EMBEDDINGS

    @pytest.mark.asyncio
    async def test_get_embedding_empty_input(self):
        """Test error handling for empty input."""
        # Arrange
        service = EmbeddingService(api_key="test_key")
        mock_embeddings = AsyncMock()
        service.client = AsyncMock()
        service.client.embeddings = mock_embeddings
        
        # Act & Assert
        with pytest.raises(EmbeddingProcessError, match="Text cannot be empty"):
            await service.get_embedding("")
        
        # Verify no API call was made
        service.client.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_embedding_all_whitespace(self):
        """Test error handling for input that's all whitespace."""
        # Arrange
        service = EmbeddingService(api_key="test_key")
        mock_embeddings = AsyncMock()
        service.client = AsyncMock()
        service.client.embeddings = mock_embeddings
        
        # Act & Assert
        with pytest.raises(EmbeddingProcessError, match="All provided texts are empty"):
            await service.get_embedding("   ")
        
        # Verify no API call was made
        service.client.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_embedding_api_error(self):
        """Test error handling for API errors."""
        # Arrange
        service = EmbeddingService(api_key="test_key")
        
        # Mock the client and embeddings.create method to raise an exception
        mock_embeddings = AsyncMock()
        mock_embeddings.create.side_effect = Exception("API error")
        service.client = AsyncMock()
        service.client.embeddings = mock_embeddings
        
        # Act & Assert
        with pytest.raises(EmbeddingProcessError, match="Failed to generate embeddings"):
            await service.get_embedding("Test text") 