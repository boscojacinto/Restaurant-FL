import os
import random
import asyncio
import torch
import scipy as sp
import numpy as np
import pandas as pd
from ai.restaurant_model import AIModel as bot

MAX_CUSTOMERS = 10000
MAX_RESTAURANTS = 1277
CUSTOMER_FEATURES_NUM = 1024
RESTAURANT_FEATURES_NUM = 1024

CUSTOMER_FEATURES_FILE = 'features_customers.npz'
RESTAURANT_FEATURES_FILE = 'features_restaurants.npz'
NEIGHBOR_REST_CUST_FILE = 'neighbor_rest_cust.npy'
RESTAURANT_EMBEDDINGS_FILE = 'restaurant_embeddings.pt'
RESTAURANT_INTERACTIONS_FILE = 'restaurant_interactions.csv'
CUSTOMER_EMBEDDINGS_FILE = 'customer_embeddings.pt' 

customer_embeddings = None

async def create_embeddings(file):
    df = pd.read_csv(file)
    df = df.sample(frac=0.5, random_state=42)
    b = bot()

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

async def init_embeddings(path):
	customer_embeds = torch.zeros((MAX_CUSTOMERS, CUSTOMER_FEATURES_NUM),
								 dtype=torch.float)
	embeds = await create_embeddings(os.path.join(path, RESTAURANT_INTERACTIONS_FILE))	
	#print(f"embeds:{embeds}")
	random_customer_ids = torch.randperm(MAX_CUSTOMERS)[:25]
	#print(f"random_customer_ids:{random_customer_ids.shape}")
	torch.save(random_customer_ids, os.path.join(path, 'restaurant_customer_ids.pt'))
	customer_embeds[random_customer_ids] = embeds
	#print(f"customer_embeds:{customer_embeds}")
	torch.save(customer_embeds, os.path.join(path, CUSTOMER_EMBEDDINGS_FILE))
	
	restaurant_embeds = torch.zeros((MAX_RESTAURANTS, RESTAURANT_FEATURES_NUM),
								 dtype=torch.float)
	torch.save(restaurant_embeds, os.path.join(path, RESTAURANT_EMBEDDINGS_FILE))
	if os.path.exists(os.path.join(path, CUSTOMER_FEATURES_FILE)):
		os.remove(os.path.join(path, CUSTOMER_FEATURES_FILE))
	if os.path.exists(os.path.join(path, RESTAURANT_FEATURES_FILE)):
		os.remove(os.path.join(path, RESTAURANT_FEATURES_FILE))

async def save_customer_embeddings(path, customer_id, embeds):
	customer_embeds = torch.load(os.path.join(path, CUSTOMER_EMBEDDINGS_FILE))
	torch.manual_seed(42)
	c_id = random.randint(0, MAX_CUSTOMERS - 1)
	#print(f"customer_ids[0]['publicKey']:{customer_ids[0]['publicKey']}")
	#print(f"customer_id:{customer_id}")
	if customer_ids[0]['publicKey'] == customer_id:
		print("In IF")
		c_id = customer_ids[0]['id']
	print(f"c_id:{c_id}")

	customer_embeds[c_id] = torch.tensor(embeds, dtype=torch.float)
	#print(f"customer_embeds.shape:{customer_embeds.shape}")
	torch.save(customer_embeds, os.path.join(path, CUSTOMER_EMBEDDINGS_FILE))
	customer_feats = sp.sparse.coo_matrix(customer_embeds)
	#print(f"customer_feats:{customer_feats}")
	sp.sparse.save_npz(os.path.join(path, CUSTOMER_FEATURES_FILE), customer_feats)

async def save_restaurant_embeddings(path, customer_id, embeds):
	global customer_embeddings

	restaurant_embeds = torch.load(os.path.join(path, RESTAURANT_EMBEDDINGS_FILE))
	torch.manual_seed(42)
	#r_id = random.randint(0, MAX_RESTAURANTS - 1)
	r_id = 1
	torch.manual_seed(24)
	c_id = random.randint(0, MAX_CUSTOMERS - 1)
	
	if customer_ids[0]['publicKey'] == customer_id:
		c_id = customer_ids[0]['id']
	print(f"r_id:{r_id}")
	print(f"c_id:{c_id}")

	restaurant_embeds[r_id] = torch.tensor(embeds, dtype=torch.float)
	torch.save(restaurant_embeds, os.path.join(path, RESTAURANT_EMBEDDINGS_FILE))
	restaurant_feats = sp.sparse.coo_matrix(restaurant_embeds)
	sp.sparse.save_npz(os.path.join(path, RESTAURANT_FEATURES_FILE), restaurant_feats)

	customer_embeddings = torch.load(os.path.join(path, CUSTOMER_EMBEDDINGS_FILE)) 
	r_c_adj = torch.zeros((MAX_RESTAURANTS, MAX_CUSTOMERS), dtype=torch.float)
	for i, v in enumerate(customer_embeddings):
		r_c_adj[r_id, i] = 1

	r_c_adj_np = r_c_adj.numpy()
	np.save(os.path.join(path, NEIGHBOR_REST_CUST_FILE), r_c_adj_np, allow_pickle=False)
