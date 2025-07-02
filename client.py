import os
import sys
import grpc
import time
import json
import queue
import ctypes
import signal
import asyncio
import threading
from pathlib import Path
from types import FrameType
from typing import Callable

from config import ConfigOptions
from im.client import StatusClient 
from ai.client import AIClient 
from fl.client import FLClient 

import p2p.restaurant_pb2 as psi_proto
import p2p.restaurant_pb2_grpc as r_psi
import private_set_intersection.python as psi

from embeddings import EmbeddingOps
from qrcode import show_restaurant_code

client = None
status_client = None
ai_client = None
fl_client_1 = None
fl_client_2 = None
psi_client = None
client_threads = []

config = None
restaurant_service = None
restaurant_config = None

customer_ids = [{'id': 1, 'name': "Rohan", 'publicKey': "0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4", 'emojiHash': """👨‍✈️ℹ️📛🤘👩🏼‍🎤👨🏿‍🦱🏌🏼‍♀️🪣🐍🅱️👋🏼👱🏿‍♀️🙅🏼‍♂️🤨"""}]

async def restaurant_setup_and_fetch(customer_id):
	global psi_client

	setup_request = psi_proto.SetupRequest(num_customers=1)
	setup_reply = await restaurant_service.Setup(setup_request)
	print(f"Neighbor Restaurant emojiHash:{setup_reply.restaurantKey}")

	items = [customer_id]
	request = psi.Request()
	request.ParseFromString(psi_client.CreateRequest(
							items).SerializeToString())

	customer_request = psi_proto.CustomerRequest(request=request)
	customer_reply = await restaurant_service.Fetch(request=customer_request)

	intersection = psi_client.GetIntersectionSize(setup_reply.setup,
										customer_reply.response)
	return intersection, setup_reply.restaurantKey

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

async def on_ai_client_cb(type, customer_id, message: str, embeds):

	if type == "start":
		status_client.sendChatMessage(customer_id, message)
	elif type == "chat":
		status_client.sendChatMessage(customer_id, message)
	elif type == "feedback":
		await save_customer_embeddings(customer_id, embeds)
		status_client.sendChatMessage(customer_id, message)
	elif type == "end":
		await save_restaurant_embeddings(customer_id, embeds)
		status_client.deactivateOneToOneChat(customer_id)
	pass

class ExitCode:
    """Exit codes for TasteBot components."""

    SUCCESS = 0
    GRACEFUL_EXIT_SIGINT = 1
    GRACEFUL_EXIT_SIGTERM = 2
    GRACEFUL_EXIT_SIGQUIT = 3


SIGNAL_TO_EXIT_CODE: dict[int, int] = {
    signal.SIGINT: ExitCode.GRACEFUL_EXIT_SIGINT,
    signal.SIGTERM: ExitCode.GRACEFUL_EXIT_SIGTERM,
}

def register_exit_handler():

	default_handlers: dict[int, Callable[[int, FrameType], None]] = {}

	def exit_handler(signum: int, _frame: FrameType):
		global client
		global status_client
		global ai_client
		global fl_client_1
		global fl_client_2
		global client_threads

		signal.signal(signum, default_handlers[signum])

		if fl_client_1 is not None:
			fl_client_1.stop()

		if fl_client_2 is not None:
			fl_client_2.stop()
			
		if status_client is not None:
			status_client.stop()

		if ai_client is not None:
			ai_client.stop()

		if client_threads is not None:
			for client_thread in client_threads:
				client_thread.join()

		if client.run_thread is not None:
			client.run_thread.join()

	for sig in SIGNAL_TO_EXIT_CODE:
		default_handler = signal.signal(sig, exit_handler)
		default_handlers[sig] = default_handler

