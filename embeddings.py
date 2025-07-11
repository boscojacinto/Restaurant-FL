import os
import random
import asyncio
import torch
import scipy as sp
import numpy as np
import pandas as pd
from pathlib import Path
from ai.restaurant_model import AIModel as bot
from config import ConfigOptions

CUSTOMER_FEATURES_FILE = 'features_customers.npz'
RESTAURANT_FEATURES_FILE = 'features_restaurants.npz'
NEIGHBOR_REST_CUST_FILE = 'neighbor_rest_cust.npy'
RESTAURANT_EMBEDDINGS_FILE = 'restaurant_embeddings.pt'
RESTAURANT_INTERACTIONS_FILE = 'restaurant_interactions.csv'
CUSTOMER_EMBEDDINGS_FILE = 'customer_embeddings.pt' 

class EmbeddingOps():
	_instance = None

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self):
		config_options = ConfigOptions()
		self.config = config_options.get_embeddings_config()
		embeddings_dir = Path(config_options._root_dir) / "embeddings"
		embeddings_dir.mkdir(parents=True, exist_ok=True)
		self.cache_dir = embeddings_dir

	async def init_embeddings(self):
		customer_embeds = torch.zeros((
				self.config.max_customers,
				self.config.customer_features_num),
				dtype=torch.float)

		embeds = await create_embeddings(self.cache_dir)	
		
		random_customer_ids = torch.randperm(self.config.max_customers)[:25]
		torch.save(random_customer_ids, str(self.cache_dir / 'restaurant_customer_ids.pt'))
		
		customer_embeds[random_customer_ids] = embeds
		torch.save(customer_embeds, str(self.cache_dir / CUSTOMER_EMBEDDINGS_FILE))
		
		restaurant_embeds = torch.zeros((
								self.config.max_restaurants,
								self.config.restaurant_features_num),
								dtype=torch.float
							)
		torch.save(restaurant_embeds, str(self.cache_dir / RESTAURANT_EMBEDDINGS_FILE))
		
		if Path(self.cache_dir / CUSTOMER_FEATURES_FILE).exists():
			os.remove(Path(self.cache_dir / CUSTOMER_FEATURES_FILE))
		if Path(self.cache_dir / RESTAURANT_FEATURES_FILE).exists():
			os.remove(Path(self.cache_dir / RESTAURANT_FEATURES_FILE))
	
	async def save_customer_embeddings(self, customer_id, embeds):
		customer_embeds = torch.load(str(self.cache_dir / CUSTOMER_EMBEDDINGS_FILE))
		torch.manual_seed(42)
		
		c_id = random.randint(0, self.config.max_customers - 1)
		if customer_ids[0]['publicKey'] == customer_id:
			c_id = customer_ids[0]['id']

		customer_embeds[c_id] = torch.tensor(embeds, dtype=torch.float)
		torch.save(customer_embeds, str(self.cache_dir / CUSTOMER_EMBEDDINGS_FILE))
		
		customer_feats = sp.sparse.coo_matrix(customer_embeds)
		sp.sparse.save_npz(str(self.cache_dir / CUSTOMER_FEATURES_FILE), customer_feats)

	async def save_restaurant_embeddings(self, customer_id, embeds):

		restaurant_embeds = torch.load(str(self.cache_dir / RESTAURANT_EMBEDDINGS_FILE))
		torch.manual_seed(42)
		r_id = 1
		torch.manual_seed(24)
		c_id = random.randint(0, self.config.max_customers - 1)
		
		if customer_ids[0]['publicKey'] == customer_id:
			c_id = customer_ids[0]['id']

		restaurant_embeds[r_id] = torch.tensor(embeds, dtype=torch.float)
		torch.save(restaurant_embeds, str(self.cache_dir / RESTAURANT_EMBEDDINGS_FILE))
		
		restaurant_feats = sp.sparse.coo_matrix(restaurant_embeds)
		sp.sparse.save_npz(str(self.cache_dir / RESTAURANT_FEATURES_FILE), restaurant_feats)

		self.customer_embeddings = torch.load(str(self.cache_dir / CUSTOMER_EMBEDDINGS_FILE)) 
		r_c_adj = torch.zeros((self.config.max_restaurants, self.config.max_customers), dtype=torch.float)
		for i, v in enumerate(self.customer_embeddings):
			r_c_adj[r_id, i] = 1

		r_c_adj_np = r_c_adj.numpy()
		np.save(str(self.cache_dir / NEIGHBOR_REST_CUST_FILE), r_c_adj_np, allow_pickle=False)


async def create_embeddings(cache_dir):
	file = str(Path(__file__).parent / "ml" / RESTAURANT_INTERACTIONS_FILE)
	df = pd.read_csv(file)
	df = df.sample(frac=0.5, random_state=42)
	b = bot(customer=None)

	async def cust_embed(x):
		return await b.embed(x)

	async def process_embed(values):
		tasks = [cust_embed(x) for x in values]
		return await asyncio.gather(*tasks) 

	df["Customer's Description"] = await process_embed(df["Customer's Description"])

	customer_embeds = torch.tensor(
		df["Customer's Description"].tolist()
	)
	return customer_embeds

