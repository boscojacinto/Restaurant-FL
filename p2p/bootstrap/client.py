import os
import sys
import time
import json
import ctypes
import base64
from ctypes import CDLL

WAKU_GO_LIB = "p2p/libs/libgowaku.so.0"

HOST = "192.168.1.26"
NODE_KEY = '0cc3ac3071d6da231a1e43849afed349ed00c3b9e289147598b653eb7092c52c'
DISC_ENABLE = True

SETUP_PORT = 60010
SETUP_DISCV5_PORT = 9910
SETUP_STORE = True
SETUP_STORE_TIME = (30*24*60*60) # 30 days
SETUP_CLUSTER_ID = 88
SETUP_SHARD_ID = [0]
SETUP_STORE_DB = "sqlite3://setup_store.db"

MSG_PORT = 60020
MSG_DISCV5_PORT = 9920
MSG_STORE = True
MSG_STORE_TIME = (5*60) # 5 minutes
MSG_CLUSTER_ID = 89
MSG_SHARD_ID = [0]
MSG_STORE_DB = "sqlite3://msg_store.db"

TASTEBOT_PUBSUB_TOPIC_1 = '/waku/2/rs/88/0'
TASTEBOT_PUBSUB_TOPIC_2 = '/waku/2/rs/89/0'

WakuCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

waku_go = None
setup_content_topic = None
msg_request_topic = None 

@WakuCallBack
def wakuCallBack(ret_code, msg: str, user_data):
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

@WakuCallBack
def setupEventCallBack(ret_code, msg: str, user_data):
	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
	if ret_code != 0:
		return

	event_str = msg.decode('utf-8')
	event = json.loads(event_str)
	if event['type'] == "message":
		msgId = event['event']['messageId']
		pubsub_topic = event['event']['pubsubTopic']
		waku_message = event['event']['wakuMessage']
		print(f"messageId:{msgId}")
		if pubsub_topic == TASTEBOT_PUBSUB_TOPIC_1:
			content_topic = waku_message['contentTopic']
			payload_b64 = waku_message['payload']
			if content_topic == "/tastebot/1/customer-list/proto":
				print(f"Setup (server) -- instore")
			else:
				print(f"Other")

@WakuCallBack
def msgEventCallBack(ret_code, msg: str, user_data):
	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
	if ret_code != 0:
		return

	event_str = msg.decode('utf-8')
	event = json.loads(event_str)
	if event['type'] == "message":
		msgId = event['event']['messageId']
		pubsub_topic = event['event']['pubsubTopic']
		waku_message = event['event']['wakuMessage']
		print(f"messageId:{msgId}")
		if pubsub_topic == TASTEBOT_PUBSUB_TOPIC_2:
			content_topic = waku_message['contentTopic']
			payload_b64 = waku_message['payload']
			if content_topic == "/tastebot/1/customer-list/proto":
				print(f"Setup (server) -- instore")
			else:
				print(f"Other")

def main():

	waku_lib_init()

	(setup_ctx, setup_peer_id, setup_address) = init_setup_node()
	print(f"Started Setup node: {setup_peer_id}, {setup_address}, {TASTEBOT_PUBSUB_TOPIC_1}")

	time.sleep(2)

	(msg_ctx, msg_peer_id, msg_address) = init_msg_node()
	print(f"Started Msg node: {msg_peer_id}, {msg_address}, {TASTEBOT_PUBSUB_TOPIC_2}")

	while True:
		time.sleep(1)

def init_setup_node():
	node_config = "{ \"host\": \"%s\", \"port\": %d, \"nodeKey\": \"%s\", \"store\": %s, \"clusterID\": %d, \"shards\": [%d], \"discV5\": %s, \"databaseURL\": \"%s\", \"discV5UDPPort\": %d}" \
				   % (HOST, int(SETUP_PORT), NODE_KEY, "true" if SETUP_STORE else "false", int(SETUP_CLUSTER_ID), *map(int, SETUP_SHARD_ID), "true" if DISC_ENABLE else "false", SETUP_STORE_DB, int(SETUP_DISCV5_PORT))
	node_config = node_config.encode('ascii')

	ctx = waku_go.waku_new(node_config, wakuCallBack, None)

	ret = waku_go.waku_set_event_callback(ctx, setupEventCallBack)

	ret = waku_go.waku_start(ctx, wakuCallBack, None)

	peer_id = ctypes.c_char_p(None)
	ret = waku_go.waku_peerid(ctx, wakuCallBack, ctypes.byref(peer_id))
	peer_id = peer_id.value.decode('utf-8')

	address = ctypes.c_char_p(None)
	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, ctypes.byref(address))
	address = address.value.decode('utf-8')

	topic = get_setup_content_topic()

	subscription = "{ \"pubsubTopic\": \"%s\", \"contentTopics\":[\"%s\"]}" % (TASTEBOT_PUBSUB_TOPIC_1, topic.decode('utf-8'))
	subscription = subscription.encode('ascii')
	ret = waku_go.waku_relay_subscribe(ctx, subscription, wakuCallBack, None)

	return ctx, peer_id, address

