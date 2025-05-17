# ingestion/processing/chunking.py
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from typing import List, Dict, Any, Optional
import os
import re

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
        # For YAML, JSON, and protobuf, use custom separators
        if language in ['yaml', 'yml']:
            logger.debug(f"Using YAML-specific splitter for: {language}")
            return RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.chunk_size,
                chunk_overlap=ingestion_settings.chunk_overlap,
                separators=["\n---\n", "\n\n", "\n", ": ", " ", ""]
            )
        elif language == 'json':
            logger.debug(f"Using JSON-specific splitter for: {language}")
            return RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.chunk_size,
                chunk_overlap=ingestion_settings.chunk_overlap,
                separators=["\n", ",", "}", "{", ": ", " ", ""]
            )
        elif language == 'protobuf':
            logger.debug(f"Using protobuf-specific splitter for: {language}")
            return RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.chunk_size,
                chunk_overlap=ingestion_settings.chunk_overlap,
                separators=["\n\n", "\n", "{", "}", ";", " ", ""]
            )
        else:
            # Fallback to a generic splitter if language not supported by LangChain's enum
            # or if you prefer a simpler approach initially
            logger.debug(f"Using generic recursive splitter for language: {language}")
            return RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.chunk_size,
                chunk_overlap=ingestion_settings.chunk_overlap
            )

def is_line_in_range(line_num: int, start_line: int, end_line: int) -> bool:
    """Check if a line number falls within a given range (inclusive)."""
    return start_line <= line_num <= end_line

def estimate_chunk_line_range(chunk_text: str, full_text: str, start_line: int) -> tuple:
    """
    Enhanced version to estimate the line range for a chunk based on its content and the full text.
    Returns a tuple of (start_line, end_line).
    """
    # Count newlines in the chunk
    chunk_lines = chunk_text.count('\n') + 1
    
    # Find the chunk's exact position in the full text
    if chunk_text in full_text:
        pos = full_text.find(chunk_text)
        lines_before = full_text[:pos].count('\n')
        chunk_start_line = start_line + lines_before
        chunk_end_line = chunk_start_line + chunk_lines - 1
        return (chunk_start_line, chunk_end_line)
    
    # If exact match fails, try more sophisticated matching
    chunk_lines_list = chunk_text.split('\n')
    if len(chunk_lines_list) > 3:
        # First try to match the first line exactly - this works well for function definitions
        first_line = chunk_lines_list[0].strip()
        if first_line in full_text:
            # Find all occurrences of the first line
            all_positions = [m.start() for m in re.finditer(re.escape(first_line), full_text)]
            
            # For each occurrence, try to match the surrounding content
            for pos in all_positions:
                lines_before = full_text[:pos].count('\n')
                potential_start_line = start_line + lines_before
                
                # Check if surrounding content matches
                context_start = max(0, pos - 100)
                context_end = min(len(full_text), pos + len(chunk_text) + 100)
                context = full_text[context_start:context_end]
                
                # If the chunk roughly matches this context area
                if len(set(chunk_text.split()) & set(context.split())) / len(set(chunk_text.split())) > 0.8:
                    return (potential_start_line, potential_start_line + chunk_lines - 1)
        
        # Use first 3 and last 3 lines as a fallback
        start_pattern = '\n'.join(chunk_lines_list[:3])
        end_pattern = '\n'.join(chunk_lines_list[-3:])
        
        if start_pattern in full_text and end_pattern in full_text:
            start_pos = full_text.find(start_pattern)
            end_pos = full_text.find(end_pattern) + len(end_pattern)
            
            lines_before_start = full_text[:start_pos].count('\n')
            lines_before_end = full_text[:end_pos].count('\n')
            
            return (start_line + lines_before_start, start_line + lines_before_end)
    
    # Final fallback: use approximate line count
    return (start_line, start_line + chunk_lines - 1)

