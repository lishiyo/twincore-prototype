import pytest
from twincore_backend.ingestion.processors.text_chunker import TextChunker


class TestTextChunker:
    @pytest.fixture
    def chunker(self):
        """Create a TextChunker instance for testing."""
        return TextChunker(default_chunk_size=1000, default_overlap=200)
    
    def test_chunking_basic(self, chunker):
        """Test basic text chunking with default parameters."""
        text = "This is a sample text that should be split into chunks for processing by the embedding model."
        chunks = chunker.chunk_text(text, chunk_size=10, overlap=2)
        
        # Check that we have chunks
        assert len(chunks) > 0
        # Ensure the full text is roughly preserved (whitespace may change)
        joined = " ".join(chunks)
        assert "sample text" in joined
        assert "embedding model" in joined
    
    def test_chunking_with_overlap(self, chunker):
        """Test text chunking with overlap between chunks."""
        text = "This is a sample text for testing overlap in chunking."
        chunks = chunker.chunk_text(text, chunk_size=10, overlap=3)
        
        # Should have multiple chunks
        assert len(chunks) > 1
        # Check for content preservation
        full_text = " ".join(chunks)
        # Text should be preserved but might have extra spaces from joins
        assert "sample text" in full_text
        assert "testing overlap" in full_text
    
    def test_chunking_empty_text(self, chunker):
        """Test chunking with empty text."""
        chunks = chunker.chunk_text("", chunk_size=10, overlap=0)
        assert len(chunks) == 0
    
    def test_chunking_text_shorter_than_chunk_size(self, chunker):
        """Test with text shorter than chunk size."""
        text = "Short text"
        chunks = chunker.chunk_text(text, chunk_size=20, overlap=0)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunking_sentence_boundaries(self, chunker):
        """Test chunking respects sentence boundaries when possible."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = chunker.chunk_text(text, chunk_size=30, overlap=5, respect_sentences=True, respect_paragraphs=False)
        
        # Check that we have chunks
        assert len(chunks) > 0
        # Ensure full text is preserved
        full_text = " ".join(chunks)
        assert "sentence one" in full_text
        assert "sentence two" in full_text
        assert "sentence three" in full_text
    
    def test_chunking_paragraph_boundaries(self, chunker):
        """Test chunking respects paragraph boundaries when possible."""
        text = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."
        chunks = chunker.chunk_text(text, chunk_size=30, overlap=5, respect_paragraphs=True)
        
        # Check we have chunks
        assert len(chunks) > 0
        # Check content preservation
        full_text = "".join(chunks)
        assert "paragraph one" in full_text
        assert "paragraph two" in full_text
        assert "paragraph three" in full_text
    
    def test_default_parameters(self, chunker):
        """Test using default parameters from constructor."""
        paragraphs = []
        for i in range(20):  # 20 paragraphs should be well over the default chunk size
            paragraphs.append(f"Paragraph {i}: This is a realistic test document with varied content. "
                            f"It includes sentences of different lengths and structures. "
                            f"The goal is to create text that will be split into multiple chunks "
                            f"by Langchain's RecursiveCharacterTextSplitter using default parameters.")
        
        text = "\n\n".join(paragraphs)
        chunks = chunker.chunk_text(text)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Chunks should be around default_chunk_size in length (or less)
        assert all(len(chunk) <= chunker.default_chunk_size + 100 for chunk in chunks)
        
        # Verify content is preserved
        full_text = " ".join(chunks)
        assert "Paragraph 0:" in full_text
        assert "Paragraph 19:" in full_text
    
    def test_large_document_chunking(self, chunker):
        """Test chunking a larger document with multiple paragraphs and sentences."""
        # Create a larger text with paragraphs and sentences
        paragraphs = []
        for i in range(10):
            sentences = [f"This is sentence {j} in paragraph {i}." for j in range(5)]
            paragraphs.append(" ".join(sentences))
        
        large_text = "\n\n".join(paragraphs)
        
        # Test with paragraph respect - use appropriate overlap
        p_chunks = chunker.chunk_text(
            large_text, 
            chunk_size=200, 
            overlap=50, 
            respect_paragraphs=True
        )
        
        # Test with sentence respect - use appropriate overlap
        s_chunks = chunker.chunk_text(
            large_text, 
            chunk_size=200, 
            overlap=50, 
            respect_sentences=True,
            respect_paragraphs=False
        )
        
        # Basic assertions to ensure chunking happened
        assert len(p_chunks) > 1
        assert len(s_chunks) > 1
        
        # Both approaches should preserve the full text
        p_text = "".join(p_chunks)
        s_text = "".join(s_chunks)
        
        # Check for content preservation with both methods
        sample_content = "sentence 0 in paragraph 3"
        assert sample_content in p_text
        assert sample_content in s_text 