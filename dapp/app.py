import os
import sys
import pytz 
import time
import json
import ctypes
import base64
from ctypes import CDLL
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
from p2p.client import P2PClient

CONSENSUS_LIB = "p2p/build/lib/libconsensus.so.0"

CLIENT_ID = 1
ROOT_PATH = f"/home/boscojacinto/projects/TasteBot/Restaurant-FL/p2p/consensus/client_{CLIENT_ID}"

HOST = "192.168.1.26"
NODE_KEY = 'fbcf082527559a8c79544373f78845f81b14b2d0cc2de55998d75e06b60c5b5e'

SETUP_PORT = 60011
SETUP_DISCV5_PORT = 9911
SETUP_BS_ENR = "enr:-KG4QB3eb3HfEYfkM3qJ4PbnxrjM_KK4BIsYh0hh1NNFWYi0UhgbINGm38YoNDgiRSFJBLJT2aRj2qifsWTlZ886GV6GAZb7zkKYgmlkgnY0gmlwhMCoARqCcnOFAFgBAACJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6mqDdWRwgia2hXdha3UyAw"

MSG_PORT = 60021
MSG_DISCV5_PORT = 9921
MSG_BS_ENR = "enr:-KG4QJ60C0bldIz1merR78DRaJWdhSyDGImFc7n42mHqgGadXRyzOG6LOuZPyEEshitBybFvqgFw039VmOmdTFPtgg-GAZb7zkrAgmlkgnY0gmlwhMCoARqCcnOFAFkBAACJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6nSDdWRwgibAhXdha3UyAw"

ConsensusCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

consensus_go = None
p2p_client = None

class AppClient:
    def __init__(self):
    	global consensus_go
    	
    	consensus_go = CDLL(CONSENSUS_LIB)
    	consensus_go.Init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    	consensus_go.Init.restype = ctypes.c_void_p
    	consensus_go.Start.argtypes = [ctypes.c_void_p, ConsensusCallBack, ctypes.c_void_p]
    	consensus_go.Start.restype = ctypes.c_int
    	consensus_go.Stop.argtypes = [ctypes.c_void_p, ConsensusCallBack, ctypes.c_void_p]
    	consensus_go.Stop.restype = ctypes.c_int
    	consensus_go.SetEventCallback.argtypes = [ctypes.c_void_p, ConsensusCallBack]
    	consensus_go.SetEventCallback.restype = ctypes.c_int
    	consensus_go.SendOrder.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
    	consensus_go.SendOrder.restype = ctypes.c_int
    	consensus_go.Query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
    	consensus_go.Query.restype = ctypes.c_int

    	self.p2p_client = P2PClient(CLIENT_ID, NODE_KEY, HOST, SETUP_PORT, SETUP_DISCV5_PORT, SETUP_BS_ENR,
    			MSG_PORT, MSG_DISCV5_PORT, MSG_BS_ENR)
    	root_path = ctypes.c_char_p(ROOT_PATH.encode('utf-8'))
    	node_key = ctypes.c_char_p(self.p2p_client.node_key.encode('utf-8'))
    	client_id = str(CLIENT_ID).encode('ascii')

    	self.consensus_ctx = consensus_go.Init(client_id, root_path, node_key)

    def start(self, consensus_cb):
    	global consensus_go

    	self.p2p_client.start()
    	self.cb = ConsensusCallBack(consensus_cb)
    	consensus_go.SetEventCallback(self.consensus_ctx, self.cb)
    	consensus_go.Start(self.consensus_ctx, consensusCallBack, None)

    def stop(self):
    	consensus_go.Stop(self.consensus_ctx, consensusCallBack, None)

    def createOrder(self):
    	global consensus_go
    	
    	proofStr = "thisistheproof"
    	proof = ctypes.c_char_p(proofStr.encode('utf-8'))

    	peer_id_str = self.p2p_client.msg_peer_id.encode('utf-8')
    	peer_id = ctypes.c_char_p(peer_id_str)
    	node_enr_bytes = self.p2p_client.get_msg_enr()	
    	node_enr = ctypes.c_char_p(node_enr_bytes)
    	inf_mode = "solo".encode('utf-8')

    	consensus_go.SendOrder(self.consensus_ctx, proof, peer_id, node_enr, peer_list_w_time, inf_mode, consensusCallBack, None) #peer_list_w_time
    	print(f"Send Order1")

    def on_consensus_cb(self, ret_code, msg: str, user_data):
    	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
    	if ret_code != 0:
    		return

    	signal_str = msg.decode('utf-8')
    	signal = json.loads(signal_str)
    	if signal['type'] == "NewBlock":
    		print("fNew Block incoming..")
    		pId = "16Uiu2HAmHk5rdpnfYGDh2XchPsQxvqB3j4zb9owzfFjV7fMWbQNs"
    		peer_list = json.dumps(['16Uiu2HAmHk5rdpnfYGDh2XchPsQxvqB3j4zb9owzfFjV7fMWbQNs']).encode('utf-8')		
    		#p2p_client.get_msg_idle_peer(signal['event']['height'], peer_list)

@ConsensusCallBack
def consensusCallBack(ret_code, msg: str, user_data):
	if ret_code != 0:
		print(f"Error: {ret_code}, msg:{msg}")

	if not user_data:
		return

	data_ref = ctypes.cast(user_data, ctypes.POINTER(ctypes.c_char_p))
	data_ptr = data_ref[0]

	if data_ref.contents:
		data_ref.contents = None

	if msg:
		msg_ptr = ctypes.create_string_buffer(msg)

		if not msg_ptr:
			return

		data_ref[0] = ctypes.cast(msg_ptr, ctypes.c_char_p)
		data_ptr = data_ref[0]

def getPeers(p2p_client):
	if p2p_client.msg_peer_id != None:
		peers_list = p2p_client.get_msg_peers()
		peers_string = peers_list.decode('utf-8')
		data = json.loads(peers_string)

		num_peers = len(data)
		for i in range(num_peers):
			if (data[i]['peerID'] == p2p_client.msg_peer_id):
				print(f"\nPeer at {i} is {data[i]['peerID']}")
				remove_id = i
			data[i]['idleTimestamp'] = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
			encoded = base64.b64encode("a12be".encode()).decode()
			data[i]['signature'] = encoded

		data.pop(remove_id)

	data = json.dumps(data)
	peer_list_w_time = data.encode('ascii')

def query(consensus_ctx):
	path_str = "data"
	path = ctypes.c_char_p(path_str.encode('utf-8'))
	key_str = "order"
	key = ctypes.c_char_p(key_str.encode('utf-8'))
	value = ctypes.c_char_p(None)
	consensus_go.Query(consensus_ctx, path, key, consensusCallBack, ctypes.byref(value))
	value = value.value.decode('utf-8')
	print(f"Value:{value}")

if __name__ == "__main__":
	app = AppClient()
	app.start(consensus_cb=app.on_consensus_cb)

	while True:
		time.sleep(0.2)
