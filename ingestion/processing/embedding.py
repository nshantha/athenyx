# ingestion/processing/embedding.py
import logging
import asyncio
from openai import OpenAI, AsyncOpenAI # Use Async Client
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import settings
from ingestion.config import ingestion_settings

logger = logging.getLogger(__name__)

# Initialize Async OpenAI client
aclient = AsyncOpenAI(api_key=settings.openai_api_key)

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for a batch of texts using OpenAI API."""
    if not texts:
        return []
    try:
        logger.debug(f"Generating embeddings for batch of {len(texts)} texts...")
        response = await aclient.embeddings.create(
            input=texts,
            model=settings.openai_embedding_model
        )
        embeddings = [item.embedding for item in response.data]
        logger.debug(f"Successfully generated {len(embeddings)} embeddings.")
        return embeddings
    except Exception as e:
        logger.error(f"OpenAI API error during embedding generation: {e}", exc_info=True)
        # The retry decorator will handle retries
        raise # Re-raise exception to trigger retry

async def embed_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adds vector embeddings to each chunk dictionary using batch processing.
    """
    logger.info(f"Starting embedding generation for {len(chunks)} chunks...")
    chunks_with_embeddings = []
    batch_size = ingestion_settings.embedding_batch_size
    delay_between_batches_sec = 1.0

    tasks = []
    text_batches = []

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_texts = [chunk['text'] for chunk in batch_chunks]
        if batch_texts:
            text_batches.append(batch_texts)
            tasks.append(generate_embeddings_batch(batch_texts))
            logger.debug(f"Waiting {delay_between_batches_sec}s before launching next batch...")
            await asyncio.sleep(delay_between_batches_sec) # Introduce delay

    # Run all batch embedding tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and combine with original chunks
    current_chunk_index = 0
    for i, result in enumerate(results):
        batch_texts = text_batches[i] # Get corresponding texts for context if error occurs
        if isinstance(result, Exception):
            logger.error(f"Failed to generate embeddings for a batch (size {len(batch_texts)}): {result}. Skipping batch.")
            # Skip the chunks from this failed batch
            current_chunk_index += len(batch_texts)
            continue
        elif len(result) != len(batch_texts):
             logger.error(f"Mismatch in embedding results count for a batch (Expected {len(batch_texts)}, Got {len(result)}). Skipping batch.")
             current_chunk_index += len(batch_texts)
             continue


        embeddings = result
        for j, embedding in enumerate(embeddings):
            chunk_index = current_chunk_index + j
            if chunk_index < len(chunks):
                # Ensure embedding dimension matches config (optional check)
                if len(embedding) != settings.embedding_dimensions:
                     logger.warning(f"Embedding dimension mismatch for chunk {chunks[chunk_index]['chunk_id']} (Expected {settings.embedding_dimensions}, Got {len(embedding)}). Skipping chunk.")
                     continue

                chunks[chunk_index]['embedding'] = embedding
                chunks_with_embeddings.append(chunks[chunk_index])
            else:
                 logger.error("Index out of bounds when matching embeddings to chunks. Check batching logic.")


        current_chunk_index += len(batch_texts) # Move index forward by processed batch size


    successful_count = len(chunks_with_embeddings)
    failed_count = len(chunks) - successful_count
    logger.info(f"Embedding generation complete. Successfully embedded: {successful_count}, Failed/Skipped: {failed_count}")

    return chunks_with_embeddings