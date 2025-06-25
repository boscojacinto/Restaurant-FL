import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from logging import INFO

from dotenv import load_dotenv

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
from graphiti_core.llm_client import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

graphiti = None

# Configure logging
logging.basicConfig(
    level=INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

load_dotenv()

# Neo4j connection parameters
# Make sure Neo4j Desktop is running with a local DBMS started
neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
neo4j_password = os.environ.get('NEO4J_PASSWORD', 'neo4j123')

if not neo4j_uri or not neo4j_user or not neo4j_password:
    raise ValueError('NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set')

async def start():
	global graphiti
	# Initialize Graphiti with Neo4j connection
	llm_config = LLMConfig(api_key="ollama", model="llama3.2", base_url="http://localhost:11434/v1")
	llm_client = OpenAIGenericClient(config=llm_config)

	embedder_config = OpenAIEmbedderConfig(api_key="ollama", embedding_model="nomic-embed-text", base_url="http://localhost:11434/v1")
	embedder = OpenAIEmbedder(config=embedder_config)

	cross_llm_config = LLMConfig(api_key="ollama", model="BAAI/bge-reranker-v2-m3", base_url="http://localhost:11434/v1")	
	cross_encoder = OpenAIRerankerClient(config=cross_llm_config)

	graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password, llm_client=llm_client, embedder=embedder, cross_encoder=cross_encoder)

async def add_eposides():
	global graphiti

	# Episodes list containing both text and JSON episodes
	episodes = [
	    {
	        'content': 'Kamala Harris is the Attorney General of California. She was previously '
	        'the district attorney for San Francisco.',
	        'type': EpisodeType.text,
	        'description': 'podcast transcript',
	    },
	    # {
	    #     'content': 'As AG, Harris was in office from January 3, 2011 – January 3, 2017',
	    #     'type': EpisodeType.text,
	    #     'description': 'podcast transcript',
	    # },
	    # {
	    #     'content': {
	    #         'name': 'Gavin Newsom',
	    #         'position': 'Governor',
	    #         'state': 'California',
	    #         'previous_role': 'Lieutenant Governor',
	    #         'previous_location': 'San Francisco',
	    #     },
	    #     'type': EpisodeType.json,
	    #     'description': 'podcast metadata',
	    # },
	    # {
	    #     'content': {
	    #         'name': 'Gavin Newsom',
	    #         'position': 'Governor',
	    #         'term_start': 'January 7, 2019',
	    #         'term_end': 'Present',
	    #     },
	    #     'type': EpisodeType.json,
	    #     'description': 'podcast metadata',
	    # },
	]

	# Add episodes to the graph
	for i, episode in enumerate(episodes):
	    await graphiti.add_episode(
	        name=f'Freakonomics Radio {i}',
	        episode_body=episode['content']
	        if isinstance(episode['content'], str)
	        else json.dumps(episode['content']),
	        source=episode['type'],
	        source_description=episode['description'],
	        reference_time=datetime.now(timezone.utc),
	    )
	    print(f'Added episode: Freakonomics Radio {i} ({episode["type"].value})')


async def main():
	global graphiti
    # Main function implementation will go here
	await start()

	try:
	    # Initialize the graph database with graphiti's indices. This only needs to be done once.
	    await graphiti.build_indices_and_constraints()
	    print(f"Done initializing")
	    # Additional code will go here

	    await add_eposides()

	finally:
	    # Close the connection
	    await graphiti.close()
	    print('\nConnection closed')

	pass

if __name__ == '__main__':
    asyncio.run(main())

