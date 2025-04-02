from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from smolagents import Tool
from langchain_community.retrievers import BM25Retriever
from smolagents import CodeAgent, OpenAIServerModel, HfApiModel

class PartyPlanningRetrieverTool(Tool):
	name = "party_planning_retriever"
	description = "Uses semantic search to retrieve relevant party planning ideas for Alfred's superhero-themed party at Wayne Manor."
	inputs = {
		"query": {
			"type": "string",
			"description": "The query to perform. This should be a query related to party planning or superhero themes."
		}
	}

	output_type = "string"

	def __init__(self, docs, **kwargs):
		super().__init__(**kwargs)
		self.retriever = BM25Retriever.from_documents(
			docs, k=5
		)

	def forward(self, query:str) -> str:

		docs = self.retriever.invoke(query)

		return "\nRetrieved ideas:\n" + "".join(
			[
				f"\n\n===== Idea {str(i)} ====\n" + doc.page_content
				for i, doc in enumerate(docs)
			]
		)

party_ideas = [
    {"text": "A superhero-themed masquerade ball with luxury decor, including gold accents and velvet curtains.", "source": "Party Ideas 1"},
    {"text": "Hire a professional DJ who can play themed music for superheroes like Batman and Wonder Woman.", "source": "Entertainment Ideas"},
    {"text": "For catering, serve dishes named after superheroes, like 'The Hulk's Green Smoothie' and 'Iron Man's Power Steak.'", "source": "Catering Ideas"},
    {"text": "Decorate with iconic superhero logos and projections of Gotham and other superhero cities around the venue.", "source": "Decoration Ideas"},
    {"text": "Interactive experiences with VR where guests can engage in superhero simulations or compete in themed games.", "source": "Entertainment Ideas"}
]

source_docs = [
	Document(page_content=doc["text"], metadata={"source": doc["source"]})
	for doc in party_ideas
]

text_splitter = RecursiveCharacterTextSplitter(
	chunk_size=500,
	chunk_overlap=50,
	add_start_index=True,
	strip_whitespace=True,
	separators=["\n\n", "\n", ".", " ", ""],
)

docs_processed = text_splitter.split_documents(source_docs)

party_planning_retriever = PartyPlanningRetrieverTool(docs_processed)

model = OpenAIServerModel(
	model_id="Triangle104/Dans-PersonalityEngine-v1.0.0-8b-Q4_K_M-GGUF",
	api_base="http://127.0.0.1:5000/v1",
	api_key="sk-no-key-required",
	max_tokens=2096,
	temperature=0.5,
	custom_role_conversions=None,	
)

agent = CodeAgent(tools=[party_planning_retriever], model=model)

agent.run(
	"Find ideas for a luxury superhero-themed party, including entertainment, catering and decoration options."
)
