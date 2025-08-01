import os
import sys
import json
import time
import queue
import ctypes
import base64
import requests
import threading
from enum import Enum
from pathlib import Path
from subprocess import Popen 
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from marshmallow import EXCLUDE

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
from config import ConfigOptions

STATUS_BACKEND_PORT = 0
STATUS_BACKEND_BIN = "im/libs/status-backend"
STATUS_GO_LIB = "im/libs/libstatus.so.0"

status_backend = None
SIGNAL_CB_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_char_p)

@dataclass_json(undefined=EXCLUDE)
@dataclass
class Account:
    name: str
    timestamp: int
    identicon: str
    key_uid: str = field(metadata=config(field_name="key-uid"))

class ContactRequestState(Enum):
    Pending = 1
    Accepted = 2
    Dismissed = 3

class StatusClient:
    def __init__(self, root_dir):
        self.config = ConfigOptions().get_im_config()
        self.lib = None
        self.cb = None
        self.uid = ''
        self.password = ''
        self.device_name = ''
        self.display_name = ''
        self.wakuv2_nameserver = '8.8.8.8'
        self.wakuv2_fleet = 'status.prod'
        self.thread = None
        self.message_queue = queue.Queue()

        self.root_dir = str(Path(ConfigOptions()._root_dir) / "im")
        self.data_dir = str(Path(self.root_dir) / "data")
        self.log_dir = str(Path(self.root_dir) / "log")
        self.root_data_dir = str(Path(self.root_dir) / "root_data")

        print(f"========= Initializing Status Messenger ========")

    def _init_lib(self):
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
        self.lib.SetSignalEventCallback.argtypes = [ctypes.c_void_p]
        self.lib.SetSignalEventCallback.restype = ctypes.c_char_p
        self.lib.GetAccounts.argtypes = []
        self.lib.GetAccounts.restype = ctypes.c_char_p
        self.lib.Logout.argtypes = []
        self.lib.Logout.restype = ctypes.c_char_p
        self.lib.GetChatKey.argtypes = [ctypes.c_char_p]
        self.lib.GetChatKey.restype = ctypes.c_char_p
        self.lib.AcceptContactRequest.argtypes = [ctypes.c_char_p]
        self.lib.AcceptContactRequest.restype = ctypes.c_char_p
        self.lib.GetContactByID.argtypes = [ctypes.c_char_p]
        self.lib.GetContactByID.restype = ctypes.c_char_p

    def init(self, device_name, cb):
        global status_backend
        # Spawn status backend dameon
        try:
            status_backend = Popen([STATUS_BACKEND_BIN, "--address",
                f"{self.config.status_host}:{self.config.status_port}"])
        except OSError as e:
            print(f"Error: status_backend failed to start:{e}.")
            raise e

        # Initialize status go library
        self.lib = ctypes.CDLL(STATUS_GO_LIB)
        self._init_lib()

        # Set event callback for messages from status-im
        self.device_name = device_name
        self.cb = SIGNAL_CB_TYPE(cb)
        self.lib.SetSignalEventCallback(self.cb)

        # Intialize status-im application
        config = {
            "dataDir": self.data_dir,
            "mixpanelAppId": "",
            "mixpanelToken": "",
            "mediaServerEnableTLS": False,
            "sentryDSN": "",
            "logDir": self.log_dir,
            "logEnabled": True,
            "logLevel": "INFO",
            "apiLoggingEnabled": True,
            "metricsEnabled": True,
            "metricsAddress": "",
            "deviceName": self.device_name,
            "rootDataDir": self.data_dir,
            "wakuV2LightClient": False,
            "wakuV2EnableMissingMessageVerification": True,
            "wakuV2EnableStoreConfirmationForMessagesSent": True
        }
        config = json.dumps(config).encode('utf-8')
        ret = self.lib.InitializeApplication(config)

    def getAccounts(self):
        accounts = self.lib.GetAccounts()
        accounts = accounts.decode('utf-8')

        if accounts == 'null' or accounts == '{"error":"accounts db wasn\'t initialized"}':
            return None

        accounts = Account.schema().loads(accounts, many=True)
        return accounts

    def login(self, uid, password):
        # Store login credentials
        self.uid = uid
        self.password = password
        data = {
            "password": self.password,
            "keyUid": self.uid,
            "wakuV2Nameserver": self.wakuv2_nameserver,
            "wakuV2Fleet": self.wakuv2_fleet
        }
        payload = json.dumps(data).encode('utf-8')
        self.lib.LoginAccount(payload)

        time.sleep(2)

        # Start status-im messenger
        data = {
            "method": "wakuext_startMessenger",
            "params": []
        }
        payload = json.dumps(data).encode('utf-8')
        ret = self.lib.CallRPC(payload)

    def logout(self):
        self.lib.Logout()

    def acceptContactRequest(self, contact_id):
        data = {
            "id": contact_id
        }
        payload = json.dumps(data).encode('utf-8')
        return self.lib.AcceptContactRequest(payload)

    def getContactInfo(self, public_key):
        contact_info = self.lib.GetContactByID(public_key.encode('utf-8')).decode('utf-8')
        return json.loads(contact_info)

    def getChatKey(self, public_key):
        data = {
            "public_key": public_key
        }
        payload = json.dumps(data).encode('utf-8')
        return self.lib.GetChatKey(payload).decode('utf-8')

    def getQRCode(self, url, port):
        url = base64.b64encode(url.encode()).decode()
        params = {'url': url, 'level': 3, 'allowProfileImage': False}
        return requests.get(f'http://localhost:{port}/GenerateQRCode',
                                params=params).content

    def createAccountAndLogin(self, display_name, password):
        # Create new account and login
    	self.display_name = display_name
    	self.password = password
    	data = {
            'rootDataDir': self.data_dir,
            'kdfIterations': 256,
            'deviceName': self.device_name,
            'displayName': self.display_name,
            'password': self.password,
            "customizationColor":"blue",
            'wakuV2Nameserver':self.wakuv2_nameserver,
            'wakuV2Fleet':self.wakuv2_fleet
        }
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CreateAccountAndLogin(payload)

    def sendContactRequest(self, publicKey, message):
        # Send contact request to recepient
    	data = {
            "method": "wakuext_sendContactRequest",
            "params": [
                {
                    "id": publicKey,
                    "message": message
                }
            ]
        }
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def createOneToOneChat(self, chatId):
        # Create one to one chat
    	data = {
            "method": "chat_createOneToOneChat",
            "params": ["", chatId, ""]
        }
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def deactivateOneToOneChat(self, Id):
        # Deactivate one to one chat
    	data = {
            "method": "wakuext_deactivateChat",
            "params": [
                {
                    "id": Id,
                    "preserveHistory": False
                }
            ]
        }
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def sendChatMessage(self, chatId, message):
        # Send chat message to recepient
    	data = {
            "method": "wakuext_sendChatMessage",
            "params": [
                {
                    "chatId": chatId,
                    "text": message,
                    "contentType": 1
                }
            ]
        }
    	payload = json.dumps(data).encode('utf-8')
    	self.lib.CallPrivateRPC(payload)

    def run(self):
        # Thread for message queue
    	while True:
    		try:
    			msg = self.message_queue.get(timeout=1)
    			print(f"Queued Message:{msg}")
    			#self.ai.sendMessage(msg)
    			self.message_queue.task_done()
    		except queue.Empty:
    			time.sleep(0.2)

    def start(self):
        # Starts message queue
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        return self.thread

    def queueMessage(self, message):
        # Queue message
    	self.message_queue.put(message)

    def stop(self):
        global status_backend
        # Stop client
        print(f"Logging out..")
        self.logout()
        if status_backend:
            status_backend.terminate()
            status_backend.wait()

