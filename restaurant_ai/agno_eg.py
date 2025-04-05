from agno.agent import Agent
from agno.embedder.ollama import OllamaEmbedder
from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.models.ollama import Ollama
from agno.vectordb.pgvector import PgVector, SearchType

db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

knowledge_base = PDFKnowledgeBase(
    path="/home/boscojacinto/Downloads/MenuandTariffforA-la-Carteitems.pdf",
    vector_db=PgVector(
        table_name="menu-items",
        db_url=db_url,
        search_type=SearchType.hybrid,
        embedder=OllamaEmbedder(id="llama3.2", dimensions=3072),
    ),
    reader=PDFReader(chunk=True),
)
knowledge_base.load(recreate=True)  # Comment out after first run

agent = Agent(
    model=Ollama(id="llama3.2"),
    knowledge=knowledge_base,
    search_knowledge=True,
    read_chat_history=True,
    show_tool_calls=True,
    markdown=True,    
)

agent.print_response("What's the cost of Samosa?", markdown=True)