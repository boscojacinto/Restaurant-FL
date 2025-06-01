import os
import re
import sys
import grpc
import time
import json
import torch
import queue
import ctypes
import random
import asyncio
import requests
import threading
import scipy as sp
import numpy as np
import pandas as pd
import multiprocessing
from ctypes import CDLL
import p2p.restaurant_pb2 as psi_proto
import p2p.restaurant_pb2_grpc as r_psi
from math import ceil, floor
from subprocess import Popen, PIPE 
from scipy.sparse import coo_matrix
from flwr.client.supernode.app import run_supernode
from ai.restaurant_model import AIModel as bot
from ai.restaurant_model import CUSTOM_MODEL
import private_set_intersection.python as psi

path1 = None
status_go = None
status_cb = None
ai_client = None
status_client = None
fl_client_1 = None
fl_client_2 = None
psi_client = None
customer_embeddings = None
restaurant_service = None

STATUS_BACKEND_PORT = 0
STATUS_BACKEND_BIN = "im/libs/status-backend"
STATUS_GO_LIB = "im/libs/libstatus.so.0"

AI_MODEL = "swigg1.0-gemma3:4b"
customer_ids = [{'id': 1, 'name': "Rohan", 'publicKey': "0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4", 'emojiHash': """👨‍✈️ℹ️📛🤘👩🏼‍🎤👨🏿‍🦱🏌🏼‍♀️🪣🐍🅱️👋🏼👱🏿‍♀️🙅🏼‍♂️🤨"""}]
RESTAURANT_UID = "0xdc9e9199cee1b4686864450961848ca39420931d56080baa2ba196283dfc2682"
RESTAURANT_PASSWORD = "swigg@12345"
RESTAURANT_DEVICE = "restaurant-pc-8"
RESTAURANT_NAME = "Restaurant8"
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
INITIAL_PROMPT = 'Hello'

