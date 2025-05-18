import os
import sys
import json
import ctypes
import time
from ctypes import CDLL
import base64
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
import restaurant_pb2

WAKU_GO_LIB = "./libgowaku.so.0"
HOST = "192.168.1.26"
PORT = 0
IS_STORE = True
CLUSTER_ID = 89
SHARD_ID = 1
SIGNING_KEY = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef' #TODO: change later
PEER_ID = "16Uiu2HAkxY2C8d1ycecQnBZqXcuSo2V8rUBsioEwHvA6cZ8JFXXJ"
PEER_PORT = "45365"

WakuCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

received_ephemeral_msg = False

def main():
	@WakuCallBack
	def wakuCallBack(ret_code, msg: str, user_data):
		if ret_code != 0:
			print(f"Error: {ret}, msg:{msg}")

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
		print(f"user_data:{user_data}")
		if ret_code != 0:
			print(f"Error: {ret_code}")
			print(f"\nEvent: {msg}")
			return
			#parse waku message header for type("message") and
			# content topic and the parse payload for our 
			# PSI messages

		print(f"msg:{msg}")
		event_str = msg.decode('utf-8')
		print(f"event_str:{event_str}")
		event = json.loads(event_str)
		print(f"event:{event}")
		if event['type'] == "message":
			msgId = event['event']['messageId']
			pubsub_topic = event['event']['pubsubTopic']
			waku_message = event['event']['wakuMessage']
			print(f"messageId:{msgId}")
			if pubsub_topic == "/tastbot/1/neighbor-1/proto":
				content_topic = waku_message['contentTopic']
				payload_b64 = waku_message['payload']
				if content_topic == "/tastebot/1/customer-list/proto":
					global received_ephemeral_msg
					print(f"Setup (server) -- instore")

					received_ephemeral_msg = True
					print(f"payload:{waku_message['payload']}")
					# payload_bytes = base64.b64decode(payload_b64)
					# print(f"payload_bytes:{payload_bytes}")
					# waku_message_ptr = ctypes.c_char_p(payload_bytes)
				else:
					print(f"Other")

	
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
	waku_go.waku_relay_topics.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_topics.restype = ctypes.c_int
	waku_go.waku_store_local_query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_store_local_query.restype = ctypes.c_int

	json_config = "{ \"host\": \"%s\", \"port\": %d, \"store\": %s, \"clusterID\": %d, \"shards\": [%d]}" % (HOST, int(PORT), "true" if IS_STORE else "false", int(CLUSTER_ID), int(SHARD_ID))
	#json_config = "{ \"host\": \"%s\", \"port\": %d, \"store\": %s}" % (HOST, int(PORT), "true" if IS_STORE else "false")
	json_config = json_config.encode('ascii')

	ctx = waku_go.waku_new(json_config, wakuCallBack, None)
	print(f"CTX:{ctx}")
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

	peer_str = f"/ip4/192.168.1.26/tcp/{PEER_PORT}/p2p/{PEER_ID}"
	peer = ctypes.c_char_p(peer_str.encode('utf-8'))
	ret = waku_go.waku_connect(ctx, peer, 20000, wakuCallBack, None)
	print(f"connect:{ret}")
	time.sleep(2)

	default_pubsub_topic = ctypes.c_char_p(None)
	waku_go.waku_default_pubsub_topic(wakuCallBack, ctypes.byref(default_pubsub_topic))
	print(f"default_pubsub_topic:{default_pubsub_topic.value}")

	pubsub_topic = '/tastbot/1/neighbor-1/proto'
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

	subscription = "{ \"pubsubTopic\": \"%s\", \"contentTopics\":[\"%s\"]}" % (pubsub_topic, content_topic.value.decode('utf-8'))
	subscription = subscription.encode('ascii')
	print(f"subscription:{subscription}")

	ret = waku_go.waku_relay_subscribe(ctx, subscription, wakuCallBack, None)
	print(f"ret:{ret}")
	time.sleep(2)

	stopics = ctypes.c_char_p(None)
	waku_go.waku_relay_topics(ctx, wakuCallBack, ctypes.byref(stopics))
	print(f"stopics:{stopics.value}")
	time.sleep(10)

	# ret = waku_go.waku_peer_cnt(ctx, wakuCallBack, user_data)
	# print(f"peercnt:{ret}")

	store_query = '{ "pubsubTopic": "%s", "pagingOptions": {"pageSize": 40, "forward":false}}' % pubsub_topic
	#store_query = "{ \"pubsubTopic\": \"%s\"}" % (pubsub_topic)
	#store_query = store_query.encode('utf-8')
	store_query_ptr = ctypes.c_char_p(store_query.encode('utf-8'))
	print(f"\nstore_query_ptr:{store_query_ptr}")

	# local_store = ctypes.c_char_p(None)
	# print(f"ctx:{ctx}") 
	# ret = waku_go.waku_store_local_query(ctx, store_query_ptr, wakuCallBack, ctypes.byref(local_store))
	# print(f"RET:{ret}")
	# print(f"local_store:{local_store.value}")

	peer_ptr = ctypes.c_char_p(PEER_ID.encode('utf-8'))
	peer_store = ctypes.c_char_p(None)
	print(f"ctx:{ctx}") 
	ret = waku_go.waku_store_query(ctx, store_query_ptr, peer_ptr, 20000, wakuCallBack, ctypes.byref(peer_store))
	print(f"RET:{ret}")
	print(f"peer_store:{peer_store.value}")


	while True:
		time.sleep(1)
if __name__ == "__main__":
	main()