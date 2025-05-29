import os
import time
import ctypes
from ctypes import CDLL
from datetime import datetime 
# import order_pb2 as order_proto
# import consensus_pb2 as consenus_proto

CONSENSUS_LIB = "p2p/consensus/build/lib/libconsensus.so.0"

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


def main():
	global consensus_go
	consensus_go = CDLL(CONSENSUS_LIB)
	consensus_go.Init.argtypes = []
	consensus_go.Init.restype = ctypes.c_void_p
	consensus_go.Start.argtypes = [ctypes.c_void_p, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.Start.restype = ctypes.c_int
	consensus_go.Stop.argtypes = [ctypes.c_void_p, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.Stop.restype = ctypes.c_int
	consensus_go.SendOrder.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ConsensusCallBack, ctypes.c_void_p]
	consensus_go.SendOrder.restype = ctypes.c_int

	ctx = consensus_go.Init()

	consensus_go.Start(ctx, consensusCallBack, None)
	print(f"STARTED")

	# req = consenus_proto.SyncRequest()
	# order = req.order
	# dummy = req.dummy

	# dummy.state = "test"
	# order.proof.buf = b"thisistheproof"
	# order.timestamp.now = datetime.now().strftime("%H:%M:%S")
	# order.identity.publicKey = '4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5'
	# print(req.SerializeToString())
	
	time.sleep(1)

	proofStr = "thisistheproof"
	proof = ctypes.c_char_p(proofStr.encode('utf-8'))
	consensus_go.SendOrder(ctx, proof, consensusCallBack, None)
	print(f"SEND")	

	time.sleep(10)

	# consensus_go.Stop(ctx, consensusCallBack, None)
	# print(f"STOPPED")	

	while True:
		time.sleep(1)

if __name__ == "__main__":
	main()