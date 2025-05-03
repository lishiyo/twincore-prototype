import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.embedding_service import (
    EmbeddingService, 
    ModelConfigurationError, 
    EmbeddingProcessError
)

# Sample embeddings for mocking responses
MOCK_EMBEDDING = [0.1, 0.2, 0.3, 0.4, 0.5]
MOCK_RESPONSE = MagicMock()
MOCK_RESPONSE.data = [{"embedding": MOCK_EMBEDDING}]

# Multiple embeddings for testing list input
MOCK_EMBEDDINGS = [
    [0.1, 0.2, 0.3, 0.4, 0.5],
    [0.6, 0.7, 0.8, 0.9, 1.0]
]
MOCK_MULTIPLE_RESPONSE = MagicMock()
MOCK_MULTIPLE_RESPONSE.data = [
    {"embedding": MOCK_EMBEDDINGS[0]},
    {"embedding": MOCK_EMBEDDINGS[1]}
]


class TestEmbeddingService:
    """Unit tests for the EmbeddingService class."""

    @patch('services.embedding_service.settings.openai_api_key', None)
    def test_init_missing_api_key(self):
        """Test initialization fails when API key is missing."""
        with pytest.raises(ModelConfigurationError, match="API key is required"):
            EmbeddingService(api_key=None)

    @patch('services.embedding_service.openai')
    def test_init_success(self, mock_openai):
        """Test successful initialization."""
        # Arrange & Act
        service = EmbeddingService(api_key="test_key")
        
        # Assert
        assert service.api_key == "test_key"
        assert service.model_name == "text-embedding-ada-002"
        assert mock_openai.api_key == "test_key"

    @patch('services.embedding_service.openai')
    def test_init_custom_model(self, mock_openai):
        """Test initialization with custom model name."""
        # Arrange & Act
        service = EmbeddingService(api_key="test_key", model_name="custom-model")
        
        # Assert
        assert service.model_name == "custom-model"

    @patch('services.embedding_service.openai.Embedding.acreate')
    @pytest.mark.asyncio
    async def test_get_embedding_single_text(self, mock_acreate):
        """Test getting embeddings for a single text."""
        # Arrange
        mock_acreate.return_value = MOCK_RESPONSE
        # Convert to AsyncMock to make it awaitable
        mock_acreate.side_effect = AsyncMock(return_value=MOCK_RESPONSE)
        service = EmbeddingService(api_key="test_key")
        
        # Act
        embedding = await service.get_embedding("Test text")
        
        # Assert
        mock_acreate.assert_called_once_with(
            model="text-embedding-ada-002",
            input=["Test text"]
        )
        assert embedding == MOCK_EMBEDDING

    @patch('services.embedding_service.openai.Embedding.acreate')
    @pytest.mark.asyncio
    async def test_get_embedding_multiple_texts(self, mock_acreate):
        """Test getting embeddings for multiple texts."""
        # Arrange
        # Convert to AsyncMock to make it awaitable
        mock_acreate.side_effect = AsyncMock(return_value=MOCK_MULTIPLE_RESPONSE)
        service = EmbeddingService(api_key="test_key")
        
        # Act
        embeddings = await service.get_embedding(["Text 1", "Text 2"])
        
        # Assert
        mock_acreate.assert_called_once_with(
            model="text-embedding-ada-002",
            input=["Text 1", "Text 2"]
        )
        assert embeddings == MOCK_EMBEDDINGS

    @patch('services.embedding_service.openai.Embedding.acreate')
    @pytest.mark.asyncio
    async def test_get_embedding_empty_input(self, mock_acreate):
        """Test error handling for empty input."""
        # Arrange
        service = EmbeddingService(api_key="test_key")
        
        # Act & Assert
        with pytest.raises(EmbeddingProcessError, match="Text cannot be empty"):
            await service.get_embedding("")
        
        # Verify no API call was made
        mock_acreate.assert_not_called()

    @patch('services.embedding_service.openai.Embedding.acreate')
    @pytest.mark.asyncio
    async def test_get_embedding_all_whitespace(self, mock_acreate):
        """Test error handling for input that's all whitespace."""
        # Arrange
        service = EmbeddingService(api_key="test_key")
        
        # Act & Assert
        with pytest.raises(EmbeddingProcessError, match="All provided texts are empty"):
            await service.get_embedding("   ")
        
        # Verify no API call was made
        mock_acreate.assert_not_called()

    @patch('services.embedding_service.openai.Embedding.acreate')
    @pytest.mark.asyncio
    async def test_get_embedding_api_error(self, mock_acreate):
        """Test error handling for API errors."""
        # Arrange
        mock_acreate.side_effect = Exception("API error")
        service = EmbeddingService(api_key="test_key")
        
        # Act & Assert
        with pytest.raises(EmbeddingProcessError, match="Failed to generate embeddings"):
            await service.get_embedding("Test text") 