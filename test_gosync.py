import os
import pytz 
import time
import json
import ctypes
from ctypes import CDLL
from datetime import datetime
from p2p.client import P2PClient

	# ID           peer.ID        `json:"peerID"`
	# Protocols    []protocol.ID  `json:"protocols"`
	# Addrs        []ma.Multiaddr `json:"addrs"`
	# Connected    bool           `json:"connected"`
	# PubsubTopics []string       `json:"pubsubTopics"`
	# IdleTimestamp time.Time     `json:"idleTimestamp"`

CONSENSUS_LIB = "./libconsensus.so.0"

CLIENT_ID = 1

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
	consensus_go.UpdateNodeAddr.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.UpdateNodeAddr.restype = ctypes.c_int
	consensus_go.SetEventCallback.argtypes = [ctypes.c_void_p, ConsensusCallBack]
	consensus_go.SetEventCallback.restype = ctypes.c_int
	consensus_go.SendOrder.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_bool, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.SendOrder.restype = ctypes.c_int
	consensus_go.Query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.Query.restype = ctypes.c_int

	root_path_str = f"/home/boscojacinto/projects/TasteBot/Restaurant-FL/p2p/consensus/client_{CLIENT_ID}"
	root_path = ctypes.c_char_p(root_path_str.encode('utf-8'))
	p2p_client = P2PClient(CLIENT_ID, NODE_KEY, HOST, SETUP_PORT, SETUP_DISCV5_PORT, SETUP_BS_ENR,
					MSG_PORT, MSG_DISCV5_PORT, MSG_BS_ENR)

	node_key = ctypes.c_char_p(p2p_client.node_key.encode('utf-8'))
	client_id = str(CLIENT_ID).encode('ascii')
	ctx = consensus_go.Init(client_id, root_path, node_key)
	# node id tm 04c6ff08d435e1b3f7fde44bdab924a166071bbb
	
	consensus_go.SetEventCallback(ctx, eventconsensusCallBack)
	
	p2p_client.start()
	print(f"P2P Started")

	time.sleep(4)

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
		if num_peers > 1 || num_peers == 1:
			nodeAddr = json.dumps(data[i]).encode('ascii')
			consensus_go.UpdateNodeAddr(ctx, nodeAddr, consensusCallBack, None)
			data.pop(remove_id)

	data = json.dumps(data)
	peer_list_w_time = data.encode('ascii')

	time.sleep(4)

	consensus_go.Start(ctx, consensusCallBack, None)
	print(f"Consensus Started")

	proofStr = "thisistheproof"
	proof = ctypes.c_char_p(proofStr.encode('utf-8'))

	peer_id_str = p2p_client.msg_peer_id.encode('utf-8')
	peer_id = ctypes.c_char_p(peer_id_str)
	node_enr_bytes = p2p_client.get_msg_enr()	
	node_enr = ctypes.c_char_p(node_enr_bytes)

	consensus_go.SendOrder(ctx, proof, peer_id, node_enr, peer_list_w_time, True, consensusCallBack, None) #peer_list_w_time
	print(f"Send Order1")	

	# time.sleep(14)

	# proofStr = "thisistheproof1"
	# proof = ctypes.c_char_p(proofStr.encode('utf-8'))

	# peer_id_str = p2p_client.msg_peer_id.encode('utf-8')
	# peer_id = ctypes.c_char_p(peer_id_str)
	# consensus_go.SendOrder(ctx, proof, peer_id, node_enr, peer_list_w_time, True, consensusCallBack, None) #node_enr
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
