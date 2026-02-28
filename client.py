import os
import sys
import grpc
import time
import json
import queue
import ctypes
import signal
import asyncio
import logging
import threading
from pathlib import Path
from types import FrameType
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

from PIL import Image
from io import BytesIO

from config import ConfigOptions
from im.client import StatusClient, ContactRequestState 
from ai.client import AIClient 
from fl.client import FLClient 
from ai.restaurant_kg import KGClient
from p2p.client import P2PClient

import p2p.restaurant_pb2 as psi_proto
import p2p.restaurant_pb2_grpc as r_psi
import private_set_intersection.python as psi

from embeddings import EmbeddingOps

client = None
client_threads = []

class Customer:
    PublicKey: str
    Name: str
    ChatKey: str
    EmojiHash: str

class ExitCode:
    SUCCESS = 0
    GRACEFUL_EXIT_SIGINT = 1
    GRACEFUL_EXIT_SIGTERM = 2
    GRACEFUL_EXIT_SIGQUIT = 3

SIGNAL_TO_EXIT_CODE: dict[int, int] = {
    signal.SIGINT: ExitCode.GRACEFUL_EXIT_SIGINT,
    signal.SIGTERM: ExitCode.GRACEFUL_EXIT_SIGTERM,
}

customers: List[Customer] = []

def register_exit_handler():
	default_handlers: dict[int, Callable[[int, FrameType], None]] = {}

	def exit_handler(signum: int, _frame: FrameType):
		global client
		global client_threads

		signal.signal(signum, default_handlers[signum])

		if client.fl_client is not None:
			client.fl_client.stop()
			
		if client.status_client is not None:
			client.status_client.stop()

		if client.ai_client is not None:
			client.ai_client.stop()

		if client.kg_client is not None:
			client.kg_client.stop()

		if client_threads is not None:
			for client_thread in client_threads:
				logger.info("Exiting thread")
				client_thread.join()

		if client.run_thread is not None:
			client.run_thread.join()

		logger.info("Exiting")

		sys.exit(0)

	for sig in SIGNAL_TO_EXIT_CODE:
		default_handler = signal.signal(sig, exit_handler)
		default_handlers[sig] = default_handler

def display_and_save_qrcode(data):
	img = Image.open(BytesIO(data))
	img.show()
	logger.info("Saving QR")
	root_dir = Path(ConfigOptions()._root_dir)
	file = root_dir / 'restaurant_contact.jpg'
	img.save(str(file))

