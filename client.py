import os
import time
import json
import queue
import ctypes
import asyncio
import requests
import threading
import multiprocessing
from ctypes import CDLL
from ollama import chat, generate, ChatResponse, AsyncClient
from flwr.client.supernode.app import run_supernode
import flwr

status_go = None
status_cb = None
ai_client = None
status_client = None

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

    def initApp(self, device_name, cb):
    	self.device_name = device_name
    	SIGNAL_CB_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
    	status_go.SetSignalEventCallback.argtypes = [ctypes.c_void_p]
    	self.cb = SIGNAL_CB_TYPE(cb)
    	status_go.SetSignalEventCallback(self.cb)
    	data = {"dataDir": self.root, "mixpanelAppId": "", "mixpanelToken": "", "mediaServerEnableTLS": False, "sentryDSN": "", "logDir": self.root, "logEnabled": True, "logLevel": "INFO", "apiLoggingEnabled": True, "metricsEnabled": True, "metricsAddress": "", "deviceName": self.device_name, "rootDataDir": self.root, "wakuV2LightClient": False, "wakuV2EnableMissingMessageVerification": True, "wakuV2EnableStoreConfirmationForMessagesSent": True}
    	payload = json.dumps(data).encode('utf-8')
    	response = self.lib.InitializeApplication(payload)
    	print(f"\nInit App:\n{response}")

    def login(self, uid, password):
    	self.uid = uid
    	self.password = password
    	data = {"password": self.password, "keyUid": self.uid, "wakuV2Nameserver": self.wakuv2_nameserver, "wakuV2Fleet": self.wakuv2_fleet}
    	payload = json.dumps(data).encode('utf-8')
    	response = self.lib.LoginAccount(payload)
    	print(f"\nLogin:\n{response}")

    	time.sleep(2)

    	data = {"method": "wakuext_startMessenger", "params": []}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallRPC(payload)

    def createAccountAndLogin(self, display_name, password):
    	self.display_name = display_name
    	self.password = password
    	data = {'rootDataDir': self.root, 'kdfIterations': 256, 'deviceName': self.device_name, 'displayName': self.display_name, 'password': self.password, "customizationColor":"blue", 'wakuV2Nameserver':self.wakuv2_nameserver, 'wakuV2Fleet':self.wakuv2_fleet}
    	payload = json.dumps(data).encode('utf-8')
    	response = self.lib.CreateAccountAndLogin(payload)
    	print(f"\nCreate Account and Login:\n{response}")

    def sendContactRequest(self, publicKey, message):
    	data = {"method": "wakuext_sendContactRequest", "params": [{"id": publicKey, "message": message}]}
    	payload = json.dumps(data).encode('utf-8')
    	response = self.lib.CallPrivateRPC(payload)
    	print(f"\nSent Contact Reques:\n{response}")

    def createOneToOneChat(self, chatId):
    	data = {"method": "chat_createOneToOneChat", "params": ["", chatId, ""]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def sendChatMessage(self, chatId, message):
    	data = {"method": "wakuext_sendChatMessage", "params": [{"chatId": chatId, "text": message, "contentType": 1}]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def on_status_cb(self, signal: str):
    	global ai_client
    	signal = json.loads(signal)
    	if signal["type"] == "node.login":
    		key_uid = signal["event"]["settings"]["key-uid"]
    		public_key = signal["event"]["settings"]["current-user-status"]["publicKey"]
    		print(f"Node Login: uid:{key_uid} publicKey:{public_key}")
    		if ai_client is not None and ai_client.started is False:
    			ai_client.start()
    	elif signal["type"] == "message.delivered":
    		print("Message delivered!")
    	elif signal["type"] == "messages.new":
    		print(f"MSGG:{signal["event"]}")    		
    		try:
    			new_msg = signal["event"]["chats"][0]["lastMessage"]["parsedText"][0]["children"][0]["literal"]
    			print(f"New Message received!:{new_msg}")
    			if ai_client is not None:
    				ai_client.sendMessage(new_msg)
    		except KeyError:
    			pass
    	return

    def run(self):
    	while True:
    		try:
    			msg = self.message_queue.get(timeout=1)
    			print(f"MESSAGE:{msg}")
    			self.ai.sendMessage(msg)
    			self.message_queue.task_done()
    		except queue.Empty:
    			print(f"Status loop")
    			time.sleep(1)

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
    	print("Exited!")

class AIClient:
	def __init__(self, model):
		self.thread = None
		self.model = model
		self.initial_prompt = {'role': 'user', 'content': 'Hello'}
		self.prompt = None
		self.lock = threading.Lock()
		self.started = False
		print(f"\n\n========= Launching model {self.model} ========\n\n")
		response = chat(model=self.model)

	def run(self):
		response = generate(model=self.model, prompt=self.initial_prompt['content'], stream=False)
		print(f"Bot:{response['response']}")

		while True: #not stop.is_set():
			print(f"AI loop running..:{self.prompt}")
			with self.lock:
				if self.prompt is not None:
					print(f"New prompt")
					response = generate(model=self.model, prompt=self.prompt['content'], stream=False)
					print(f"Bot:{response['response']}")
					self.sm.sendChatMessage("0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b", response['response'])					
					self.prompt = None
			time.sleep(1)
		print("AI loop stopped")

	def start(self):
		global status_client
		self.sm = status_client
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.run)
		self.started = True 		
		self.thread.start()

	def sendMessage(self, message):
		with self.lock:
			self.prompt = {'role': 'user', 'content': message}

	def stop(self):
		if self.thread:
			self.stop_event.set()
			self.started = False
			self.thread.join()
		print("AI client stopped")

class FLClient:
	def __init__(self):
		self.started = False
		self.thread = None

	def run(self):
		run_supernode()

	def start(self):
		self.thread = threading.Thread(target=self.run)
		self.started = True
		self.thread.start()


def main():
	global status_go
	global ai_client
	global status_client

	status_go = CDLL("./restaurant_status/libstatus.so.0")

	fl_client = FLClient()
	time.sleep(4)
	fl_client.start()

	status_client = StatusClient(root="./")
	ai_client = AIClient("swigg-gemma3:1b")

	status_client.initApp("restaurant-pc-8", cb=status_client.on_status_cb)
	time.sleep(1)

	# status_client.createAccountAndLogin("Restaurant8", "swigg@12345")
	# time.sleep(1)

	status_client.login("0xdc9e9199cee1b4686864450961848ca39420931d56080baa2ba196283dfc2682", "swigg@12345")
	time.sleep(1)

	# status_client.sendContactRequest("0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b", "Hello! This is your restaurant Bot")
	# time.sleep(1)

	status_client.createOneToOneChat("0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b")
	time.sleep(1)

	# status_client.sendChatMessage("0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b", "HI! I am your firendly restaurant bot")
	# time.sleep(0.2)

	status_client.start()

	try:
		while True:
			time.sleep(1)
			print("tick")
	except KeyboardInterrupt:
		status_client.stop()
		ai_client.stop()

if __name__ == '__main__':
	main()