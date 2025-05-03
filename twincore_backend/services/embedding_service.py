import logging
from typing import List, Optional, Union
import openai
from pydantic import ValidationError

from core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingServiceError(Exception):
    """Base exception for embedding service errors."""
    pass

class ModelConfigurationError(EmbeddingServiceError):
    """Exception raised for model configuration errors."""
    pass

class EmbeddingProcessError(EmbeddingServiceError):
    """Exception raised for errors during the embedding process."""
    pass

class EmbeddingService:
    """Service for generating text embeddings using OpenAI models.
    
    This service abstracts the process of generating embeddings from text,
    providing a consistent interface regardless of the underlying model.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """Initialize the embedding service with OpenAI credentials.
        
        Args:
            api_key: Optional OpenAI API key. If None, reads from settings.
            model_name: Optional model name to use. If None, reads from settings.
        
        Raises:
            ModelConfigurationError: If the API key is missing or the model cannot be initialized.
        """
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or "text-embedding-ada-002"  # Default OpenAI embedding model
        
        if not self.api_key:
            raise ModelConfigurationError("OpenAI API key is required but not provided")
        
        try:
            # Set the API key for the OpenAI client
            openai.api_key = self.api_key
            logger.info(f"EmbeddingService initialized with model: {self.model_name}")
        except Exception as e:
            raise ModelConfigurationError(f"Failed to initialize OpenAI client: {str(e)}")
    
    async def get_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for the given text using OpenAI.
        
        Args:
            text: A string or list of strings to generate embeddings for.
                 If a single string is provided, a single embedding is returned.
                 If a list of strings is provided, a list of embeddings is returned.
        
        Returns:
            A list of floats representing the embedding, or a list of embeddings if
            input was a list of strings.
        
        Raises:
            EmbeddingProcessError: If embedding generation fails.
        """
        try:
            if not text:
                raise ValueError("Text cannot be empty")
            
            # Handle both single string and list of strings
            is_single = isinstance(text, str)
            texts = [text] if is_single else text
            
            # Filter out empty strings
            texts = [t for t in texts if t.strip()]
            if not texts:
                raise ValueError("All provided texts are empty after stripping whitespace")
            
            # Get embeddings from OpenAI
            response = await openai.Embedding.acreate(
                model=self.model_name,
                input=texts
            )
            
            # Extract embeddings from response
            embeddings = [data["embedding"] for data in response.data]
            
            # Return a single embedding if input was a single string
            return embeddings[0] if is_single else embeddings
        
        except ValidationError as e:
            raise EmbeddingProcessError(f"Input validation error: {str(e)}")
        except ValueError as e:
            raise EmbeddingProcessError(str(e))
        except Exception as e:
            raise EmbeddingProcessError(f"Failed to generate embeddings: {str(e)}") 