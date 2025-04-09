# ingestion/processing/chunking.py
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from typing import List, Dict, Any, Optional
import os

from ingestion.config import ingestion_settings

logger = logging.getLogger(__name__)

# Mapping from simple language names to LangChain Language enum if needed
# Adjust based on the languages you actually parse and LangChain's support
LANGCHAIN_LANGUAGE_MAP = {
    "python": Language.PYTHON,
    "markdown": Language.MARKDOWN,
    "go": Language.GO,
    "java": Language.JAVA,
    "javascript": Language.JS, # Langchain uses JS
    "csharp": Language.CSHARP,
    "c": Language.C, # Example if needed later
    "cpp": Language.CPP, # Example if needed later
    # Add other mappings as LangChain supports them
    # Note: Check LangChain documentation for exact Language enum values
}

def get_code_splitter(language: str) -> RecursiveCharacterTextSplitter:
    """Gets a text splitter suitable for the given programming language."""
    lc_language = LANGCHAIN_LANGUAGE_MAP.get(language)
    if lc_language:
        logger.debug(f"Using language-specific splitter for: {language}")
        return RecursiveCharacterTextSplitter.from_language(
            language=lc_language,
            chunk_size=ingestion_settings.chunk_size,
            chunk_overlap=ingestion_settings.chunk_overlap
        )
    else:
        # Fallback to a generic splitter if language not supported by LangChain's enum
        # or if you prefer a simpler approach initially
        logger.debug(f"Using generic recursive splitter for language: {language}")
        return RecursiveCharacterTextSplitter(
            chunk_size=ingestion_settings.chunk_size,
            chunk_overlap=ingestion_settings.chunk_overlap
        )

def chunk_code(parsed_data: List[Dict[str, Any]], language: str) -> List[Dict[str, Any]]:
    """
    Chunks the code content within parsed functions and classes.
    Adds 'chunks' list to each function/class dict.
    Also chunks the remaining file content outside functions/classes.

    Returns a list of chunk dictionaries, each with metadata.
    """
    if not parsed_data:
        return []

    all_chunks = []
    splitter = get_code_splitter(language)

    for file_data in parsed_data:
        file_path = file_data['path']
        processed_content_indices = set() # Track characters belonging to functions/classes

        # 1. Chunk functions and classes
        items_to_chunk = file_data.get('functions', []) + file_data.get('classes', [])
        for item in items_to_chunk:
            item_content = item.get('content', '')
            if not item_content: continue

             # --- FIX: Comment out or remove these lines causing the NameError ---
            # start_char = content.find(item_content) # Simplistic, assumes unique content blocks
            # end_char = start_char + len(item_content)
            # if start_char != -1:
            #      processed_content_indices.update(range(start_char, end_char))
            # --- End Fix --- # --- FIX: Comment out or remove these lines causing the NameError ---
            # start_char = content.find(item_content) # Simplistic, assumes unique content blocks
            # end_char = start_char + len(item_content)
            # if start_char != -1:
            #      processed_content_indices.update(range(start_char, end_char))
            # --- End Fix ---

            chunks = splitter.split_text(item_content)
            item_type = 'Function' if 'unique_id' in item and '::' in item['unique_id'] and item['unique_id'].split('::')[1] != item['name'] else 'Class' if 'unique_id' in item else 'Unknown'


            for i, chunk_text in enumerate(chunks):
                 # Create a unique chunk ID
                chunk_id = f"{item['unique_id']}_chunk_{i}"
                chunk_metadata = {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "path": file_path,
                    "language": language,
                    "parent_type": item_type, # Function or Class
                    "parent_name": item.get('name'),
                    "parent_id": item.get('unique_id'),
                    "start_line": item.get('start_line'), # Approximate line for the chunk
                    "chunk_index": i,
                }
                all_chunks.append(chunk_metadata)


        # 2. Chunk remaining file content (outside functions/classes)
        # This part is tricky. A simple approach: chunk the whole file and filter later,
        # or try to subtract function/class content. Let's chunk the whole file content
        # and add metadata indicating it's 'file-level'.
        try:
            with open(os.path.join(ingestion_settings.clone_dir, file_path), 'r', encoding='utf-8', errors='replace') as f:
                 full_content = f.read()

            file_level_chunks = splitter.split_text(full_content)
            file_node_id = f"file::{file_path}" # Unique ID for the file node

            for i, chunk_text in enumerate(file_level_chunks):
                 # Create a unique chunk ID
                 # Check if this chunk substantially overlaps with already processed function/class chunks (optional optimization)
                 # Simple approach: add all file chunks, relate them to the file node
                 chunk_id = f"{file_node_id}_chunk_{i}"
                 chunk_metadata = {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "path": file_path,
                    "language": language,
                    "parent_type": "File",
                    "parent_name": os.path.basename(file_path),
                    "parent_id": file_node_id,
                     # Line numbers are hard to get accurately for file-level chunks without more complex mapping
                    "start_line": None,
                    "chunk_index": i,
                }
                 all_chunks.append(chunk_metadata)


        except Exception as e:
            logger.error(f"Could not read file {file_path} for file-level chunking: {e}")


    logger.info(f"Generated {len(all_chunks)} chunks in total.")
    return all_chunks