def chunk_code(parsed_data, language='python'):
    """
    Process parsed code and create code chunks.
    This function will handle mapping the chunks to their parent entities (classes/functions).
    
    Args:
        parsed_data: List of dictionaries containing parsed code information
        language: Programming language for the chunking splitter
        
    Returns:
        List of code chunks with parent entity information
    """
    logger = logging.getLogger(__name__)
    chunks = []
    
    for file_data in parsed_data:
        file_path = file_data.get('path', '')
        # Check if content is present in file_data
        content = file_data.get('content', '')
        
        # If content is not in file_data, read it from the file directly
        if not content:
            try:
                repo_root = os.path.join(ingestion_settings.repo_dir, 'repos')
                repo_name = ingestion_settings.extract_repo_name(ingestion_settings.ingest_repo_url)
                repo_folder = os.path.join(repo_root, repo_name)
                
                full_path = os.path.join(repo_folder, file_path)
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")
                logger.warning(f"Skipping chunking for {file_path} due to empty content or parse error")
                continue
        
        # Skip if content is empty or there's a parse error 
        # Note: We now explicitly log this is a parse error if that's the case
        if file_data.get('parse_error', False):
            logger.warning(f"Skipping chunking for {file_path} due to parse error")
            continue
            
        if not content.strip():
            logger.warning(f"Skipping chunking for {file_path} due to empty content")
            continue
        
        lang = file_data.get('language', language)
        
        # Get all functions and classes with their line ranges from the file
        parent_entities = []
        
        # Add functions
        for func in file_data.get('functions', []):
            parent_entities.append({
                'type': 'Function',
                'id': func['unique_id'],
                'name': func['name'],
                'start_line': func['start_line'],
                'end_line': func['end_line'],
                'nesting_level': 0  # Initialize nesting_level to 0
            })
        
        # Add classes
        for cls in file_data.get('classes', []):
            parent_entities.append({
                'type': 'Class',
                'id': cls['unique_id'],
                'name': cls['name'],
                'start_line': cls['start_line'],
                'end_line': cls['end_line'],
                'nesting_level': 0  # Initialize nesting_level to 0
            })
        
        # Sort entities by their line ranges to handle nested structures
        parent_entities.sort(key=lambda x: (x['start_line'], -x['end_line']))
        
        # Detect nested entities (like methods inside classes)
        # For each entity, determine its parent
        for i, entity in enumerate(parent_entities):
            entity['parent'] = None
            
            # Look for parent entities that contain this one
            for j, potential_parent in enumerate(parent_entities):
                if i != j and potential_parent['start_line'] <= entity['start_line'] and potential_parent['end_line'] >= entity['end_line']:
                    # This entity is nested inside potential_parent
                    # If we already have a parent, only update if this one is more specific
                    if entity['parent'] is None or (
                        potential_parent['end_line'] - potential_parent['start_line'] <
                        parent_entities[entity['parent']]['end_line'] - parent_entities[entity['parent']]['start_line']
                    ):
                        entity['parent'] = j
                        # Make sure parent has nesting_level defined
                        if 'nesting_level' not in potential_parent:
                            potential_parent['nesting_level'] = 0
                        entity['nesting_level'] = potential_parent['nesting_level'] + 1
        
        # Create file-specific splitter based on language
        splitter = get_code_splitter(lang)
        if not splitter:
            logger.warning(f"No splitter configured for language {lang}. Using default chunking.")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=ingestion_settings.chunk_size,
                chunk_overlap=ingestion_settings.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
        
        # Split the entire file content
        all_chunks = splitter.create_documents([content])
        
        # Assign line numbers to chunks if not already included
        chunks_with_lines = []
        for chunk in all_chunks:
            # Extract chunk text
            chunk_text = chunk.page_content
            
            # Calculate line numbers
            start_line, end_line = estimate_chunk_line_range(chunk_text, content, 1)
            
            # Store all relevant chunk info
            chunks_with_lines.append({
                'content': chunk_text,
                'start_line': start_line,
                'end_line': end_line
            })
        
        # Group chunks by likely parent entity
        function_chunks = []
        class_chunks = []
        file_chunks = []

        # First do a pre-scan to identify chunks that have clear function signatures
        # This helps with prioritizing function chunks even if line ranges are imperfect
        function_signature_patterns = [
            r'^\s*(public|private|protected)?\s+(static)?\s+\w+\s+\w+\s*\([^)]*\)\s*\{',  # Java method
            r'^\s*def\s+\w+\s*\([^)]*\)\s*:',  # Python function
            r'^\s*function\s+\w+\s*\([^)]*\)\s*\{',  # JavaScript function
            r'^\s*@\w+.*\s*\n\s*(public|private|protected)?\s+(static)?\s+\w+\s+\w+\s*\(',  # Annotated Java method
            r'^\s*\w+\s*=\s*function\s*\([^)]*\)\s*\{',  # JavaScript function expression
            r'^\s*\w+\s*:\s*function\s*\([^)]*\)\s*\{',  # JavaScript object method
            r'^\s*const\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{',  # JavaScript arrow function
            r'^\s*\([^)]*\)\s*=>\s*\{'  # JavaScript arrow function anonymous
        ]

        # Class pattern detection to improve class chunk assignment
        class_signature_patterns = [
            r'^\s*class\s+\w+(\s*\([^)]*\))?\s*:',  # Python class
            r'^\s*(public|private|protected)?\s+class\s+\w+(\s+extends\s+\w+)?(\s+implements\s+\w+(?:,\s*\w+)*)?\s*\{',  # Java class
            r'^\s*interface\s+\w+(\s+extends\s+\w+(?:,\s*\w+)*)?\s*\{',  # Java interface
            r'^\s*class\s+\w+(\s+extends\s+\w+)?(\s+implements\s+\w+(?:,\s*\w+)*)?\s*\{',  # JavaScript class
        ]

        # Improved chunk assignment with stronger pattern detection for language features
        for chunk_data in chunks_with_lines:
            content = chunk_data['content']
            first_line = content.split('\n')[0] if '\n' in content else content
            
            # Check if this chunk starts with a function signature
            is_function_signature = False
            for pattern in function_signature_patterns:
                if re.search(pattern, content, re.MULTILINE):
                    is_function_signature = True
                    break
            
            # Check if this chunk starts with a class signature
            is_class_signature = False
            for pattern in class_signature_patterns:
                if re.search(pattern, content, re.MULTILINE):
                    is_class_signature = True
                    break
            
            # Find all entities that contain this chunk
            chunk_start = chunk_data['start_line']
            chunk_end = chunk_data['end_line']
            containing_entities = []
            for idx, entity in enumerate(parent_entities):
                if entity['start_line'] <= chunk_start and entity['end_line'] >= chunk_end:
                    containing_entities.append((idx, entity))
            
            # Sort by nesting level (highest first) and entity type (prioritize functions)
            # Give extra weight to functions for chunks with function signatures
            # Give extra weight to classes for chunks with class signatures
            containing_entities.sort(key=lambda x: (
                x[1]['nesting_level'], 
                4 if x[1]['type'] == 'Function' and is_function_signature else
                3 if x[1]['type'] == 'Class' and is_class_signature else
                2 if x[1]['type'] == 'Function' else 
                1 if x[1]['type'] == 'Class' else 0
            ), reverse=True)
            
            if containing_entities:
                assigned_parent = containing_entities[0][1]
                if assigned_parent['type'] == 'Function':
                    function_chunks.append((chunk_data, assigned_parent))
                else:
                    class_chunks.append((chunk_data, assigned_parent))
            else:
                # Enhanced name matching for chunks without containing entities
                if is_function_signature:
                    # Try to extract function name from the first line
                    function_name = None
                    for pattern, extract_group in [
                        (r'^\s*(public|private|protected)?\s+(static)?\s+\w+\s+(\w+)\s*\(', 3),  # Java
                        (r'^\s*def\s+(\w+)\s*\(', 1),  # Python
                        (r'^\s*function\s+(\w+)\s*\(', 1),  # JavaScript
                        (r'^\s*@\w+.*\s*\n\s*(public|private|protected)?\s+(static)?\s+\w+\s+(\w+)\s*\(', 3),  # Annotated Java
                        (r'^\s*(\w+)\s*=\s*function\s*\(', 1),  # JS function expression
                        (r'^\s*(\w+)\s*:\s*function\s*\(', 1),  # JS object method
                        (r'^\s*const\s+(\w+)\s*=\s*\([^)]*\)\s*=>', 1)  # JS arrow function
                    ]:
                        match = re.search(pattern, content, re.MULTILINE)
                        if match:
                            function_name = match.group(extract_group)
                            break
                    
                    if function_name:
                        # Look for functions with matching name, allowing for more flexible line ranges
                        for idx, entity in enumerate(parent_entities):
                            if entity['type'] == 'Function' and entity['name'] == function_name:
                                # Don't be too strict about line ranges for named function matches
                                function_chunks.append((chunk_data, entity))
                                break
                        else:  # No matching function found
                            file_chunks.append(chunk_data)
                    else:
                        file_chunks.append(chunk_data)
                elif is_class_signature:
                    # Try to extract class name from the first line
                    class_name = None
                    for pattern, extract_group in [
                        (r'^\s*class\s+(\w+)', 1),  # Python class
                        (r'^\s*(public|private|protected)?\s+class\s+(\w+)', 2),  # Java class
                        (r'^\s*interface\s+(\w+)', 1),  # Java interface
                    ]:
                        match = re.search(pattern, content, re.MULTILINE)
                        if match:
                            class_name = match.group(extract_group)
                            break
                    
                    if class_name:
                        # Look for classes with matching name, allowing for more flexible line ranges
                        for idx, entity in enumerate(parent_entities):
                            if entity['type'] == 'Class' and entity['name'] == class_name:
                                # Don't be too strict about line ranges for named class matches
                                class_chunks.append((chunk_data, entity))
                                break
                        else:  # No matching class found
                            file_chunks.append(chunk_data)
                    else:
                        file_chunks.append(chunk_data)
                else:
                    # No signature match - check if chunk content relates to any entity by name
                    # This helps with class/function documentation chunks that don't contain the signature
                    for idx, entity in enumerate(parent_entities):
                        entity_name = entity['name']
                        # If chunk contains entity name and is close to its line range, associate them
                        if entity_name in content and abs(chunk_start - entity['start_line']) < 10:
                            if entity['type'] == 'Function':
                                function_chunks.append((chunk_data, entity))
                                break
                            elif entity['type'] == 'Class':
                                class_chunks.append((chunk_data, entity))
                                break
                    else:
                        file_chunks.append(chunk_data)

        # Process function chunks first (highest priority)
        for chunk_data, assigned_parent in function_chunks:
            parent_id = assigned_parent['id']
            parent_type = assigned_parent['type']
            parent_name = assigned_parent['name']
            chunk_id = f"{parent_id}_chunk_{len(chunks)}"
            
            # Create the final chunk object
            chunk = {
                'chunk_id': chunk_id,
                'content': chunk_data['content'],
                'start_line': chunk_data['start_line'],
                'end_line': chunk_data['end_line'],
                'parent_id': parent_id,
                'parent_type': parent_type,
                'parent_name': parent_name,
                'file_path': file_path
            }
            
            chunks.append(chunk)

        # Process class chunks next
        for chunk_data, assigned_parent in class_chunks:
            parent_id = assigned_parent['id']
            parent_type = assigned_parent['type']
            parent_name = assigned_parent['name']
            chunk_id = f"{parent_id}_chunk_{len(chunks)}"
            
            # Create the final chunk object
            chunk = {
                'chunk_id': chunk_id,
                'content': chunk_data['content'],
                'start_line': chunk_data['start_line'],
                'end_line': chunk_data['end_line'],
                'parent_id': parent_id,
                'parent_type': parent_type,
                'parent_name': parent_name,
                'file_path': file_path
            }
            
            chunks.append(chunk)

        # Process remaining file-level chunks
        for chunk_data in file_chunks:
            # For file-level chunks, use a prefix to clearly indicate it's at file level
            parent_id = f"file::{file_path}"
            parent_type = "File"
            parent_name = os.path.basename(file_path)
            chunk_id = f"{parent_id}_chunk_{len(chunks)}"
            
            # Create the final chunk object
            chunk = {
                'chunk_id': chunk_id,
                'content': chunk_data['content'],
                'start_line': chunk_data['start_line'],
                'end_line': chunk_data['end_line'],
                'parent_id': parent_id,
                'parent_type': parent_type,
                'parent_name': parent_name,
                'file_path': file_path
            }
            
            chunks.append(chunk)
    
    # Count chunks by parent type for reporting
    parent_type_counts = {}
    for chunk in chunks:
        parent_type = chunk.get('parent_type', 'Unknown')
        if parent_type in parent_type_counts:
            parent_type_counts[parent_type] += 1
        else:
            parent_type_counts[parent_type] = 1
    
    logger.info(f"Generated {len(chunks)} chunks in total.")
    for parent_type, count in parent_type_counts.items():
        logger.info(f"Generated {count} chunks for parent type: {parent_type}")
    
    return chunks

