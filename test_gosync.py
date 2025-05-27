import os
import ctypes
from ctypes import CDLL

SYNC_GO_LIB = "p2p/consensus/build/lib/libgosync.so.0"

sync_go = None

def main():
	global sync_go
	sync_go = CDLL(SYNC_GO_LIB)
	print(f"sync_go:{sync_go}")
	# sync_go.sync_start.argtypes = [ctypes.c_char_p]
	# sync_go.sync_start.restype = ctypes.c_void_p

	sync_go.sync_init()
	print(f"Success")

	# config_path_str = "p2p/consensus/config/config.toml"
	# config_path = ctypes.c_char_p(config_path_str.encode('utf-8'))
	sync_go.sync_start()

if __name__ == "__main__":
	main()