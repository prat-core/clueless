import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from dotenv import load_dotenv
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_core.output_parsers import StrOutputParser
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGTool:
    """
    Complete RAG (Retrieval-Augmented Generation) tool using LangChain + Pinecone + OpenAI.
    Based on proven working implementation.
    """
    
    def __init__(self, openai_api_key: str, pinecone_api_key: str, 
                 index_name: str = "clueless-rag"):
        """
        Initialize RAG tool with required API keys using LangChain approach.
        
        Args:
            openai_api_key: OpenAI API key for embeddings and chat
            pinecone_api_key: Pinecone API key for vector storage
            index_name: Name of the Pinecone index
        """
        self.openai_api_key = openai_api_key
        self.pinecone_api_key = pinecone_api_key
        self.index_name = index_name
        
        try:
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=pinecone_api_key)
            
            # Initialize OpenAI embeddings using LangChain (more reliable)
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small", 
                openai_api_key=openai_api_key
            )
            
            # Initialize Pinecone vector store using LangChain
            self.vectorstore = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=self.embeddings
            )
            
            # Initialize OpenAI client for chat completions
            self.client = OpenAI(api_key=openai_api_key)
            
            # Initialize text splitter for document chunking
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            # System message for Claude-style responses
            self.system_message = {
                'role': 'system',
                'content': """You are a helpful AI assistant that provides clear, accurate, and contextual responses based on the provided context. 
                You should be concise but thorough, and always aim to be helpful and informative. 
                If the context doesn't contain relevant information, you can still provide a general response but mention that you don't have specific context."""
            }
            
            logger.info("RAG Tool initialized successfully with LangChain")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG Tool: {e}")
            raise
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Add a document to the RAG system using LangChain approach.
        
        Args:
            content: Text content of the document
            metadata: Document metadata (url, title, etc.)
            
        Returns:
            Document ID if successful, None if failed
        """
        try:
            # Generate unique document ID
            doc_id = self._generate_doc_id(content, metadata)
            
            # Split content into chunks
            chunks = self.text_splitter.create_documents([content])
            
            # Add metadata to each chunk
            for chunk in chunks:
                chunk.metadata.update(metadata)
                chunk.metadata.update({
                    'doc_id': doc_id,
                    'content_length': len(content),
                    'added_at': datetime.now().isoformat(),
                    'content_hash': hashlib.sha256(content.encode()).hexdigest()
                })
            
            # Add documents to vector store using LangChain
            self.vectorstore.add_documents(chunks)
            
            logger.info(f"Successfully added document: {doc_id} ({len(chunks)} chunks)")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return None
    
    def add_documents_batch(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> List[str]:
        """
        Add multiple documents in batches.
        
        Args:
            documents: List of dicts with 'content' and 'metadata' keys
            batch_size: Number of documents to process in each batch
            
        Returns:
            List of document IDs that were successfully added
        """
        successful_ids = []
        
        try:
            all_chunks = []
            
            for doc in documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                
                if not content:
                    continue
                
                doc_id = self._generate_doc_id(content, metadata)
                chunks = self.text_splitter.create_documents([content])
                
                # Add metadata to each chunk
                for chunk in chunks:
                    chunk.metadata.update(metadata)
                    chunk.metadata.update({
                        'doc_id': doc_id,
                        'content_length': len(content),
                        'added_at': datetime.now().isoformat(),
                        'content_hash': hashlib.sha256(content.encode()).hexdigest()
                    })
                
                all_chunks.extend(chunks)
                successful_ids.append(doc_id)
            
            # Add all chunks in batches
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                self.vectorstore.add_documents(batch)
                logger.info(f"Added batch {i//batch_size + 1}: {len(batch)} chunks")
            
            logger.info(f"Successfully added {len(successful_ids)} documents ({len(all_chunks)} total chunks)")
            return successful_ids
            
        except Exception as e:
            logger.error(f"Error adding documents batch: {e}")
            return successful_ids  # Return what was successful
    
    def _generate_doc_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        Generate a unique document ID based on content and metadata.
        
        Args:
            content: Document content
            metadata: Document metadata
            
        Returns:
            Unique document ID
        """
        # Create ID from URL if available, otherwise from content hash
        if 'url' in metadata:
            base_id = metadata['url']
        else:
            base_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Clean the ID to be compatible
        clean_id = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(base_id))
        return clean_id
    
    def search_documents(self, query: str, k: int = 6, 
                        filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using LangChain similarity search.
        
        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of relevant documents with content and metadata
        """
        try:
            # Use LangChain's similarity search
            if filter_dict:
                results = self.vectorstore.similarity_search(
                    query, k=k, filter=filter_dict
                )
            else:
                results = self.vectorstore.similarity_search(query, k=k)
            
            # Format results
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            logger.info(f"Found {len(formatted_results)} relevant documents for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def retrieve_context(self, query: str, max_context_length: int = 4000) -> str:
        """
        Retrieve relevant context for a query using LangChain approach.
        
        Args:
            query: Search query
            max_context_length: Maximum length of context to return
            
        Returns:
            Concatenated context from relevant documents
        """
        try:
            # Search for relevant documents
            results = self.search_documents(query, k=6)
            
            if not results:
                return ""
            
            # Build context from results
            context_parts = []
            current_length = 0
            
            for result in results:
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                
                if content:
                    # Add source information
                    source = metadata.get('url', metadata.get('title', 'Unknown source'))
                    context_part = f"[Source: {source}]\n{content}\n"
                    
                    # Check if adding this would exceed limit
                    if current_length + len(context_part) > max_context_length:
                        # Truncate to fit
                        remaining_space = max_context_length - current_length
                        if remaining_space > 100:  # Only add if meaningful space left
                            context_part = context_part[:remaining_space] + "..."
                            context_parts.append(context_part)
                        break
                    
                    context_parts.append(context_part)
                    current_length += len(context_part)
            
            return "\n---\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return ""
    
    def get_relevant_info(self, query: str, model: str = "gpt-4o") -> str:
        """
        Get AI-generated response based on relevant context (like your working code).
        
        Args:
            query: User's question
            model: OpenAI model to use for response generation
            
        Returns:
            AI-generated response based on context
        """
        try:
            # Get relevant context
            context = self.search_documents(query, k=6)
            
            if not context:
                return "No relevant information found. Please make sure the vector database is populated with data."
            
            # Format the prompt like your working code
            formatted_user_query = f"""
This is the User's Query:
{query}

This is the context retrieved:
{context}
"""
            
            # Create messages array
            messages = [
                self.system_message,
                {
                    'role': 'user',
                    'content': formatted_user_query
                }
            ]
            
            # Generate response using OpenAI
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error getting relevant info: {e}")
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
    
    def process_query(self, user_input: str, use_retrieval: bool = True) -> Dict[str, Any]:
        """
        Main method to process user queries with RAG pipeline (compatible with existing Flask app).
        
        Args:
            user_input: The user's input text
            use_retrieval: Whether to use retrieval for context (default: True)
            
        Returns:
            Dictionary containing the complete response with metadata
        """
        logger.info(f"📝 Processing user query: {user_input[:100]}...")
        
        try:
            if use_retrieval:
                # Get AI response with context
                response_text = self.get_relevant_info(user_input)
                context_used = len(self.search_documents(user_input, k=1))  # Quick check
            else:
                # Direct response without retrieval
                messages = [
                    self.system_message,
                    {
                        'role': 'user',
                        'content': user_input
                    }
                ]
                
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                )
                
                response_text = response.choices[0].message.content
                context_used = 0
            
            result = {
                'response': response_text,
                'status': 'success',
                'model': 'rag-tool-langchain',
                'context_used': context_used,
                'retrieval_used': use_retrieval,
                'timestamp': datetime.now().isoformat(),
                'user_query': user_input
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in process_query: {e}")
            return {
                'response': f'Sorry, I encountered an error while processing your request: {str(e)}',
                'status': 'error',
                'error': str(e),
                'user_query': user_input,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the RAG system.
        
        Returns:
            Dictionary with system statistics
        """
        try:
            # Get Pinecone index stats
            index = self.pc.Index(self.index_name)
            stats = index.describe_index_stats()
            
            return {
                'pinecone_index': self.index_name,
                'total_documents': stats.total_vector_count,
                'index_dimension': stats.dimension,
                'index_fullness': stats.index_fullness,
                'embedding_model': 'text-embedding-3-small',
                'chat_model': 'gpt-4o',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }


# Factory function to create RAG tool instance
def create_rag_tool() -> Optional[RAGTool]:
    """
    Create RAG tool instance using environment variables.
    
    Returns:
        RAGTool instance or None if configuration is missing
    """
    openai_api_key = os.getenv('OPENAI_API_KEY')
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    index_name = os.getenv('PINECONE_INDEX_NAME', 'clueless-rag')
    
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return None
    
    if not pinecone_api_key:
        logger.error("PINECONE_API_KEY not found in environment variables")
        return None
    
    try:
        return RAGTool(
            openai_api_key=openai_api_key,
            pinecone_api_key=pinecone_api_key,
            index_name=index_name
        )
    except Exception as e:
        logger.error(f"Failed to create RAG tool: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    # Create RAG tool
    rag_tool = create_rag_tool()
    
    if rag_tool:
        # Example: Add a document
        sample_doc = "This is a sample document about machine learning and AI."
        sample_metadata = {
            'title': 'Sample ML Document',
            'url': 'https://example.com/ml-doc',
            'domain': 'example.com',
            'type': 'article'
        }
        
        doc_id = rag_tool.add_document(sample_doc, sample_metadata)
        if doc_id:
            print(f"Added document with ID: {doc_id}")
            
            # Example: Search for documents
            results = rag_tool.search_documents("machine learning", k=3)
            print(f"Found {len(results)} results")
            
            # Example: Get AI response with context
            response = rag_tool.get_relevant_info("What is AI?")
            print(f"Response: {response[:200]}...")
            
            # Example: Get stats
            stats = rag_tool.get_stats()
            print(f"RAG Stats: {stats}")
    else:
        print("Failed to initialize RAG tool. Check your environment variables.")