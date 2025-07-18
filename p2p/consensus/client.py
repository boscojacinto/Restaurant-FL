import time
import json
import ctypes
from pathlib import Path
from datetime import datetime
from typing import List, Optional

CONSENSUS_LIB = "p2p/libs/libconsensus.so.0"

ConsensusCallBack = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)

class ConsensusClient:
    
    def __init__(self, root_path, node_key):

    	self.c_lib = None
    	self.c_root_path = root_path
    	self.c_data_dir = Path(self.c_root_path) / "data"
    	self.c_data_dir.mkdir(exist_ok=True)    	    	
    	self.c_config_path = Path(self.c_root_path) / "config"
    	self.c_config_path.mkdir(exist_ok=True)    	    	

    	self.c_node_key = node_key

    	self.c_init_lib()

    def c_init_lib(self):

    	self.c_lib = ctypes.CDLL(CONSENSUS_LIB)
    	self.c_lib.Init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    	self.c_lib.Init.restype = ctypes.c_void_p
    	self.c_lib.Start.argtypes = [ctypes.c_void_p, ConsensusCallBack, ctypes.c_void_p]
    	self.c_lib.Start.restype = ctypes.c_int
    	self.c_lib.Stop.argtypes = [ctypes.c_void_p, ConsensusCallBack, ctypes.c_void_p]
    	self.c_lib.Stop.restype = ctypes.c_int
    	self.c_lib.SetEventCallback.argtypes = [ctypes.c_void_p, ConsensusCallBack]
    	self.c_lib.SetEventCallback.restype = ctypes.c_int
    	self.c_lib.SendOrder.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
    	self.c_lib.SendOrder.restype = ctypes.c_int
    	self.c_lib.Query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
    	self.c_lib.Query.restype = ctypes.c_int

    def init(self):

    	root_path = ctypes.c_char_p(str(self.c_root_path).encode('utf-8'))
    	node_key = ctypes.c_char_p(self.c_node_key.encode('utf-8'))

    	self.c_ctx = self.c_lib.Init(root_path, node_key)

    	self.c_lib.SetEventCallback(self.c_ctx,
    		ConsensusCallBack(self.on_consensus_cb))

    def start(self):
    	
    	self.c_lib.Start(self.c_ctx, consensus_callback, None)
    	print("Started p2p consensus node")
    	
    def stop(self):

    	self.c_lib.Stop(self.c_ctx, consensus_callback, None)

    def query(key, path):

    	path = ctypes.c_char_p(path.encode('utf-8'))
    	key = ctypes.c_char_p(key.encode('utf-8'))
    	value = ctypes.c_char_p(None)

    	self.c_lib.Query(self.c_ctx, path, key, consensus_callback,
    					ctypes.byref(value))
    	value = value.value.decode('utf-8')

    	return value

    def publish(self, msg):
    	# self.c_lib.SendOrder(self.c_ctx, proof, peer_id, node_enr, 
    	# 	peer_list.encode('ascii'), inf_mode, consensus_callback, None)
    	print(f"Send message")

    def on_consensus_cb(self, ret_code, msg: str, user_data):
    	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
    	if ret_code != 0:
    		return

    	signal_str = msg.decode('utf-8')
    	signal = json.loads(signal_str)
    	if signal['type'] == "NewBlock":
    		print("New Block event")

@ConsensusCallBack
def consensus_callback(ret_code, msg: str, user_data):
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


if __name__ == "__main__":
	
	app = ConsensusClient()
	
	app.start()

	while True:
		time.sleep(0.2)
