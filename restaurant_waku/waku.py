import json
import ctypes
import time
from ctypes import CDLL

WAKU_GO_LIB = "./libgowaku.so.0"
HOST = "192.168.1.26"
PORT = 0
IS_STORE = True

WakuCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

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

	@WakuCallBack
	def eventCallBack(ret_code, msg: str, user_data):
		if ret_code != 0:
			print(f"Error: {ret_code}")
			print(f"\nEvent: {msg}")
			#parse waku message header for type("message") and
			# content topic and the parse payload for our 
			# PSI messages			
	
	waku_go = CDLL(WAKU_GO_LIB)
	waku_go.waku_new.argtypes = [ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
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
	waku_go.waku_set_event_callback.argtypes = [ctypes.c_void_p, WakuCallBack]

	json_config = "{ \"host\": \"%s\", \"port\": %d, \"store\": %s}" % (HOST, int(PORT), "true" if IS_STORE else "false")
	json_config = json_config.encode('ascii')

	ctx = waku_go.waku_new(json_config, wakuCallBack, None)
	time.sleep(2)

	ret = waku_go.waku_set_event_callback(ctx, eventCallBack)
	print(f"setcallback:{ret}")

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

	pubsub_topic = '/tastbot/1/neighbor/proto'
	app_name_str = "tastebot"
	app_version_str = "1"
	topic_name_str = "customer-list"
	encoding_str = "proto"
	app_name = ctypes.c_char_p(app_name_str.encode('utf-8'))
	app_version = ctypes.c_char_p(app_version_str.encode('utf-8'))
	topic_name = ctypes.c_char_p(topic_name_str.encode('utf-8'))
	encoding = ctypes.c_char_p(encoding_str.encode('utf-8'))

	content_topic = ctypes.c_char_p(None)
	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
									 encoding, wakuCallBack, ctypes.byref(content_topic))
	print(f"content topic:{content_topic.value}")
	time.sleep(2)

	subscription = "{ \"pubsubTopic\": \"%s\", \"contentTopics\": [\"%s\"]}" % (pubsub_topic, content_topic.value.decode('utf-8'))
	subscription = subscription.encode('ascii')
	print(f"subscription:{subscription}")

	ret = waku_go.waku_relay_subscribe(ctx, subscription, wakuCallBack, None)
	print(f"ret:{ret}")

	# ret = waku_go.waku_peer_cnt(ctx, wakuCallBack, user_data)
	# print(f"peercnt:{ret}")

	while True:
		time.sleep(1)

if __name__ == "__main__":
	main()