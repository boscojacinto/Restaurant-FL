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

class SignalClient:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.running = False
        self.thread = None

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            print(f"Received message: {data}")
        except json.JSONDecodeError:
            print(f"Raw message: {message}")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, code, msg):
        print(f"Connection closed. Status: {code}, Message: {msg}")
        self.running = False

    def on_open(self, ws):
        print("Signal connection opened")
        self.running = True
        #ws.send(json.dumps({"type": "hello", "message": "Connected!"}))

    def run(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        self.ws.run_forever()

    def start(self):
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run)
            self.thread.daemon = True
            self.thread.start()
            print("Signal thread started")

    def stop(self):
        if self.ws:
            self.ws.close()
        self.running = False
        if self.thread:
            self.thread.join()
        print("Signal thread stopped")

    def send_message(self, message):
        if self.ws and self.running:
            self.ws.send(json.dumps(message))
            print(f"Sent message: {message}")

def main():	
	status_go = CDLL("./restaurant_status/libstatus.so.0")

	status_go.InitializeApplication.argtypes = [ctypes.c_char_p]
	status_go.InitializeApplication.restype = ctypes.c_char_p
	status_go.LoginAccount.argtypes = [ctypes.c_char_p]
	status_go.LoginAccount.restype = ctypes.c_char_p
	status_go.CallRPC.argtypes = [ctypes.c_char_p]
	status_go.CallRPC.restype = ctypes.c_char_p
	status_go.CreateAccountAndLogin.argtypes = [ctypes.c_char_p]
	status_go.CreateAccountAndLogin.restype = ctypes.c_char_p
	status_go.CallPrivateRPC.argtypes = [ctypes.c_char_p]
	status_go.CallPrivateRPC.restype = ctypes.c_char_p

	signal_client = SignalClient("ws://127.0.0.1:33327/signals")
	signal_client.start()
	time.sleep(2)

	data = {
	"dataDir": "./",
	"mixpanelAppId": "",
	"mixpanelToken": "",
	"mediaServerEnableTLS": False,
	"sentryDSN": "",
	"logDir": "./",
	"logEnabled": True,
	"logLevel": "INFO",
	"apiLoggingEnabled": True,
	"metricsEnabled": True,
	"metricsAddress": "",
	"deviceName": "restaurant-pc-7",
	"rootDataDir": "./",
	"wakuV2LightClient": False,
	"wakuV2EnableMissingMessageVerification": True,
	"wakuV2EnableStoreConfirmationForMessagesSent": True,
	}
	payload = json.dumps(data).encode('utf-8')	

	response = status_go.InitializeApplication(payload)
	response = json.loads(response)
	print(f"InitializeApplication:{response}")
	time.sleep(5)

	data = {'rootDataDir': './', 'kdfIterations': 256,
			'deviceName': 'restaurant-pc-7', 'displayName': 'Restaurant7',
			'password': 'swigg4@1234', "customizationColor":"blue",
			'wakuV2Nameserver':'8.8.8.8', 'wakuV2Fleet':'status.prod'}

	payload = json.dumps(data).encode('utf-8')	

	response = status_go.CreateAccountAndLogin(payload)
	response = json.loads(response)
	print(f"CreateAccountAndLogin:{response}")
	time.sleep(5)

	data = {
	"password": "swigg4@1234",
	"keyUid": "0x0c0bff93b4c526a4d70c72b47096734795fae99cd94ad23b4bf22ef5f67e3b40",
	"wakuV2Nameserver": "8.8.8.8",
	"wakuV2Fleet": "status.prod"
	}
	payload = json.dumps(data).encode('utf-8')	

	response = status_go.LoginAccount(payload)
	response = json.loads(response)
	print(f"LoginAccount:{response}")
	time.sleep(5)

	data = {
	"method": "wakuext_startMessenger",
	"params": [],
	}
	payload = json.dumps(data).encode('utf-8')	

	response = status_go.CallRPC(payload)
	response = json.loads(response)
	print(f"wakuext_startMessenge:{response}")
	time.sleep(5)

	data = {
	"method": "wakuext_sendContactRequest",
	"params": [
		{
			"id": "0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b",
			"message": "Hi, Pop",
		}
	]	
	}
	payload = json.dumps(data).encode('utf-8')	
	response = status_go.CallPrivateRPC(payload)
	response = json.loads(response)
	print(f"wakuext_sendContactRequest:{response}")
	time.sleep(5)

	data = {
	"method": "chat_createOneToOneChat",
	"params": [
		"",
		"0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b",
		""
	]	
	}
	payload = json.dumps(data).encode('utf-8')	
	response = status_go.CallPrivateRPC(payload)
	response = json.loads(response)
	print(f"chat_createOneToOneChat:{response}")
	time.sleep(5)

	data = {
	"method": "wakuext_sendChatMessage",
	"params": [
		{
			"chatId": "0x04c13e582c51cfd8185079b3136f7ce007683a3068788e09234069dda6e0dfc1040ca0308aa8948475f2f73ff1900ca4d2f36d46a484239731413d89dda84b2f6b",
			"text": "Hope it was not too smelly!",
			"contentType": 1
		}
	]	
	}
	payload = json.dumps(data).encode('utf-8')	

	response = status_go.CallPrivateRPC(payload)
	response = json.loads(response)
	print(f"wakuext_sendChatMessage:{response}")

	time.sleep(100000000)


if __name__ == '__main__':
	main()