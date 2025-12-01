from database_manager import DatabaseManager

demo_papers = [
    {
        "arxiv_id": "demo-0001",
        "title": "Medical AI for Cancer Detection",
        "abstract": "This is a demo abstract about AI for cancer detection.",
        "authors": ["Alice Smith", "Bob Lee"],
        "published_date": "2024-01-01",
        "categories": ["cs.CL", "q-bio.QM"],
        "pdf_url": "https://arxiv.org/pdf/demo-0001.pdf",
    },
    {
        "arxiv_id": "demo-0002",
        "title": "Deep Learning for Cardiology",
        "abstract": "This is a demo abstract about deep learning in cardiology.",
        "authors": ["Carol Jones"],
        "published_date": "2024-02-15",
        "categories": ["cs.LG", "q-bio.CB"],
        "pdf_url": "https://arxiv.org/pdf/demo-0002.pdf",
    },
    {
        "arxiv_id": "demo-0003",
        "title": "LLMs for Clinical Decision Support",
        "abstract": "Demo abstract about using large language models in clinical settings.",
        "authors": ["David Kim"],
        "published_date": "2024-03-10",
        "categories": ["cs.CL", "cs.AI"],
        "pdf_url": "https://arxiv.org/pdf/demo-0003.pdf",
    },
]

def main():
    db = DatabaseManager()
    for paper in demo_papers:
        ok = db.insert_paper(paper)
        print(f"Inserted {paper['arxiv_id']}: {ok}")
    db.close()

if __name__ == "__main__":
    main()
