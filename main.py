import os
import time
import json
import ctypes
import requests
import websocket
import threading
import multiprocessing
from ctypes import CDLL
from ollama import chat
from ollama import ChatResponse
from flwr.client.supernode.app import run_supernode

status_go = None
status_cb = None

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

    def initApp(self, device_name, cb):
    	self.device_name = device_name
    	SIGNAL_CB_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
    	status_go.SetSignalEventCallback.argtypes = [ctypes.c_void_p]
    	self.cb = SIGNAL_CB_TYPE(cb)
    	status_go.SetSignalEventCallback(self.cb)
    	data = {"dataDir": self.root, "mixpanelAppId": "", "mixpanelToken": "", "mediaServerEnableTLS": False, "sentryDSN": "", "logDir": self.root, "logEnabled": True, "logLevel": "INFO", "apiLoggingEnabled": True, "metricsEnabled": True, "metricsAddress": "", "deviceName": self.device_name, "rootDataDir": self.root, "wakuV2LightClient": False, "wakuV2EnableMissingMessageVerification": True, "wakuV2EnableStoreConfirmationForMessagesSent": True}
    	payload = json.dumps(data).encode('utf-8')
    	status_go.InitializeApplication(payload)

    def login(self, uid, password):
    	self.uid = uid
    	self.password = password
    	data = {"password": self.password, "keyUid": self.uid, "wakuV2Nameserver": self.wakuv2_nameserver, "wakuV2Fleet": self.wakuv2_fleet}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.LoginAccount(payload)

    	time.sleep(5)

    	data = {"method": "wakuext_startMessenger", "params": []}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallRPC(payload)

    def createAccountAndLogin(self, display_name):
    	self.display_name = display_name
    	data = {'rootDataDir': self.root, 'kdfIterations': 256, 'deviceName': self.device_name, 'displayName': self.display_name, 'password': self.password, "customizationColor":"blue", 'wakuV2Nameserver':self.wakuv2_nameserver, 'wakuV2Fleet':self.wakuv2_fleet}
    	payload = json.dumps(data).encode('utf-8')
    	response = self.lib.CreateAccountAndLogin(payload)

    def sendContactRequest(self, publicKey, message):
    	data = {"method": "wakuext_sendContactRequest", "params": [{"id": publicKey, "message": message}]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def createOneToOneChat(self, chatId):
    	data = {"method": "chat_createOneToOneChat", "params": ["", chatId, ""]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def sendChatMessage(self, chatId, message):
    	data = {"method": "wakuext_sendChatMessage", "params": [{"chatId": chatId, "text": message, "contentType": 1}]}
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def on_status_cb(self, signal: str):
    	signal = json.loads(signal)
    	if signal["type"] == "node.login":
    		key_uid = signal["event"]["settings"]["key-uid"]
    		public_key = signal["event"]["settings"]["current-user-status"]["publicKey"]
    		print(f"Node Login: uid:{key_uid} publicKey:{public_key}")
    	elif signal["type"] == "message.delivered":
    		print("Message delivered!")
    	elif signal["type"] == "messages.new":
    		print(f"MSGG:{signal["event"]}")
    		try:
    			print(f"New Message received!:{signal["event"]["chats"][0]["lastMessage"]["parsedText"][0]["children"][0]["literal"]}")
    		except KeyError:
    			pass
    	return

    def stop(self):
    	print("Exited!")
    	pass

def launchModel():
	print("\n\n========= Trying to launch model ========\n\n")
	response: ChatResponse = chat(model='swigg-gemma3:1b')
	return response['message']['content']

def main():
	global status_go

	status_go = CDLL("./restaurant_status/libstatus.so.0")
	status_client = StatusClient(root="./")

	status_client.initApp("restaurant-pc-7", cb=status_client.on_status_cb)
	time.sleep(0.2)

	# #status_client.createAccountAndLogin("Restaurant7")
	# #time.sleep(0.2)

	status_client.login("0x0c0bff93b4c526a4d70c72b47096734795fae99cd94ad23b4bf22ef5f67e3b40", "swigg4@1234")
	time.sleep(0.2)

	# status_client.sendContactRequest("0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b", "Hello there")
	# time.sleep(0.2)

	status_client.createOneToOneChat("0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b")
	time.sleep(0.2)

	status_client.sendChatMessage("0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b", "Good morning my friend!")
	time.sleep(0.2)

	# msg = launchModel()
	# print(f"MSG:{msg}")

	try:
		while True:
			time.sleep(0.2)
	except KeyboardInterrupt:
		status_client.stop()

if __name__ == '__main__':
	main()