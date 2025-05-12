import json
import ctypes
import time
from ctypes import CDLL

WAKU_GO_LIB = "./libgowaku.so.0"

WakuCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

config_obj = {"host": None, "port": None}
config = json.dumps(config_obj)
config_bytes = config.encode('utf-8')
configuration = ctypes.c_char_p(config_bytes)

user_data = ctypes.c_void_p(12345)

def main():
	@WakuCallBack
	def wakuCallBack(ret_code, msg: str, user_data):
		print(f"ret_code:{ret_code}")
		print(f"msg:{msg}")
		print(f"user_data:{user_data}")

	cb = wakuCallBack
	
	waku_go = CDLL(WAKU_GO_LIB)
	waku_go.waku_new.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack]
	waku_go.waku_new.restype = ctypes.c_void_p
	waku_go.waku_start.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_start.restype = ctypes.c_int
	waku_go.waku_peerid.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peerid.restype = ctypes.c_int
	waku_go.waku_listen_addresses.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_listen_addresses.restype = ctypes.c_int
	waku_go.waku_content_topic.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
										   ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_content_topic.restype = ctypes.c_int
	waku_go.waku_default_pubsub_topic.argtypes = [WakuCallBack, ctypes.c_void_p]
	waku_go.waku_default_pubsub_topic.restype = ctypes.c_int
	waku_go.waku_dns_discovery.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
										   ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_dns_discovery.restype = ctypes.c_int


	waku_go.waku_connect.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_connect.restype = ctypes.c_int
	waku_go.waku_peer_cnt.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peer_cnt.restype = ctypes.c_int

	ctx = waku_go.waku_new(None, configuration, cb, user_data)
	
	time.sleep(2)

	ret = waku_go.waku_start(ctx, wakuCallBack, user_data)
	print(f"start:{ret}")
	time.sleep(2)

	ret = waku_go.waku_peerid(ctx, wakuCallBack, user_data)
	print(f"peerid:{ret}")
	time.sleep(2)

	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, user_data)
	print(f"address:{ret}")
	time.sleep(2)

	app_name_str = "tastebot"
	app_version_str = "1.0"
	topic_name_str = "1.0"
	encoding_str = "rfc26"
	app_name = ctypes.c_char_p(app_name_str.encode('utf-8'))
	app_version = ctypes.c_char_p(app_version_str.encode('utf-8'))
	topic_name = ctypes.c_char_p(topic_name_str.encode('utf-8'))
	encoding = ctypes.c_char_p(encoding_str.encode('utf-8'))

	ret = waku_go.waku_content_topic(app_name, app_version, topic_name, encoding, wakuCallBack, user_data)
	print(f"content topic:{ret}")
	time.sleep(2)

	ret = waku_go.waku_default_pubsub_topic(wakuCallBack, userdata)
	time.sleep(2)

	# url_str = "enrtree://AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI@test.waku.nodes.status.im"
	# nameserver_str = ""
	# timeout = 20000
	# url = ctypes.c_char_p(url_str.encode('utf-8'))
	# nameserver = ctypes.c_char_p(nameserver_str.encode('utf-8'))
	# waku_go.waku_dns_discovery(ctx, url, nameserver, timeout, wakuCallBack, user_data)
	# time.sleep(2)

	# peer_str = "/dns4/node-01.do-ams3.waku.test.status.im/tcp/30303/p2p/16Uiu2HAkykgaECHswi3YKJ5dMLbq2kPVCo89fcyTd38UcQD6ej5W"
	# peer = ctypes.c_char_p(peer_str.encode('utf-8'))
	# ret = waku_go.waku_connect(ctx, peer, 20000, wakuCallBack, user_data)
	# print(f"connect:{ret}")
	# time.sleep(2)

	#waku_relay_subscribe(ctx, )

	# ret = waku_go.waku_peer_cnt(ctx, wakuCallBack, user_data)
	# print(f"peercnt:{ret}")

	# time.sleep(10)

if __name__ == "__main__":
	main()