from typing import List, Optional

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)

class TextChunker:
    """
    Component for splitting text into manageable chunks for embedding and processing.
    Uses Langchain's text splitters for robust text chunking.
    """
    
    def __init__(
        self, 
        default_chunk_size: int = 1000,
        default_overlap: int = 200
    ):
        """
        Initialize the TextChunker.
        
        Args:
            default_chunk_size: Default size of each chunk in characters
            default_overlap: Default number of overlapping characters between consecutive chunks
        """
        self.default_chunk_size = default_chunk_size
        self.default_overlap = default_overlap
    
    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        respect_sentences: bool = False,
        respect_paragraphs: bool = True
    ) -> List[str]:
        """
        Split text into chunks of approximately specified size with optional overlap.
        
        Args:
            text: The text to be chunked
            chunk_size: Target size of each chunk in characters (overrides default)
            overlap: Number of overlapping characters between consecutive chunks (overrides default)
            respect_sentences: Try to avoid splitting in the middle of sentences
            respect_paragraphs: Try to avoid splitting in the middle of paragraphs
        
        Returns:
            List of text chunks
        """
        # Use provided values or defaults
        chunk_size = chunk_size or self.default_chunk_size
        overlap = overlap or self.default_overlap
        
        # Ensure overlap is valid (must be smaller than chunk_size)
        overlap = min(overlap, chunk_size // 2)
        
        # Empty text check
        if not text or not text.strip():
            return []
            
        # Text shorter than chunk size
        if len(text) <= chunk_size:
            return [text]
        
        # Define separators based on parameters
        separators = []
        
        # Add paragraph separators if needed
        if respect_paragraphs:
            separators.extend(["\n\n", "\n", " "])
        # Add sentence separators if needed
        elif respect_sentences:
            separators.extend([".", "!", "?", ";", ":", " "])
        else:
            # Default character splitting
            separators = [" "]
            
        # Use the appropriate splitter based on parameters
        if respect_paragraphs or respect_sentences:
            # RecursiveCharacterTextSplitter is better for respecting natural boundaries
            splitter = RecursiveCharacterTextSplitter(
                separators=separators,
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                keep_separator=True,
                is_separator_regex=False
            )
        else:
            # CharacterTextSplitter for simpler splitting
            splitter = CharacterTextSplitter(
                separator=" ",
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                keep_separator=True
            )
            
        # Split the text and return the chunks
        return splitter.split_text(text) 