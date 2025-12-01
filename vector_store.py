"""
Vector Store - Embeddings management with SQLite backend
Author: Amaan
"""

import numpy as np
from typing import List, Dict, Optional
import logging
from database_manager import DatabaseManager
from pdf_parser import PDFParser

logger = logging.getLogger(__name__)

class VectorStore:
    """Manages embeddings using SQLite for storage"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.parser = PDFParser()
        
        # Try to import sentence-transformers for free embeddings
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.use_transformer = True
            logger.info("Using Sentence Transformers for embeddings")
        except ImportError:
            logger.warning("Sentence Transformers not installed. Using simple embeddings.")
            logger.warning("Install with: pip install sentence-transformers")
            self.use_transformer = False
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text"""
        if self.use_transformer:
            # Use sentence transformers (free, local, good quality)
            embedding = self.model.encode(text)
            return embedding.tolist()
        else:
            # Fallback: Simple TF-IDF style embedding (for testing only)
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> List[float]:
        """Simple embedding for testing (not for production!)"""
        # Create a fixed-size vector based on text features
        import hashlib
        
        # Get text features
        text_lower = text.lower()
        features = []
        
        # Character frequency features
        for char in 'abcdefghijklmnopqrstuvwxyz':
            features.append(text_lower.count(char) / max(len(text_lower), 1))
        
        # Word features
        words = text_lower.split()
        features.append(len(words) / 100.0)  # Word count
        features.append(len(text) / 1000.0)  # Character count
        
        # Keyword features
        keywords = ['rag', 'llm', 'embedding', 'retrieval', 'transformer', 'attention']
        for keyword in keywords:
            features.append(1.0 if keyword in text_lower else 0.0)
        
        # Pad to fixed size (384 dimensions)
        while len(features) < 384:
            features.append(0.0)
        
        return features[:384]
    
    def process_paper(self, arxiv_id: str) -> bool:
        """Create and store embeddings for a paper"""
        try:
            # Get chunks from parser
            chunks = self.parser.prepare_chunks_for_embedding(arxiv_id)
            
            if not chunks:
                logger.warning(f"No chunks for {arxiv_id}")
                return False
            
            # Create and store embeddings for each chunk
            for chunk in chunks:
                embedding = self.create_embedding(chunk['text'])
                
                self.db.store_embedding(
                    paper_id=arxiv_id,
                    chunk_index=chunk['index'],
                    chunk_text=chunk['text'],
                    embedding=embedding,
                    chunk_type=chunk['type']
                )
            
            logger.info(f"Created {len(chunks)} embeddings for {arxiv_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {arxiv_id}: {e}")
            return False
    
    def process_all_papers(self, limit=50) -> Dict:
        """Process all papers that need embeddings"""
        # Get papers that have been parsed but not embedded
        self.db.cursor.execute("""
        SELECT arxiv_id FROM papers 
        WHERE processed = 1 AND embedding_created = 0
        LIMIT ?
        """, (limit,))
        
        papers = [row[0] for row in self.db.cursor.fetchall()]
        
        results = {
            'total': len(papers),
            'success': 0,
            'failed': []
        }
        
        for arxiv_id in papers:
            if self.process_paper(arxiv_id):
                results['success'] += 1
            else:
                results['failed'].append(arxiv_id)
        
        logger.info(f"Processed {results['success']}/{results['total']} papers")
        return results
    
    def semantic_search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for similar papers using embeddings"""
        # Create query embedding
        query_embedding = np.array(self.create_embedding(query))
        
        # Get all embeddings from database
        self.db.cursor.execute("""
        SELECT paper_id, chunk_index, chunk_text, embedding
        FROM embeddings
        """)
        
        results = []
        for row in self.db.cursor.fetchall():
            if row[3]:  # If embedding exists
                import pickle
                chunk_embedding = np.array(pickle.loads(row[3]))
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                
                results.append({
                    'paper_id': row[0],
                    'chunk_index': row[1],
                    'chunk_text': row[2],
                    'similarity': similarity
                })
        
        # Sort by similarity and get top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Group by paper and get unique papers
        seen_papers = set()
        unique_results = []
        
        for result in results:
            if result['paper_id'] not in seen_papers:
                # Get paper details
                paper = self.db.get_paper(result['paper_id'])
                if paper:
                    unique_results.append({
                        'arxiv_id': paper['arxiv_id'],
                        'title': paper['title'],
                        'abstract': paper['abstract'][:200] + '...',
                        'similarity': result['similarity'],
                        'relevant_chunk': result['chunk_text'][:200] + '...'
                    })
                    seen_papers.add(result['paper_id'])
                    
                    if len(unique_results) >= n_results:
                        break
        
        return unique_results
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)