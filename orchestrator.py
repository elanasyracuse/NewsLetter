"""
Pipeline Orchestrator - Coordinates all components
Author: Amaan
"""

import json
import os
from datetime import datetime
import logging
import schedule
import time
from typing import Dict, List
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Import components with error handling
try:
    from database_manager import DatabaseManager
    # NOTE: Assuming digest_generator.py exists in the same directory.
    from digest_generator import EmailDigestBot
    from arxiv_bot import ArxivBot
    from pdf_parser import PDFParser
    from vector_store import VectorStore
    
except ImportError as e:
    print(f"Error importing components: {e}")
    print("Make sure all component files are in the same directory.")
    import sys
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Email Configuration (ACTION REQUIRED!) ---
# IMPORTANT: Update these credentials and ensure they are loaded securely!
SMTP_SERVER = 'smtp.gmail.com' 
SMTP_PORT = 587 
SENDER_EMAIL = 'cyberels366@gmail.com' # Your configured sender email
SMTP_PASSWORD = 'ifjm jhaa gvsf ldll'    # <--- REPLACE THIS: Your Gmail App Password

class PipelineOrchestrator:
    """Coordinates the entire data pipeline"""
    
    def __init__(self):
        logger.info("Initializing Pipeline Orchestrator...")
        
        # Load configuration
        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.error("config.json not found. Creating a placeholder.")
            self.config = {
                "days_back": 7,
                "max_papers_per_run": 50
            }
        
        # Initialize components
        self.db = DatabaseManager()
        self.arxiv_bot = ArxivBot()
        self.pdf_parser = PDFParser()
        self.vector_store = VectorStore()
        self.digest_bot = EmailDigestBot(self.db) # ADDED: Digest Bot Initialization
        
        # Create necessary directories
        os.makedirs("./data/team_exchange", exist_ok=True)
        
        logger.info("Orchestrator ready!")

    def _send_digest_email(self, recipient_email: str, subject: str, html_content: str):
        """Internal method to handle the actual SMTP mail sending."""
        if SMTP_PASSWORD == 'YOUR_APP_PASSWORD':
            logger.warning(f"Mocking email send to {recipient_email}. Please update SMTP credentials for live sending.")
            time.sleep(0.5) 
            return True

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = SENDER_EMAIL
            msg['To'] = recipient_email

            part1 = MIMEText(html_content, 'html')
            msg.attach(part1)

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Successfully sent digest to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False
            
    # Existing run_complete_pipeline... (omitted for brevity)
    def run_complete_pipeline(self) -> Dict:
        """Run the entire pipeline end-to-end"""
        logger.info("="*60)
        logger.info("STARTING COMPLETE PIPELINE")
        logger.info("="*60)
        
        start_time = datetime.now()
        results = {'start_time': start_time.isoformat(), 'steps': {}}
        
        try:
            # Step 1: Fetch new papers
            logger.info("Step 1: Fetching papers from arXiv...")
            fetch_results = self.arxiv_bot.fetch_recent_papers(
                days_back=self.config['days_back'],
                max_results=self.config['max_papers_per_run']
            )
            results['steps']['fetch'] = fetch_results
            logger.info(f"✓ Fetched {fetch_results['papers_stored']} papers")
            
            # Step 2: Parse PDFs
            logger.info("Step 2: Parsing PDF documents...")
            parse_results = self.pdf_parser.parse_all_unprocessed()
            results['steps']['parse'] = parse_results
            logger.info(f"✓ Parsed {parse_results['success']} papers")
            
            # Step 3: Create embeddings
            logger.info("Step 3: Creating embeddings...")
            embedding_results = self.vector_store.process_all_papers()
            results['steps']['embeddings'] = embedding_results
            logger.info(f"✓ Created embeddings for {embedding_results['success']} papers")
            
            # Step 4: Prepare data for team
            logger.info("Step 4: Preparing data for team...")
            team_results = self.prepare_team_data()
            results['steps']['team_data'] = team_results
            logger.info(f"✓ Prepared data for team")
            
            results['status'] = 'SUCCESS'
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            results['status'] = 'FAILED'
            results['error'] = str(e)
        
        results['end_time'] = datetime.now().isoformat()
        
        # Save pipeline results
        self._save_results(results)
        
        logger.info("="*60)
        logger.info(f"PIPELINE COMPLETE - Status: {results['status']}")
        logger.info("="*60)
        
        return results

    # Existing prepare_team_data... (omitted for brevity)
    def prepare_team_data(self) -> Dict:
        """Prepare data for team members"""
        team_results = {}
        
        # For Nikita - Papers needing summarization
        papers_for_nikita = self.db.get_papers_for_summarization()
        
        if papers_for_nikita:
            nikita_data = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "total_papers": len(papers_for_nikita)
                },
                "papers": []
            }
            
            for paper in papers_for_nikita:
                nikita_data["papers"].append({
                    "arxiv_id": paper['arxiv_id'],
                    "title": paper['title'],
                    "abstract": paper['abstract'],
                    "authors": paper['authors'],
                    "full_text": paper.get('full_text', ''),
                    "sections": paper.get('sections', {}),
                    "for_summarization": True
                })
            
            # Save to JSON for Nikita
            with open("./data/team_exchange/for_nikita_summarization.json", 'w') as f:
                json.dump(nikita_data, f, indent=2)
            
            team_results['nikita'] = len(papers_for_nikita)
            logger.info(f"Prepared {len(papers_for_nikita)} papers for Nikita")
        
        # For Arun - Papers with metadata for knowledge graph
        self.db.cursor.execute("""
        SELECT arxiv_id, title, abstract, authors, categories, published_date
        FROM papers
        WHERE processed = 1
        ORDER BY published_date DESC
        LIMIT 50
        """)
        
        arun_papers = []
        for row in self.db.cursor.fetchall():
            paper = dict(row)
            paper['authors'] = json.loads(paper['authors']) if paper['authors'] else []
            paper['categories'] = json.loads(paper['categories']) if paper['categories'] else []
            arun_papers.append(paper)
        
        if arun_papers:
            arun_data = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "total_papers": len(arun_papers)
                },
                "papers": arun_papers
            }
            
            with open("./data/team_exchange/for_arun_knowledge_graph.json", 'w') as f:
                json.dump(arun_data, f, indent=2)
            
            team_results['arun'] = len(arun_papers)
            logger.info(f"Prepared {len(arun_papers)} papers for Arun")
        
        # For Elana - Latest papers for UI
        self.db.cursor.execute("""
        SELECT arxiv_id, title, abstract, published_date
        FROM papers
        WHERE processed = 1
        ORDER BY published_date DESC
        LIMIT 20
        """)
        
        elana_papers = [dict(row) for row in self.db.cursor.fetchall()]
        
        if elana_papers:
            elana_data = {
                "latest_papers": elana_papers,
                "updated_at": datetime.now().isoformat(),
                "stats": self.db.get_stats()
            }
            
            with open("./data/team_exchange/for_elana_ui.json", 'w') as f:
                json.dump(elana_data, f, indent=2)
            
            team_results['elana'] = len(elana_papers)
            logger.info(f"Prepared {len(elana_papers)} papers for Elana")
        
        return team_results

    # Existing search_papers... (omitted for brevity)
    def search_papers(self, query: str) -> Dict:
        """Search papers using vector similarity"""
        results = self.vector_store.semantic_search(query, n_results=5)
        
        return {
            'query': query,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

    def send_weekly_digests(self):
        """
        ADDED: Generates personalized digests and sends them to all active subscribers.
        """
        logger.info("--- Starting Weekly Digest Delivery Job ---")
        
        subscribers = self.db.get_all_subscribers()
        total_sent = 0
        
        if not subscribers:
            logger.warning("No active subscribers found for digest. Skipping.")
            return
            
        logger.info(f"Found {len(subscribers)} active subscribers.")
        
        for subscriber in subscribers:
            recipient_email = subscriber['email']
            preferences = subscriber['preferences']
            
            logger.info(f"Generating personalized digest for {recipient_email}...")
            
            # 1. Generate the personalized HTML content
            html_content = self.digest_bot.generate_digest_html(preferences)
            
            # 2. Define the subject line
            subject = f"Your Weekly RAG Digest - Top Research Papers"
            
            # 3. Send the email
            if self._send_digest_email(recipient_email, subject, html_content):
                total_sent += 1
                
            # Important: Add a small delay to avoid hitting email provider rate limits
            time.sleep(1) 
            
        logger.info(f"--- Digest delivery job complete. Sent {total_sent} of {len(subscribers)} emails. ---")

    def schedule_weekly_run(self):
        """UPDATED: Schedule pipeline and digest to run weekly"""
        # Schedule the data pipeline to run every Sunday at 2:00 AM
        schedule.every().sunday.at("02:00").do(self.run_complete_pipeline)

        # Schedule the email delivery to run a bit later, e.g., every Sunday at 3:00 AM
        schedule.every().sunday.at("03:00").do(self.send_weekly_digests)
        
        logger.info("Data pipeline scheduled for weekly runs (Sundays at 2 AM)")
        logger.info("Email digest scheduled for weekly runs (Sundays at 3 AM)")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    # Existing get_status and _save_results... (omitted for brevity)
    def get_status(self) -> Dict:
        """Get current pipeline status"""
        stats = self.db.get_stats()
        
        # Get last run info
        self.db.cursor.execute("""
        SELECT start_time, end_time, status, papers_fetched, papers_processed
        FROM pipeline_runs
        ORDER BY id DESC
        LIMIT 1
        """)
        
        last_run = self.db.cursor.fetchone()
        
        if last_run:
            stats['last_run'] = {
                'start_time': last_run[0],
                'end_time': last_run[1],
                'status': last_run[2],
                'papers_fetched': last_run[3],
                'papers_processed': last_run[4]
            }
        else:
            stats['last_run'] = None
        
        return stats
    
    def _save_results(self, results: Dict):
        """Save pipeline results to file"""
        os.makedirs("./data/pipeline_runs", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"./data/pipeline_runs/run_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)


def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════╗
    ║   RAG Research Bot Pipeline Manager   ║
    ╚═══════════════════════════════════════╝
    """)
    
    orchestrator = PipelineOrchestrator()
    
    print("\nWhat would you like to do?")
    print("1. Run complete pipeline")
    print("2. Check pipeline status")
    print("3. Search papers")
    print("4. Schedule weekly runs (Includes Email Digest)") # UPDATED TEXT
    print("5. Exit")
    print("6. Send Email Digest NOW (For testing)") # ADDED OPTION
    
    choice = input("\nEnter choice (1-6): ") # UPDATED PROMPT
    
    if choice == "1":
        print("\nRunning complete pipeline...")
        results = orchestrator.run_complete_pipeline()
        print(f"\nPipeline completed with status: {results['status']}")
        
    elif choice == "2":
        status = orchestrator.get_status()
        print("\n📊 Pipeline Status:")
        print(f"  Total papers: {status['total_papers']}")
        print(f"  Processed papers: {status['processed_papers']}")
        print(f"  Papers with embeddings: {status['papers_with_embeddings']}")
        
        if status['last_run']:
            print(f"\n  Last run: {status['last_run']['start_time']}")
            print(f"  Status: {status['last_run']['status']}")
        
    elif choice == "3":
        query = input("\nEnter search query: ")
        results = orchestrator.search_papers(query)
        
        print(f"\nFound {len(results['results'])} relevant papers:")
        for i, paper in enumerate(results['results'], 1):
            print(f"\n{i}. {paper['title']}")
            print(f"   Similarity: {paper['similarity']:.3f}")
            print(f"   {paper['abstract']}")
    
    elif choice == "4":
        print("\nStarting scheduler... (Press Ctrl+C to stop)")
        orchestrator.schedule_weekly_run()
    
    elif choice == "5":
        print("\nGoodbye!")
    
    elif choice == "6": # ADDED LOGIC
        print("\nTriggering immediate email digest send...")
        orchestrator.send_weekly_digests()
        print("\nDigest send job complete (Check logs for status and your inbox).")
        
    else:
        print("\nInvalid choice")

if __name__ == "__main__":
    main()