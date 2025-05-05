from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings that can be loaded from environment variables."""
    
    # API Settings
    api_debug: bool = Field(default=False, description="Enable debug mode")
    
    # Database Settings - Qdrant
    qdrant_host: str = Field(default="localhost", description="Qdrant server host")
    qdrant_port: int = Field(default=6333, description="Qdrant server port")
    qdrant_collection_name: str = Field(default="twin_memory", description="Qdrant collection name for storing embeddings")
    qdrant_prefer_grpc: bool = Field(default=False, description="Whether to prefer gRPC for Qdrant connection")
    qdrant_grpc_port: int = Field(default=6334, description="Qdrant gRPC port")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key (if required)")
    
    # Qdrant Test Settings
    qdrant_test_host: str = Field(default="localhost", description="Qdrant test server host")
    qdrant_test_port: int = Field(default=7333, description="Qdrant test server port")
    qdrant_test_grpc_port: int = Field(default=7334, description="Qdrant test gRPC port")
    qdrant_test_api_key: Optional[str] = Field(default=None, description="Qdrant test API key (if required)")
    
    # Database Settings - Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password", description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")
    
    # Neo4j Test Settings
    neo4j_test_uri: str = Field(default="bolt://localhost:8687", description="Neo4j test connection URI")
    neo4j_test_user: str = Field(default="neo4j", description="Neo4j test username")
    neo4j_test_password: str = Field(default="twincore_test", description="Neo4j test password")
    neo4j_test_database: str = Field(default="neo4j", description="Neo4j test database name")
    
    # Embedding Model Settings
    embedding_model_name: str = Field(
        default="text-embedding-3-small", 
        description="Name of the sentence transformer model for embeddings"
    )
    embedding_dimension: int = Field(default=1536, description="Dimension of the embedding vectors")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for embeddings (if using OpenAI)")
    
    # Model settings for configuring environment variables
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],  # Try parent directory first, then current directory
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Create a global settings instance
settings = Settings() 