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

config_obj = {"host": "0.0.0.0", "port": "0", "logLevel": "error", "store": "true", "ClusterID": "1"}
config = json.dumps(config_obj)
config_bytes = config.encode('utf-8')
configuration = ctypes.c_char_p(config_bytes)

def main():
	@WakuCallBack
	def wakuCallBack(ret_code, msg: str, user_data):
		if ret_code != 0:
			print(f"Error: {ret}")

		if not user_data:
			print("user data is null")
			return

		data_ref = ctypes.cast(user_data, ctypes.POINTER(ctypes.c_char_p))
		data_ptr = data_ref[0]

		# if data_ref.contents:
		# 	libc.free(data_ref.contents)
		# 	data_ref.contents = None

		if msg:
			msg_str = msg.decode('utf-8')
			msg_len = len(msg_str)

			msg_ptr = ctypes.create_string_buffer(msg_len)

			if not msg_ptr:
				return

			ctypes.memmove(msg_ptr, msg_str.encode(), msg_len)

			data_ref[0] = ctypes.cast(msg_ptr, ctypes.c_char_p)
			data_ptr = data_ref[0]
	
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
	waku_go.waku_relay_subscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_subscribe.restype = ctypes.c_int

	ctx = waku_go.waku_new(None, configuration, wakuCallBack, None)
	time.sleep(2)

	ret = waku_go.waku_start(ctx, wakuCallBack, None)
	print(f"start:{ret}")
	time.sleep(2)

	peer_id = ctypes.c_char_p(None)
	ret = waku_go.waku_peerid(ctx, wakuCallBack, ctypes.byref(peer_id))
	print(f"peerid:{peer_id.value}")
	time.sleep(2)

	addresses = ctypes.c_char_p(None)
	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, ctypes.byref(addresses))
	print(f"addresses:{addresses.value}")
	time.sleep(2)

	app_name_str = "example"
	app_version_str = "1"
	topic_name_str = "default"
	encoding_str = "rfc26"
	app_name = ctypes.c_char_p(app_name_str.encode('utf-8'))
	app_version = ctypes.c_char_p(app_version_str.encode('utf-8'))
	topic_name = ctypes.c_char_p(topic_name_str.encode('utf-8'))
	encoding = ctypes.c_char_p(encoding_str.encode('utf-8'))

	content_topic = ctypes.c_char_p(None)
	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
									 encoding, wakuCallBack, ctypes.byref(content_topic))
	print(f"content topic:{content_topic.value}")
	time.sleep(2)

	default_pubsub_topic = ctypes.c_char_p(None)
	ret = waku_go.waku_default_pubsub_topic(wakuCallBack, ctypes.byref(default_pubsub_topic))
	time.sleep(2)
	print(f"default_pubsub_topic:{default_pubsub_topic.value}")

	# url_str = "enrtree://AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI@test.waku.nodes.status.im"
	# nameserver_str = ""
	# timeout = 20000
	# url = ctypes.c_char_p(url_str.encode('utf-8'))
	# nameserver = ctypes.c_char_p(nameserver_str.encode('utf-8'))

	# discovered_nodes = ctypes.c_char_p(None)
	# waku_go.waku_dns_discovery(ctx, url, nameserver, timeout, wakuCallBack, ctypes.byref(discovered_nodes))
	# print(f"discovered_nodes:{discovered_nodes.value}")
	# time.sleep(2)

	#peer_str = "/dns4/node-01.do-ams3.waku.test.status.im/tcp/30303/p2p/16Uiu2HAkykgaECHswi3YKJ5dMLbq2kPVCo89fcyTd38UcQD6ej5W"
	peer_str = "/dns4/node-01.gc-us-central1-a.waku.test.status.im/tcp/30303/p2p/16Uiu2HAmDCp8XJ9z1ev18zuv8NHekAsjNyezAvmMfFEJkiharitG"
	peer = ctypes.c_char_p(peer_str.encode('utf-8'))
	ret = waku_go.waku_connect(ctx, peer, 20000, wakuCallBack, None)
	print(f"connect:{ret}")

	# topic = default_pubsub_topic.value.decode('utf-8')
	# content = content_topic.value.decode('utf-8')
	# print(f"topic:{topic}, content:{content}")

	# content_filter_obj = {"pubsubTopic": topic, "contentTopics": [content]}
	# print(f"content_filter_obj:{content_filter_obj}")

	# content_filter_str = json.dumps(content_filter_obj)
	# print(f"content_filter_str:{content_filter_str}")

	# content_filter_bytes = content_filter_str.encode('utf-8')
	# print(f"content_filter_bytes:{content_filter_bytes}")

	# content_filter = ctypes.c_char_p(content_filter_bytes)

	# ret = waku_go.waku_relay_subscribe(ctx, content_filter, wakuCallBack, None)
	# print(f"ret:{ret}")

	# ret = waku_go.waku_peer_cnt(ctx, wakuCallBack, user_data)
	# print(f"peercnt:{ret}")

	# time.sleep(10)

if __name__ == "__main__":
	main()