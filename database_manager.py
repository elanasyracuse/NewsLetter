import sqlite3
import json
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Core database manager for all RAG bot data"""
    
    def __init__(self, db_path="./data/ragbot.db"):
        self.db_path = db_path
        # ensure ./data exists
        import os
        os.makedirs("./data", exist_ok=True)

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()
        logger.info(f"Database initialized at {db_path}")
    
    def _create_tables(self):
        """Create all necessary tables"""
        
        # Main papers table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            arxiv_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT,
            authors TEXT,  -- JSON array stored as text
            published_date DATETIME,
            categories TEXT,  -- JSON array
            pdf_url TEXT,
            pdf_downloaded BOOLEAN DEFAULT 0,
            full_text TEXT,
            sections TEXT,  -- JSON object
            processed BOOLEAN DEFAULT 0,
            embedding_created BOOLEAN DEFAULT 0,
            summary_generated BOOLEAN DEFAULT 0,
            fetched_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Embeddings table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT,
            embedding BLOB,
            chunk_type TEXT,
            FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
        )
        """)
        
        # Pipeline logs
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time DATETIME,
            end_time DATETIME,
            papers_fetched INTEGER,
            papers_processed INTEGER,
            status TEXT,
            error_message TEXT
        )
        """)
        
        # Users/Subscribers table for the email digest
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            preferences TEXT,
            is_active BOOLEAN DEFAULT 1,
            join_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        self.conn.commit()

    # --- Paper-Related Methods ---

    def insert_paper(self, paper_data: Dict) -> bool:
        """Insert or update a paper."""
        try:
            authors = json.dumps(paper_data.get("authors", []))
            categories = json.dumps(paper_data.get("categories", []))
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO papers (
                    arxiv_id, title, abstract, authors, published_date,
                    categories, pdf_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_data["arxiv_id"],
                    paper_data["title"],
                    paper_data.get("abstract"),
                    authors,
                    paper_data.get("published_date"),
                    categories,
                    paper_data.get("pdf_url"),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting paper: {e}")
            self.conn.rollback()
            return False
    
    def get_paper(self, arxiv_id: str) -> Optional[Dict]:
        """Fetch a single paper by its ID."""
        self.cursor.execute("SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        paper = dict(row)
        # parse JSON fields
        paper["authors"] = json.loads(paper["authors"]) if paper.get("authors") else []
        paper["categories"] = json.loads(paper["categories"]) if paper.get("categories") else []
        if paper.get("sections"):
            paper["sections"] = json.loads(paper["sections"])
        else:
            paper["sections"] = {}
        return paper

    def get_papers_for_summarization(self) -> List[Dict]:
        """Fetch papers that have full text but lack a summary."""
        self.cursor.execute("""
        SELECT * FROM papers 
        WHERE pdf_downloaded = 1 AND full_text IS NOT NULL AND summary_generated = 0
        LIMIT 5
        """)
        return [dict(row) for row in self.cursor.fetchall()]

    def get_papers_for_digest(self, start_date: str, end_date: str) -> List[Dict]:
        """Fetch processed papers within a date range."""
        self.cursor.execute("""
        SELECT * FROM papers
        WHERE published_date BETWEEN ? AND ?
          AND processed = 1
          AND summary_generated = 1
        """, (start_date, end_date))
        return [dict(row) for row in self.cursor.fetchall()]

    def search_papers(self, query: str, limit: int = 10) -> List[Dict]:
        """Simple text search in papers."""
        like = f"%{query}%"
        self.cursor.execute("""
        SELECT arxiv_id, title, abstract, authors, published_date
        FROM papers
        WHERE (title LIKE ? OR abstract LIKE ?)
        ORDER BY published_date DESC
        LIMIT ?
        """, (like, like, limit))
        rows = self.cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["authors"] = json.loads(d["authors"]) if d.get("authors") else []
            except json.JSONDecodeError:
                d["authors"] = []
            results.append(d)
        return results

    def get_stats(self) -> Dict:
        """Fetch basic pipeline statistics."""
        self.cursor.execute("SELECT COUNT(arxiv_id) FROM papers")
        total_papers = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(arxiv_id) FROM papers WHERE processed = 1")
        processed_papers = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(arxiv_id) FROM papers WHERE embedding_created = 1")
        papers_with_embeddings = self.cursor.fetchone()[0]
        
        return {
            "total_papers": total_papers,
            "processed_papers": processed_papers,
            "papers_with_embeddings": papers_with_embeddings,
        }
        
    # --- User Management Methods ---

    def add_or_update_user(self, email: str, preferences: List[str]):
        """Add a new user or update an existing user's preferences."""
        pref_json = json.dumps(preferences)
        self.cursor.execute("""
        INSERT INTO users (email, preferences, is_active) 
        VALUES (?, ?, 1)
        ON CONFLICT(email) DO UPDATE SET 
            preferences = excluded.preferences, 
            is_active = excluded.is_active
        """, (email, pref_json))
        self.conn.commit()
        logger.info(f"User preferences updated for: {email}")

    def get_all_subscribers(self) -> List[Dict]:
        """Retrieve all active subscribers with their preferences."""
        self.cursor.execute("SELECT email, preferences FROM users WHERE is_active = 1")
        subscribers = []
        for row in self.cursor.fetchall():
            try:
                preferences = json.loads(row["preferences"]) if row["preferences"] else []
            except json.JSONDecodeError:
                preferences = []
            subscribers.append({"email": row["email"], "preferences": preferences})
        return subscribers
    
    def close(self):
        """Close database connection."""
        self.conn.close()


if __name__ == "__main__":
    # quick test of users table (optional)
    manager = DatabaseManager()
    manager.add_or_update_user("amaan@example.com", ["RAG", "LLM", "Knowledge Graph"])
    manager.add_or_update_user("jane.doe@example.com", ["Fine-Tuning", "Transformer"])
    manager.add_or_update_user("cyberels366@gmail.com", ["RAG", "LLM", "Knowledge Graph"])
    
    subscribers = manager.get_all_subscribers()
    print("\nActive Subscribers:")
    for sub in subscribers:
        print(f"- {sub['email']} | Prefs: {sub['preferences']}")
        
    manager.close()
