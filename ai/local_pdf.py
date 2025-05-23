from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.vectordb.pgvector import PgVector

pdf_knowledge_base = PDFKnowledgeBase(
    path="/home/boscojacinto/Downloads/sudama-menu.pdf",
    # Table name: ai.pdf_documents
    vector_db=PgVector(
        table_name="pdf_documents",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
    reader=PDFReader(chunk=True),
)