class TasteBot():
	_instance = None

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self):
		global client_threads

		self.public_key = None
		self.uid = None
		self.media_port = []

		self.fl_client = None
		self.status_client = None
		self.ai_client = None
		self.kg_client = None
		self.neighbor_service = None
		self.psi_client = None
		self.p2p_client = None

		self.init_thread = None
		self.init_thread_lock = False
		
		self.init_nodelogin_event = threading.Event()
		self.customer_add_event = threading.Event()
		
		self.run_thread = None
		self.run_thread_lock = False


		self.add_customer_queue = queue.Queue()
		self.add_order_queue = queue.Queue()

		self.config = ConfigOptions().get_restaurant_config()

	def on_status_cb(self, signal: str):
		global customers

		signal = json.loads(signal)
		#print(f"signal received!:{signal}")
		if signal["type"] == "node.login":
			try:
				key_uid = signal["event"]["settings"]["key-uid"]
				public_key = signal["event"]["settings"]["current-user-status"]["publicKey"]
				logger.info(f"Node Login: uid:{key_uid} publicKey:{public_key}")
				self.public_key = public_key
				self.uid = key_uid
				self.init_nodelogin_event.set() 
			except KeyError:
				pass
		elif signal["type"] == "message.delivered":
			logger.debug("Message delivered!")
		elif signal["type"] == "messages.new":
			#print(f"event!:{signal["event"]}")
			try:
				chats = signal["event"]["chats"]
				messages = signal["event"]["messages"]
				contacts = signal["event"]["contacts"]
				for chat in chats:
					was_customer_added = False
					new_msg = chat["lastMessage"]["text"]
					customer_id = chat["lastMessage"]["from"]
					logger.info(f"New Message received!:{new_msg}, from:{customer_id}")
					if self.ai_client is not None:
						contact_info = self.status_client.getContactInfo(customer_id)
						#print(f"contact_info:{contact_info['contactRequestLocalState']}")
						if ("contactRequestLocalState" in contact_info and
							contact_info['contactRequestLocalState'] == ContactRequestState.Accepted.value):
							was_customer_added = True

						#print(f"was_customer_added:{was_customer_added}")

						if was_customer_added == True:
							customer_present = next((True for customer in customers if customer.PublicKey == customer_id), False)
							#print(f"customer_present:{customer_present}")
							if customer_present == False:
								self.add_customer_queue.put(contact_info)
								self.customer_add_event.set()
							else:
								self.ai_client.sendMessage(customer_id, new_msg)
						else:
							for contact in contacts:
								contact['msgId'] = next((msg['id'] for msg in messages if msg['chatId'] == contact['id']), None)
								if 'msgId' in contact:
									#print(f"In msgId")
									self.add_customer_queue.put(contact)
									self.customer_add_event.set()
								else:
									logger.warning("Message from unknown account, ignoring!")

			except KeyError:
				pass
		elif signal["type"] == "mediaserver.started":
			#print(f"media_port:{signal["event"]["port"]}")
			self.media_port.append(signal["event"]["port"])
		elif signal["type"] == "wakuv2.peerstats":
			#print(f"stats!:{signal["event"]}")
			pass
		else:
			#print(f"other!:{signal["type"]}")
			pass
		return

	async def on_ai_client_cb(self, type, customer_id,
							message: str, embeds):
		if type == "start":
			self.status_client.sendChatMessage(customer_id, message)
		elif type == "chat":
			self.status_client.sendChatMessage(customer_id, message)
		elif type == "feedback":
			await save_customer_embeddings(customer_id, embeds)
			self.status_client.sendChatMessage(customer_id, message)
		elif type == "end":
			await save_restaurant_embeddings(customer_id, embeds)
			self.status_client.deactivateOneToOneChat(customer_id)
		pass

	def on_consensus_cb(self, ret_code, msg: str, user_data):
		if ret_code != 0:
			return

		signal_str = msg.decode('utf-8')
		signal = json.loads(signal_str)
		if signal['type'] == "NewBlock":
			logger.info("New Block event")

	def attempt_init(self):
		accounts = self.status_client.getAccounts()
		if accounts == None:
			self.attempt_login(create=True)
			return False

		for account in accounts:
			if account.name == self.config.name:
				self.attempt_login(uid=account.key_uid, create=False)
				return True

		self.attempt_login(create=True)
		return False

	def attempt_login(self, uid=None, create=False):

		if create == False:
			logger.info(f"Attempt to login..uid:{uid}")
			self.status_client.login(
				uid,
				self.config.password
			)
		else:
			logger.info("Attempt to create and login..")
			self.status_client.createAccountAndLogin(
				self.config.name,
				self.config.password
			)

	def init_execute(self, nodelogin_event):
		while True:
			with self.init_thread_lock:
				if nodelogin_event.is_set() is False:
					self.attempt_init()
					time.sleep(10)
				else:
					time.sleep(0.5)
					asyncio.run(self.enable_services())
					time.sleep(0.5)
					asyncio.run(self.init_services())
					return

	def init_clients(self):

		self.fl_client = FLClient()

		self.status_client = StatusClient(
			root_dir=ConfigOptions()._root_dir
		)
		self.status_client.init(
			self.config.password,
			cb=self.on_status_cb
		)		

		self.ai_client = AIClient()
		self.p2p_client = P2PClient()
		self.p2p_client.init(
			on_consensus_cb=self.on_consensus_cb
		)
		self.kg_client = KGClient()

	async def init_services(self):
		try:
			async with grpc.aio.insecure_channel('[::]:50051') as channel:
				self.neighbor_service = r_psi.RestaurantNeighborStub(channel)
		except grpc.RpcError as e:
			logger.error(f"RPC error: {e}")

		client_key = bytes(range(32))
		self.psi_client = psi.client.CreateFromKey(client_key, False)			

	async def start_clients(self):

		fl_1_thread = self.fl_client.start()
		client_threads.append(fl_1_thread)
		
		status_thread = self.status_client.start()
		client_threads.append(status_thread)

		ai_thread = self.ai_client.start(cb=self.on_ai_client_cb)
		client_threads.append(ai_thread)

		p2p_thread = self.p2p_client.start()
		client_threads.append(p2p_thread)

		await self.kg_client.start()

		await(EmbeddingOps().init_embeddings())

	async def enable_services(self):
		try:
			chat_key = self.status_client.getChatKey(self.public_key)
			self.chat_key = chat_key.strip('"')

			qr_binary = self.status_client.getQRCode(self.chat_key,
									self.media_port[1])
			if qr_binary is not None:
				display_and_save_qrcode(qr_binary)
		except OSError as e:
			raise e

	async def add_customer(self, contact):
		global customers
				
		customer = Customer()
		customer.PublicKey = contact["id"]
		customer.Name = contact["primaryName"] or contact["displayName"]
		customer.ChatKey = contact["compressedKey"]  
		customer.EmojiHash = contact["emojiHash"]
		
		customers.append(customer)
		logger.info(f"New customer added:{customer.Name} id:{customer.PublicKey} emojiHash: {customer.EmojiHash}")

		try:
			async with grpc.aio.insecure_channel('[::]:50051') as channel:
				self.neighbor_service = r_psi.RestaurantNeighborStub(channel)
				intersection, restaurant_key = await self.psi_setup_and_fetch(
														customer.PublicKey)
		except grpc.RpcError as e:
			logger.error(f"RPC error: {e}")

		logger.info("Creating Greeting message..")
		await self.ai_client.greet(customer, restaurant_key)

	def add_order(self, order: Dict[str, Any]):

		if 'proof' in order:
			self.add_order_queue.put(order)
			logger.info("Added Order")

	async def create_order(self, order):

		await self.p2p_client.publish(order['proof'])
		logger.info("Created and sent Order")

	async def psi_setup_and_fetch(self, customer_id):

		setup_request = psi_proto.SetupRequest(num_customers=1)
		setup_reply = await self.neighbor_service.Setup(setup_request)
		logger.info(f"Neighbor Restaurant emojiHash:{setup_reply.restaurantKey}")

		items = [customer_id]
		request = psi.Request()
		request.ParseFromString(self.psi_client.CreateRequest(
								items).SerializeToString())

		customer_request = psi_proto.CustomerRequest(request=request)
		customer_reply = await self.neighbor_service.Fetch(request=customer_request)

		intersection = self.psi_client.GetIntersectionSize(setup_reply.setup,
											customer_reply.response)
		return intersection, setup_reply.restaurantKey

	def run_execute(self, customer_add_event):
		asyncio.run(self.start_clients())

		while True:
			with self.run_thread_lock:
				if customer_add_event.is_set() is True:
					if self.add_customer_queue.qsize() > 0:
						contact = self.add_customer_queue.get_nowait()
						if "msgId" in contact:
							self.status_client.acceptContactRequest(contact["msgId"])
						asyncio.run(self.add_customer(contact))
				try:
					order = self.add_order_queue.get_nowait()
					asyncio.run(self.create_order(order))
					self.add_order_queue.task_done()
				except queue.Empty:
					pass

				time.sleep(0.2)

	def start(self):
		self.init_thread = threading.Thread(target=self.init_execute,
									args=(self.init_nodelogin_event,))
		self.init_thread_lock = threading.Lock()

		self.run_thread = threading.Thread(target=self.run_execute,
									args=(self.customer_add_event,))
		self.run_thread_lock = threading.Lock()	

		self.init_thread.start()

def main():
	global client

	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s %(name)s %(levelname)s %(message)s'
	)

	client = TasteBot()

	client.init_clients()
	
	register_exit_handler()

	client.start()

	while client.init_thread.is_alive():
		time.sleep(0.1)

	client.run_thread.start()

	while True:
		time.sleep(0.1)

if __name__ == '__main__':
	main()