class StatusClient:
    def __init__(self, root):
    	global status_go
    	self.lib = status_go
    	self.cb = None
    	self.root = root
    	self.uid = ''
    	self.password = ''
    	self.device_name = ''
    	self.display_name = ''
    	self.wakuv2_nameserver = '8.8.8.8'
    	self.wakuv2_fleet = 'status.prod'
    	self.lib.InitializeApplication.argtypes = [ctypes.c_char_p]
    	self.lib.InitializeApplication.restype = ctypes.c_char_p
    	self.lib.LoginAccount.argtypes = [ctypes.c_char_p]
    	self.lib.LoginAccount.restype = ctypes.c_char_p
    	self.lib.CallRPC.argtypes = [ctypes.c_char_p]
    	self.lib.CallRPC.restype = ctypes.c_char_p
    	self.lib.CreateAccountAndLogin.argtypes = [ctypes.c_char_p]
    	self.lib.CreateAccountAndLogin.restype = ctypes.c_char_p
    	self.lib.CallPrivateRPC.argtypes = [ctypes.c_char_p]
    	self.lib.CallPrivateRPC.restype = ctypes.c_char_p
    	self.thread = None
    	self.message_queue = queue.Queue()
    	print(f"\n========= Initializing Status Messenger ========\n")    	

    def initApp(self, device_name, cb):
    	self.device_name = device_name
    	SIGNAL_CB_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
    	status_go.SetSignalEventCallback.argtypes = [ctypes.c_void_p]
    	self.cb = SIGNAL_CB_TYPE(cb)
    	status_go.SetSignalEventCallback(self.cb)
    	data = {"dataDir": self.root, "mixpanelAppId": "", "mixpanelToken": "", "mediaServerEnableTLS": False, "sentryDSN": "", "logDir": self.root, "logEnabled": True, "logLevel": "INFO", "apiLoggingEnabled": True, "metricsEnabled": True, "metricsAddress": "", "deviceName": self.device_name, "rootDataDir": self.root, "wakuV2LightClient": False, "wakuV2EnableMissingMessageVerification": True, "wakuV2EnableStoreConfirmationForMessagesSent": True}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.InitializeApplication(payload)

    def login(self, uid, password):
    	self.uid = uid
    	self.password = password
    	data = {"password": self.password, "keyUid": self.uid, "wakuV2Nameserver": self.wakuv2_nameserver, "wakuV2Fleet": self.wakuv2_fleet}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.LoginAccount(payload)

    	time.sleep(2)

    	data = {"method": "wakuext_startMessenger", "params": []}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallRPC(payload)

    def createAccountAndLogin(self, display_name, password):
    	self.display_name = display_name
    	self.password = password
    	data = {'rootDataDir': self.root, 'kdfIterations': 256, 'deviceName': self.device_name, 'displayName': self.display_name, 'password': self.password, "customizationColor":"blue", 'wakuV2Nameserver':self.wakuv2_nameserver, 'wakuV2Fleet':self.wakuv2_fleet}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CreateAccountAndLogin(payload)

    def sendContactRequest(self, publicKey, message):
    	data = {"method": "wakuext_sendContactRequest", "params": [{"id": publicKey, "message": message}]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def createOneToOneChat(self, chatId):
    	data = {"method": "chat_createOneToOneChat", "params": ["", chatId, ""]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def deactivateOneToOneChat(self, Id):
    	data = {"method": "wakuext_deactivateChat", "params": [{"id": Id, "preserveHistory": False}]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def sendChatMessage(self, chatId, message):
    	data = {"method": "wakuext_sendChatMessage", "params": [{"chatId": chatId, "text": message, "contentType": 1}]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def on_status_cb(self, signal: str):
    	global ai_client
    	signal = json.loads(signal)
    	print(f"signal received!:{signal["type"]}")
    	if signal["type"] == "node.login":
    		try :
    			key_uid = signal["event"]["settings"]["key-uid"]
    			public_key = signal["event"]["settings"]["current-user-status"]["publicKey"]
    			print(f"Node Login: uid:{key_uid} publicKey:{public_key}")
    		except KeyError:
    			pass
    	elif signal["type"] == "message.delivered":
    		print("Message delivered!")
    	elif signal["type"] == "messages.new":
    		print(f"event!:{signal["event"]}")
    		try:
    			new_msg = signal["event"]["chats"][0]["lastMessage"]["parsedText"][0]["children"][0]["literal"]
    			c_id = signal["event"]["chats"][0]["lastMessage"]["from"]
    			print(f"New Message received!:{new_msg}, from:{c_id}")
    			if ai_client is not None:
    				ai_client.sendMessage(c_id, new_msg)
    		except KeyError:
    			pass
    	elif signal["type"] == "wakuv2.peerstats":
    		print(f"stats!:{signal["event"]}")
    		pass
    	else:
    		print(f"other!:{signal["type"]}")
    		pass
    	return

    def run(self):
    	while True:
    		try:
    			msg = self.message_queue.get(timeout=1)
    			print(f"Queued Message:{msg}")
    			self.ai.sendMessage(msg)
    			self.message_queue.task_done()
    		except queue.Empty:
    			time.sleep(0.2)

    def start(self):
    	global ai_client
    	self.ai = ai_client
    	self.thread = threading.Thread(target=self.run)
    	self.thread.start()

    def queueMessage(self, message):
    	self.message_queue.put(message)

    def stop(self):
    	if self.thread:
    		self.thread.join()

class AIClient:
	def __init__(self, model):
		self.thread = None
		self.initial_prompt = INITIAL_PROMPT
		self.prompt = None
		self.customer_id = None
		self.started = False
		self.bots = {}
		self.lock = threading.Lock()
		print(f"\n========= Launching AI model {CUSTOM_MODEL} ========\n")

	def run(self, save_customer_embeddings, save_restaurant_embeddings):

		while True:
			with self.lock:
				if self.prompt is not None \
				and self.customer_id is not None \
				and self.bots[self.customer_id] is not None:
					bot = self.bots[self.customer_id]
					print(f"New prompt: {self.prompt}, from customer: {self.customer_id}")

					response = asyncio.run(bot.generate(self.prompt))
					print(f"Sending Bot's response:{response}")
					self.sm.sendChatMessage(self.customer_id, response)

					if bot.summary is not None:
						embeds = asyncio.run(bot.embed(bot.summary))
						bot.summary = None
						asyncio.run(save_customer_embeddings(self.customer_id, embeds))
						self.sm.sendChatMessage(self.customer_id, bot.feedback_prompt)
					elif bot.feedback is not None:
						embeds = asyncio.run(bot.embed(bot.feedback))
						bot.feedback = None
						asyncio.run(save_restaurant_embeddings(self.customer_id, embeds))
						self.sm.deactivateOneToOneChat(self.customer_id)
						self.bots[self.customer_id] = None

					self.prompt = None
					self.customer_id = None

	def start(self):
		global status_client

		self.sm = status_client
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.run, args=(save_customer_embeddings,
									save_restaurant_embeddings))
		self.started = True 		
		self.thread.start()

	def sendMessage(self, customer_id, message):
		with self.lock:
			try:
				self.bots[customer_id]
				self.prompt = message
				self.customer_id = customer_id
			except KeyError:
				print("Cannot send message to Bot, User Session closed.")

	def greet(self, customer_id):
		c_id = customer_id['publicKey']
		try:
			self.bots[c_id]
		except KeyError:
			intersection, restaurantKey = asyncio.run(restaurant_feedback(c_id))
			if intersection == 1 and restaurantKey is not None:
				print("Customer in Neighbor restaurant Set")
			self.bots[c_id] = bot(customer_id, restaurantKey)

		_generate = self.bots[c_id].generate
		self.sm.createOneToOneChat(c_id)

		response = asyncio.run(_generate(self.initial_prompt))
		print(f"Greeting:{response}")
		self.sm.sendChatMessage(c_id, response)

	def stop(self):
		if self.thread:
			self.stop_event.set()
			self.started = False
			self.thread.join()

class FLClient:
	def __init__(self, i):
		self.started = False
		self.thread = None
		self.id = i
		print(f"\n========= Initializing Flower Client {i} ========\n")

	def run(self, i):
		run_supernode(i)

	def start(self):
		self.thread = threading.Thread(target=self.run, args=(self.id,))
		self.started = True
		self.thread.start()

	def stop(self):
		self.thread.stop()

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

async def init_embeddings():
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

async def save_customer_embeddings(customer_id, embeds):
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
	customer_feats = coo_matrix(customer_embeds)
	#print(f"customer_feats:{customer_feats}")
	sp.sparse.save_npz(os.path.join(path, CUSTOMER_FEATURES_FILE), customer_feats)

async def save_restaurant_embeddings(customer_id, embeds):
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
	restaurant_feats =coo_matrix(restaurant_embeds)
	sp.sparse.save_npz(os.path.join(path, RESTAURANT_FEATURES_FILE), restaurant_feats)

	customer_embeddings = torch.load(os.path.join(path, CUSTOMER_EMBEDDINGS_FILE)) 
	r_c_adj = torch.zeros((MAX_RESTAURANTS, MAX_CUSTOMERS), dtype=torch.float)
	for i, v in enumerate(customer_embeddings):
		r_c_adj[r_id, i] = 1

	r_c_adj_np = r_c_adj.numpy()
	np.save(os.path.join(path, NEIGHBOR_REST_CUST_FILE), r_c_adj_np, allow_pickle=False)

async def restaurant_feedback(customer_id):
	global restaurant_service
	global psi_client

	client_key = bytes(range(32))
	psi_client = psi.client.CreateFromKey(client_key, False)
	try:
		async with grpc.aio.insecure_channel('[::]:50051') as channel:
			restaurant_service = r_psi.RestaurantNeighborStub(channel)
			return await restaurant_setup_and_fetch(customer_id)

	except grpc.RpcError as e:
		print(f"RPC error: {e}")
	except Exception as e:
		print(f"Restaurant feeback error: {e}")

async def restaurant_setup_and_fetch(customer_id):
	global psi_client

	setup_request = psi_proto.SetupRequest(num_customers=1)
	setup_reply = await restaurant_service.Setup(setup_request)
	print(f"setup_reply.restaurantKey:{setup_reply.restaurantKey}")

	items = [customer_id]
	request = psi.Request()
	request.ParseFromString(psi_client.CreateRequest(
							items).SerializeToString())

	customer_request = psi_proto.CustomerRequest(request=request)
	customer_reply = await restaurant_service.Fetch(request=customer_request)

	intersection = psi_client.GetIntersectionSize(setup_reply.setup,
										customer_reply.response)
	return intersection, setup_reply.restaurantKey

def main(p):
	global path
	global status_go
	global ai_client
	global fl_client_1
	global fl_client_2
	global status_client
	global customer_ids
	global AI_MODEL
	global RESTAURANT_UID
	global RESTAURANT_PASSWORD
	global RESTAURANT_DEVICE
	global RESTAURANT_NAME
	global STATUS_BACKEND_BIN

	path = p
	try:
		status_backend = Popen([STATUS_BACKEND_BIN, "--address", "127.0.0.1:0"])
	except OSError as e:
		print(f"Error: status_backend failed to start:{e}.")

	status_go = CDLL(STATUS_GO_LIB)

	fl_client_1 = FLClient(1)
	fl_client_1.start()
	time.sleep(0.5)

	fl_client_2 = FLClient(2)
	fl_client_2.start()
	time.sleep(0.5)

	status_client = StatusClient(root="./")
	time.sleep(0.5)

	ai_client = AIClient(AI_MODEL)

	asyncio.run(init_embeddings())

	status_client.initApp(RESTAURANT_PASSWORD, cb=status_client.on_status_cb)
	time.sleep(0.5)

	# status_client.createAccountAndLogin(RESTAURANT_NAME, RESTAURANT_PASSWORD)
	# time.sleep(0.5)

	status_client.login(RESTAURANT_UID, RESTAURANT_PASSWORD)
	time.sleep(0.5)

	# status_client.sendContactRequest(customer_ids[0]['publicKey'], "Hello! This is your restaurant Bot")
	# time.sleep(0.5)

	status_client.start()
	time.sleep(0.5)
	
	ai_client.start()

	ai_client.greet(customer_ids[0])

	try:
		while True:
			time.sleep(0.1)
	except KeyboardInterrupt:
		fl_client_1.stop()
		fl_client_2.stop()
		status_client.stop()
		ai_client.stop()
		status_backend.terminate()

async def test():
	b = bot()
	await init_embeddings()
	# embeds = await b.embed("The users show great love for mughlai food")
	# await save_customer_embeddings("0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4", embeds)
	# embeds = await b.embed("The restaurant is know for its mughlai food")
	# await save_restaurant_embeddings("0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4", embeds)

if __name__ == '__main__':
	path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ml/')
	main(path)