def chunk_code_file(file_path: str, content: str, parent_type: str = "File", language: str = "unknown") -> List[Dict[str, Any]]:
    """
    Process a single file and create code chunks.
    
    Args:
        file_path: Path to the file
        content: File content
        parent_type: Type of parent entity (default: File)
        language: Programming language of the file (default: unknown)
        
    Returns:
        List of code chunks
    """
    logger.info(f"Processing chunks for {file_path} ({language})")
    
    # Get code splitter for the language
    splitter = get_code_splitter(language)
    
    # Split the content into chunks
    all_chunks = splitter.create_documents([content])
    
    # Create the chunks
    chunks = []
    for i, chunk in enumerate(all_chunks):
        # Extract chunk text
        chunk_text = chunk.page_content
        
        # Calculate line numbers
        start_line, end_line = estimate_chunk_line_range(chunk_text, content, 1)
        
        # For file-level chunks, use a prefix to clearly indicate it's at file level
        parent_id = f"file::{file_path}"
        parent_name = os.path.basename(file_path)
        chunk_id = f"{parent_id}_chunk_{i}"
        
        # Create the final chunk object
        chunk_data = {
            'chunk_id': chunk_id,
            'content': chunk_text,
            'start_line': start_line,
            'end_line': end_line,
            'parent_id': parent_id,
            'parent_type': parent_type,
            'parent_name': parent_name,
            'file_path': file_path,
            'language': language
        }
        
        chunks.append(chunk_data)
    
    logger.info(f"Generated {len(chunks)} chunks in total.")
    logger.info(f"Generated {len(chunks)} chunks for parent type: {parent_type}")
    
    return chunks