class TasteBot():
	_instance = None

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self):
		global ai_client
		global fl_client_1
		global fl_client_2
		global status_client
		global customer_ids
		global config
		global restaurant_config
		global client_threads

		self.public_key = None
		self.uid = None

		self.init_thread = None
		self.init_thread_lock = False
		self.init_done_event = threading.Event()
		
		self.run_thread = None
		self.run_thread_lock = False

		self.init_success = False

		config = ConfigOptions()
		restaurant_config = config.get_restaurant_config()

		self.init_clients()

		register_exit_handler()

	def on_status_cb(self, signal: str):
		global ai_client
		signal = json.loads(signal)
		#print(f"signal received!:{signal}")
		if signal["type"] == "node.login":
			try :
				key_uid = signal["event"]["settings"]["key-uid"]
				public_key = signal["event"]["settings"]["current-user-status"]["publicKey"]
				print(f"Node Login: uid:{key_uid} publicKey:{public_key}")
				self.public_key = public_key
				self.uid = key_uid
				self.init_done_event.set() 
			except KeyError:
				pass
		elif signal["type"] == "message.delivered":
			print("Message delivered!")
		elif signal["type"] == "messages.new":
			#print(f"event!:{signal["event"]}")
			try:
				new_msg = signal["event"]["chats"][0]["lastMessage"]["parsedText"][0]["children"][0]["literal"]
				c_id = signal["event"]["chats"][0]["lastMessage"]["from"]
				print(f"New Message received!:{new_msg}, from:{c_id}")
				if ai_client is not None:
					ai_client.sendMessage(c_id, new_msg)
			except KeyError:
				pass
		elif signal["type"] == "wakuv2.peerstats":
			#print(f"stats!:{signal["event"]}")
			pass
		else:
			#print(f"other!:{signal["type"]}")
			pass
		return

	def attempt_init(self):
		global status_client
		global restaurant_config

		accounts = status_client.getAccounts()
		if accounts == None:
			self.attempt_login(create=True)
			return False

		for account in accounts:
			# print(f"account.KeyUID:{account.key_uid}")
			# print(f"account.Name:{account.name}")
			# print(f"restaurant_config.name:{restaurant_config.name}")			
			if account.name == restaurant_config.name:
				self.attempt_login(uid=account.key_uid, create=False)
				return True

		self.attempt_login(create=True)
		return False

	def attempt_login(self, uid=None, create=False):
		global status_client
		global restaurant_config

		if create == False:
			print(f"Attempt to login..uid:{uid}")
			status_client.login(
				uid,
				restaurant_config.password
			)
		else:
			print("Attempt to create and login..")
			status_client.createAccountAndLogin(
				restaurant_config.name,
				restaurant_config.password
			)

	def init_execute(self, done_event):
		while True:
			with self.init_thread_lock:
				if (self.init_success is False and
					done_event.is_set() is False
				):
					self.attempt_init()
					time.sleep(10)
				else:
					return

	def init_clients(self):
		global ai_client
		global fl_client_1
		global fl_client_2
		global status_client

		fl_client_1 = FLClient(1)
		fl_client_2 = FLClient(2)

		status_client = StatusClient(root_dir=config._root_dir)
		status_client.init(
			restaurant_config.password,
			cb=self.on_status_cb
		)		

		ai_client = AIClient()

	async def start_clients(self):
		global status_client
		global ai_client
		global fl_client_1
		global fl_client_2
		global restaurant_config

		fl_1_thread = fl_client_1.start()
		client_threads.append(fl_1_thread)

		fl_2_thread = fl_client_2.start()
		client_threads.append(fl_2_thread)
		
		status_thread = status_client.start()
		client_threads.append(status_thread)

		ai_thread = ai_client.start(cb=on_ai_client_cb)
		client_threads.append(ai_thread)

		show_restaurant_code(self.public_key)

		await(EmbeddingOps().init_embeddings())

		# status_client.sendContactRequest(
		# 	customer_ids[0]['publicKey'],
		# 	"Hello! This is your restaurant Bot"
		# )

		# status_client.createOneToOneChat(
		# 	customer_ids[0]['publicKey']
		# )

		# intersection, restaurant_key = asyncio.run(
		# 	restaurant_feedback(customer_ids[0]['publicKey'])
		# )
		# #restaurant_key = """🚕🔈🧩👩🏽‍🤝‍👩🏾🏌️‍♂️👆🏾👩‍👧‍👧🐀😴🧑🏼‍💻🤒💇🏼‍♂️🥞🕵️‍♀️"""

		# asyncio.run(ai_client.greet(customer_ids[0], restaurant_key))

	def run_execute(self):
		asyncio.run(self.start_clients())

		while True:
			with self.run_thread_lock:
				time.sleep(0.2)

	def start(self):
		self.init_thread = threading.Thread(target=self.init_execute,
									args=(self.init_done_event, ))
		self.init_thread_lock = threading.Lock()
		self.run_thread = threading.Thread(target=self.run_execute)
		self.run_thread_lock = threading.Lock()	

		self.init_thread.start()

def main():

	client = TasteBot()
	client.start()

	while client.init_thread.is_alive():
		time.sleep(0.1)

	client.run_thread.start()

	while True:
		time.sleep(0.1)

if __name__ == '__main__':
	main()
