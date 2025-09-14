from typing import List, Dict, Optional
import logging
import openai
from openai import OpenAI
import time

class ContentProcessor:
    def __init__(self, openai_api_key: str):
        """
        Initialize ContentProcessor with OpenAI API key.

        Args:
            openai_api_key: API key for OpenAI services
        """
        self.api_key = openai_api_key
        self.client = OpenAI(api_key=openai_api_key)

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("ContentProcessor initialized with OpenAI API")

        # Configuration for API calls
        self.embedding_model = "text-embedding-3-small"  # Can upgrade to text-embedding-3-large
        self.summary_model = "gpt-3.5-turbo"  # Can upgrade to gpt-4
        self.max_retries = 3
        self.retry_delay = 1

    def generate_summary(self, text: str, max_length: int = 500) -> Optional[str]:
        """
        Generate a summary of the provided text using OpenAI API.

        Args:
            text: Text content to summarize
            max_length: Maximum length of the summary in characters

        Returns:
            Summary string or None if generation fails
        """
        if not text or not text.strip():
            self.logger.warning("Empty text provided for summary generation")
            return None

        # Truncate very long texts to avoid token limits
        max_input_chars = 12000  # Approximately 3000 tokens
        if len(text) > max_input_chars:
            text = text[:max_input_chars] + "..."
            self.logger.info(f"Truncated text to {max_input_chars} characters for summarization")

        prompt = f"""Please provide a concise summary of the following web page content.
        Focus on the main topics, key information, and purpose of the page.
        Keep the summary under {max_length // 4} words.

        Content:
        {text}

        Summary:"""

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.summary_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that creates concise, informative summaries of web page content."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_length // 4,  # Rough conversion from chars to tokens
                    temperature=0.3,  # Lower temperature for more focused summaries
                    n=1
                )

                summary = response.choices[0].message.content.strip()
                self.logger.info(f"Generated summary of {len(summary)} characters")
                return summary

            except openai.RateLimitError as e:
                self.logger.warning(f"Rate limit hit, attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                continue

            except openai.APIError as e:
                self.logger.error(f"OpenAI API error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                continue

            except Exception as e:
                self.logger.error(f"Unexpected error generating summary: {e}")
                return None

        self.logger.error(f"Failed to generate summary after {self.max_retries} attempts")
        return None

    def create_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text using OpenAI API.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector or None if generation fails
        """
        if not text or not text.strip():
            self.logger.warning("Empty text provided for embedding generation")
            return None

        # Truncate text if too long (8191 token limit for embedding models)
        max_chars = 30000  # Conservative estimate
        if len(text) > max_chars:
            text = text[:max_chars]
            self.logger.info(f"Truncated text to {max_chars} characters for embedding")

        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )

                embedding = response.data[0].embedding
                self.logger.info(f"Generated embedding vector of dimension {len(embedding)}")
                return embedding

            except openai.RateLimitError as e:
                self.logger.warning(f"Rate limit hit, attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                continue

            except openai.APIError as e:
                self.logger.error(f"OpenAI API error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                continue

            except Exception as e:
                self.logger.error(f"Unexpected error generating embedding: {e}")
                return None

        self.logger.error(f"Failed to generate embedding after {self.max_retries} attempts")
        return None

    def batch_embed(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batch for efficiency.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embedding vectors (or None for failed items)
        """
        if not texts:
            return []

        # Filter out empty texts but maintain indices
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                # Truncate if necessary
                if len(text) > 30000:
                    text = text[:30000]
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [None] * len(texts)

        # Process in batches (OpenAI allows batch embedding)
        batch_size = 20  # Conservative batch size
        embeddings = [None] * len(texts)

        for i in range(0, len(valid_texts), batch_size):
            batch = valid_texts[i:i + batch_size]
            batch_indices = valid_indices[i:i + batch_size]

            for attempt in range(self.max_retries):
                try:
                    response = self.client.embeddings.create(
                        model=self.embedding_model,
                        input=batch
                    )

                    for j, embedding_data in enumerate(response.data):
                        original_index = batch_indices[j]
                        embeddings[original_index] = embedding_data.embedding

                    self.logger.info(f"Generated batch of {len(batch)} embeddings")
                    break

                except openai.RateLimitError as e:
                    self.logger.warning(f"Rate limit hit in batch, attempt {attempt + 1}/{self.max_retries}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                    continue

                except openai.APIError as e:
                    self.logger.error(f"OpenAI API error in batch, attempt {attempt + 1}/{self.max_retries}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    continue

                except Exception as e:
                    self.logger.error(f"Unexpected error in batch embedding: {e}")
                    break

        return embeddings