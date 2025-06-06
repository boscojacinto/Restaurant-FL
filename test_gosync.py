import os
import pytz 
import time
import json
import ctypes
from ctypes import CDLL
from datetime import datetime
from p2p.client import P2PClient
from eth_account import Account

CONSENSUS_LIB = "p2p/build/lib/libconsensus.so.0"
WAKU_GO_LIB = "p2p/libgowaku.so.0"

SETUP_BS_ENR = "enr:-KG4QB3eb3HfEYfkM3qJ4PbnxrjM_KK4BIsYh0hh1NNFWYi0UhgbINGm38YoNDgiRSFJBLJT2aRj2qifsWTlZ886GV6GAZb7zkKYgmlkgnY0gmlwhMCoARqCcnOFAFgBAACJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6mqDdWRwgia2hXdha3UyAw"
MSG_BS_ENR = "enr:-KG4QJ60C0bldIz1merR78DRaJWdhSyDGImFc7n42mHqgGadXRyzOG6LOuZPyEEshitBybFvqgFw039VmOmdTFPtgg-GAZb7zkrAgmlkgnY0gmlwhMCoARqCcnOFAFkBAACJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6nSDdWRwgibAhXdha3UyAw"
NODE_KEY = '4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5'
HOST = "192.168.1.26"

ConsensusCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

consensus_go = None

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

@ConsensusCallBack
def eventconsensusCallBack(ret_code, msg: str, user_data):
	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
	if ret_code != 0:
		return

	event_str = msg.decode('utf-8')
	event = json.loads(event_str)

def main():
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
	consensus_go.SendOrder.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.SendOrder.restype = ctypes.c_int
	consensus_go.Query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.Query.restype = ctypes.c_int
	# consensus_go.AddPeer.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
	# consensus_go.AddPeer.restype = ctypes.c_int

	config_path_str = "/home/boscojacinto/projects/TasteBot/Restaurant-FL/p2p/consensus/config"
	config_path = ctypes.c_char_p(config_path_str.encode('utf-8'))
	p2p_client = P2PClient(WAKU_GO_LIB, SETUP_BS_ENR, MSG_BS_ENR, NODE_KEY, HOST)
	
	account = Account.from_key(p2p_client.node_key)

	ctx = consensus_go.Init(config_path, account.key)

	consensus_go.SetEventCallback(ctx, eventconsensusCallBack)

	consensus_go.Start(ctx, consensusCallBack, None)
	print(f"Consensus Started")
	
	# #time.sleep(1)
	p2p_client.start()
	print(f"P2P Started")

	time.sleep(4)

	peers_list = p2p_client.get_msg_peers()
	peers_string = peers_list.decode('utf-8')
	data = json.loads(peers_string)
	data[0]['idleTimestamp'] = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
	data[1]['idleTimestamp'] = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
	data = json.dumps(data)
	peer_list_w_time = data.encode('ascii')
	#consensus_go.AddPeer(ctx, peer_list_w_time, consensusCallBack, None)

	time.sleep(4)
	# #time.sleep(15)

	proofStr = "thisistheproof"
	proof = ctypes.c_char_p(proofStr.encode('utf-8'))

	peer_id_str = p2p_client.msg_peer_id.encode('utf-8')
	peer_id = ctypes.c_char_p(peer_id_str)
	node_enr_bytes = p2p_client.get_msg_enr()	
	node_enr = ctypes.c_char_p(node_enr_bytes)

	consensus_go.SendOrder(ctx, proof, peer_id, node_enr, peer_list_w_time, consensusCallBack, None)
	print(f"Send Order1")	

	# time.sleep(14)

	# proofStr = "thisistheproof1"
	# proof = ctypes.c_char_p(proofStr.encode('utf-8'))

	# peer_id_str = p2p_client.msg_peer_id.encode('utf-8')
	# peer_id = ctypes.c_char_p(peer_id_str)
	# consensus_go.SendOrder(ctx, proof, peer_id, consensusCallBack, None)
	# print(f"Send Order2")


	# path_str = "data"
	# path = ctypes.c_char_p(path_str.encode('utf-8'))
	# key_str = "order"
	# key = ctypes.c_char_p(key_str.encode('utf-8'))
	# value = ctypes.c_char_p(None)
	# consensus_go.Query(ctx, path, key, consensusCallBack, ctypes.byref(value))
	# value = value.value.decode('utf-8')
	# print(f"Value:{value}")

	# proofStr = "thisistheproof2"
	# proof = ctypes.c_char_p(proofStr.encode('utf-8'))
	# consensus_go.SendOrder(ctx, proof, consensusCallBack, None)
	# print(f"Send Order2")	


	# # consensus_go.Stop(ctx, consensusCallBack, None)
	# # print(f"STOPPED")	

	while True:
		time.sleep(1)

if __name__ == "__main__":
	main()


	# req = consenus_proto.SyncRequest()
	# order = req.order
	# dummy = req.dummy

	# dummy.state = "test"
	# order.proof.buf = b"thisistheproof"
	# order.timestamp.now = datetime.now().strftime("%H:%M:%S")
	# order.identity.publicKey = '4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5'
	# print(req.SerializeToString())
