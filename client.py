import os
import sys
import grpc
import time
import json
import queue
import ctypes
import signal
import asyncio

from im.client import StatusClient 
from ai.client import AIClient 
from fl.client import FLClient 

import p2p.restaurant_pb2 as psi_proto
import p2p.restaurant_pb2_grpc as r_psi
import private_set_intersection.python as psi
from embeddings import (
	init_embeddings,
	save_customer_embeddings,
	save_restaurant_embeddings
)

status_client = None
ai_client = None
fl_client_1 = None
fl_client_2 = None
psi_client = None
client_threads = []

path = None
restaurant_service = None

customer_ids = [{'id': 1, 'name': "Rohan", 'publicKey': "0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4", 'emojiHash': """👨‍✈️ℹ️📛🤘👩🏼‍🎤👨🏿‍🦱🏌🏼‍♀️🪣🐍🅱️👋🏼👱🏿‍♀️🙅🏼‍♂️🤨"""}]

RESTAURANT_UID = "0x9f02de9e49c6784cc95120daac6211d6ae16c9cc3a6292c2394c220c312d6bec"
# Restaurant Public key 0x043b493da25ff3f725d66185ed2094f0058ee2a577987bd89b6c9c2cf70fdf9fc13c0629449be9e76b7826335b828ac2bb2eb8cf639e6f31eca442ebb38eb7b148 
RESTAURANT_PASSWORD = "swigg@12345"
RESTAURANT_DEVICE = "restaurant-pc-9"
RESTAURANT_NAME = "Restaurant9"

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

def on_status_cb(signal: str):
	global ai_client
	signal = json.loads(signal)
	#print(f"signal received!:{signal["type"]}")
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

async def on_ai_client_cb(type, customer_id, message: str, embeds):
	global path

	if type == "start":
		status_client.sendChatMessage(customer_id, message)
	elif type == "chat":
		status_client.sendChatMessage(customer_id, message)
	elif type == "feedback":
		await save_customer_embeddings(path, customer_id, embeds)
		status_client.sendChatMessage(customer_id, message)
	elif type == "end":
		await save_restaurant_embeddings(path, customer_id, embeds)
		status_client.deactivateOneToOneChat(customer_id)
	pass

def register_exit_handler():

	def exit_handler(signum, _frame):
		global status_client
		global ai_client
		global fl_client_1
		global fl_client_2
		global client_threads

		#signal.signal(signalnum, default_handlers[signalnum])

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

		sys.exit(1)

	signal.signal(signal.SIGINT, exit_handler)
	signal.signal(signal.SIGTERM, exit_handler)

def main():
	global path
	global ai_client
	global fl_client_1
	global fl_client_2
	global status_client
	global customer_ids
	global RESTAURANT_UID
	global RESTAURANT_PASSWORD
	global RESTAURANT_DEVICE
	global RESTAURANT_NAME

	path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ml/')

	fl_client_1 = FLClient(1)
	fl_1_thread = fl_client_1.start()
	client_threads.append(fl_1_thread)

	fl_client_2 = FLClient(2)
	fl_2_thread = fl_client_2.start()
	client_threads.append(fl_2_thread)

	status_client = StatusClient(root="./")

	ai_client = AIClient()

	register_exit_handler()

	asyncio.run(init_embeddings(path))

	status_client.init(RESTAURANT_PASSWORD, cb=on_status_cb)

	# status_client.createAccountAndLogin(RESTAURANT_NAME, RESTAURANT_PASSWORD)

	status_client.login(RESTAURANT_UID, RESTAURANT_PASSWORD)

	# status_client.sendContactRequest(customer_ids[0]['publicKey'], "Hello! This is your restaurant Bot")

	status_thread = status_client.start()
	client_threads.append(status_thread)
	
	ai_thread = ai_client.start(cb=on_ai_client_cb)
	client_threads.append(ai_thread)

	status_client.createOneToOneChat(customer_ids[0]['publicKey'])

	intersection, restaurant_key = asyncio.run(restaurant_feedback(customer_ids[0]['publicKey']))
	#restaurant_key = """🚕🔈🧩👩🏽‍🤝‍👩🏾🏌️‍♂️👆🏾👩‍👧‍👧🐀😴🧑🏼‍💻🤒💇🏼‍♂️🥞🕵️‍♀️"""

	asyncio.run(ai_client.greet(customer_ids[0], restaurant_key))

	while True:
		time.sleep(0.1)		

if __name__ == '__main__':
	main()