def init_msg_node():
	node_config = "{ \"host\": \"%s\", \"port\": %d, \"nodeKey\": \"%s\", \"store\": %s, \"clusterID\": %d, \"shards\": [%d], \"discV5\": %s, \"databaseURL\": \"%s\", \"discV5UDPPort\": %d}" \
				   % (HOST, int(MSG_PORT), NODE_KEY, "true" if MSG_STORE else "false", int(MSG_CLUSTER_ID), *map(int, MSG_SHARD_ID), "true" if DISC_ENABLE else "false", MSG_STORE_DB, int(MSG_DISCV5_PORT))
	node_config = node_config.encode('ascii')

	ctx = waku_go.waku_new(node_config, wakuCallBack, None)

	ret = waku_go.waku_set_event_callback(ctx, msgEventCallBack)

	ret = waku_go.waku_start(ctx, wakuCallBack, None)

	peer_id = ctypes.c_char_p(None)
	ret = waku_go.waku_peerid(ctx, wakuCallBack, ctypes.byref(peer_id))
	peer_id = peer_id.value.decode('utf-8')

	address = ctypes.c_char_p(None)
	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, ctypes.byref(address))
	address = address.value.decode('utf-8')

	topic = get_msg_content_topic(1)
	print(f"\ntopic:{topic.decode('utf-8')}")

	subscription = "{ \"pubsubTopic\": \"%s\", \"contentTopics\":[\"%s\"]}" % (TASTEBOT_PUBSUB_TOPIC_2, topic.decode('utf-8'))
	subscription = subscription.encode('ascii')
	ret = waku_go.waku_relay_subscribe(ctx, subscription, wakuCallBack, None)

	return ctx, peer_id, address 

def get_setup_content_topic():
	app_name = ctypes.c_char_p("tastebot".encode('utf-8'))
	app_version = ctypes.c_char_p("1".encode('utf-8'))
	topic_name = ctypes.c_char_p("setup".encode('utf-8'))
	encoding = ctypes.c_char_p('proto'.encode('utf-8'))

	content_topic = ctypes.c_char_p(None)
	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
		encoding, wakuCallBack, ctypes.byref(content_topic))
	return content_topic.value

def get_msg_content_topic(timestamp):
	app_name = ctypes.c_char_p("tastebot".encode('utf-8'))
	app_version = ctypes.c_char_p("1".encode('utf-8'))
	topic_name = ctypes.c_char_p(f"msg-{timestamp}".encode('utf-8'))
	encoding = ctypes.c_char_p('proto'.encode('utf-8'))

	content_topic = ctypes.c_char_p(None)
	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
		encoding, wakuCallBack, ctypes.byref(content_topic))
	return content_topic.value

def waku_lib_init():
	global waku_go

	waku_go = CDLL(WAKU_GO_LIB)
	waku_go.waku_new.argtypes = [ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_new.restype = ctypes.c_void_p
	waku_go.waku_start.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_start.restype = ctypes.c_int
	waku_go.waku_set_event_callback.argtypes = [ctypes.c_void_p, WakuCallBack]
	waku_go.waku_peerid.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peerid.restype = ctypes.c_int
	waku_go.waku_listen_addresses.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_listen_addresses.restype = ctypes.c_int
	waku_go.waku_peers.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peers.restype = ctypes.c_int
	waku_go.waku_peer_cnt.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peer_cnt.restype = ctypes.c_int
	waku_go.waku_relay_subscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_subscribe.restype = ctypes.c_int

if __name__ == "__main__":
	main()