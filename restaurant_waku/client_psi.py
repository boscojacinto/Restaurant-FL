import os
import sys
import time
import json
import ctypes
import base64
from ctypes import CDLL
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
import restaurant_pb2

WAKU_GO_LIB = "./libgowaku.so.0"
DISC_URL = "enrtree://AKP74RJLRUIRLPUD3KHFKX23B5LKQYSTWE4KPXZUMJQZSLG4LYMY2@nodes.restaurants.com"
DISC_NAMESERVER = "nodes.restaurants.com"
DISC_ENABLE = True

SETUP_PORT = 60011
SETUP_STORE = True
SETUP_STORE_TIME = (30*24*60*60) # 30 days
SETUP_CLUSTER_ID = 88
SETUP_SHARD_ID = 1

PSI_PORT = 60021
PSI_STORE = True
PSI_STORE_TIME = (5*60) # 5 minutes
PSI_CLUSTER_ID = 89
PSI_SHARD_ID = 1

TASTEBOT_PUBSUB_TOPIC = '/tastbot/1/customer-intersect/proto'

WakuCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

waku_go = None
setup_content_topic = None
psi_request_topic = None 

class PSIClient:
    def __init__(self, setup_bs_enr, psi_bs_enr, node_key, host):
    	self.setup_bs_enr = setup_bs_enr
    	self.psi_bs_enr = psi_bs_enr
    	self.node_key = node_key
    	self.host = host
    	waku_lib_init()

    def start(self):
    	(setup_ctx, setup_connected, setup_peer_id,
    		setup_address, setup_content_topic) = self.init_setup_node()
    	print(f"Started PSI node: {setup_peer_id}, {setup_address}, {setup_content_topic}")

    	(psi_ctx, psi_connected, psi_peer_id,
    		psi_address, psi_content_topic) = self.init_psi_node()
    	print(f"Started PSI node: {psi_peer_id}, {psi_address}, {psi_content_topic}")

    def init_setup_node(self):
    	node_config = "{ \"host\": \"%s\", \"port\": %d, \"nodeKey\": \"%s\", \"store\": %s, \"clusterID\": %d, \"shards\": [%d], \"discV5BootstrapNodes\": [\"%s\"]}" \
    					% (self.host, int(SETUP_PORT), self.node_key, "true" if SETUP_STORE else "false", int(SETUP_CLUSTER_ID), int(SETUP_SHARD_ID), self.setup_bs_enr)
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

    	peers_list = ctypes.c_char_p(None)
    	waku_go.waku_peers(ctx, wakuCallBack, ctypes.byref(peers_list))
    	print(f"peers_list:{peers_list.value}")

    	peer_str = "/ip4/192.168.1.26/tcp/60010/p2p/16Uiu2HAmHk5rdpnfYGDh2XchPsQxvqB3j4zb9owzfFjV7fMWbQNs"
    	peer = ctypes.c_char_p(peer_str.encode('utf-8'))
    	connected = waku_go.waku_connect(ctx, peer, 20000, wakuCallBack, None)

    	topic = self.get_setup_content_topic()

    	subscription = "{ \"pubsubTopic\": \"%s\", \"contentTopics\":[\"%s\"]}" % (TASTEBOT_PUBSUB_TOPIC, topic.decode('utf-8'))
    	subscription = subscription.encode('ascii')
    	ret = waku_go.waku_relay_subscribe(ctx, subscription, wakuCallBack, None)

    	return ctx, connected, peer_id, address, topic

    def init_psi_node(self):
    	node_config = "{ \"host\": \"%s\", \"port\": %d, \"nodeKey\": \"%s\", \"store\": %s, \"clusterID\": %d, \"shards\": [%d], \"discV5BootstrapNodes\": [\"%s\"]}" \
    					% (self.host, int(PSI_PORT), self.node_key, "true" if PSI_STORE else "false", int(PSI_CLUSTER_ID), int(PSI_SHARD_ID), self.psi_bs_enr)

    	node_config = node_config.encode('ascii')

    	ctx = waku_go.waku_new(node_config, wakuCallBack, None)

    	ret = waku_go.waku_set_event_callback(ctx, psiEventCallBack)

    	ret = waku_go.waku_start(ctx, wakuCallBack, None)

    	peer_id = ctypes.c_char_p(None)
    	ret = waku_go.waku_peerid(ctx, wakuCallBack, ctypes.byref(peer_id))
    	peer_id = peer_id.value.decode('utf-8')

    	address = ctypes.c_char_p(None)
    	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, ctypes.byref(address))
    	address = address.value.decode('utf-8')

    	peer_str = "/ip4/192.168.1.26/tcp/60020/p2p/16Uiu2HAm4vuRBjEzZ82WP44gbY6B1qBvPPun5r2eWBfe4EhmYTFQ"
    	peer = ctypes.c_char_p(peer_str.encode('utf-8'))
    	connected = waku_go.waku_connect(ctx, peer, 20000, wakuCallBack, None)

    	current_time = datetime.now().strftime("%H:%M:%S")	
    	topic = self.get_psi_content_topic(current_time)

    	subscription = "{ \"pubsubTopic\": \"%s\", \"contentTopics\":[\"%s\"]}" % (TASTEBOT_PUBSUB_TOPIC, topic.decode('utf-8'))
    	subscription = subscription.encode('ascii')
    	ret = waku_go.waku_relay_subscribe(ctx, subscription, wakuCallBack, None)

    	return ctx, connected, peer_id, address, topic 

    def get_setup_content_topic(self):
    	app_name = ctypes.c_char_p("tastebot".encode('utf-8'))
    	app_version = ctypes.c_char_p("1".encode('utf-8'))
    	topic_name = ctypes.c_char_p("setup".encode('utf-8'))
    	encoding = ctypes.c_char_p('proto'.encode('utf-8'))

    	content_topic = ctypes.c_char_p(None)
    	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
    		encoding, wakuCallBack, ctypes.byref(content_topic))
    	return content_topic.value

    def get_psi_content_topic(self, timestamp):
    	app_name = ctypes.c_char_p("tastebot".encode('utf-8'))
    	app_version = ctypes.c_char_p("1".encode('utf-8'))
    	topic_name = ctypes.c_char_p(f"psi-{timestamp}".encode('utf-8'))
    	encoding = ctypes.c_char_p('proto'.encode('utf-8'))

    	content_topic = ctypes.c_char_p(None)
    	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
    		encoding, wakuCallBack, ctypes.byref(content_topic))
    	return content_topic.value

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
		if pubsub_topic == TASTEBOT_PUBSUB_TOPIC:
			content_topic = waku_message['contentTopic']
			payload_b64 = waku_message['payload']
			if content_topic == "/tastebot/1/customer-list/proto":
				print(f"Setup (server) -- instore")
			else:
				print(f"Other")

@WakuCallBack
def psiEventCallBack(ret_code, msg: str, user_data):
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
		if pubsub_topic == TASTEBOT_PUBSUB_TOPIC:
			content_topic = waku_message['contentTopic']
			payload_b64 = waku_message['payload']
			if content_topic == "/tastebot/1/customer-list/proto":
				print(f"Setup (server) -- instore")
			else:
				print(f"Other")

def waku_lib_init():
	global waku_go

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
	waku_go.waku_peers.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peers.restype = ctypes.c_int
	waku_go.waku_peer_cnt.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peer_cnt.restype = ctypes.c_int
	waku_go.waku_relay_subscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_subscribe.restype = ctypes.c_int
	waku_go.waku_set_event_callback.argtypes = [ctypes.c_void_p, WakuCallBack]
	waku_go.waku_relay_topics.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_topics.restype = ctypes.c_int
	waku_go.waku_store_local_query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_store_local_query.restype = ctypes.c_int

if __name__ == "__main__":
	setup_bs_enr = "-Jq4QJfs2uKrvjdhRyuHfB8JxBv-AxzXLAKIwJOoaz9k0sb_ZWLB0sKQJaqHYyAucAoUD3P36q8BRPitOvutyZpj7u2GAZb3wmK0gmlkgnY0gmlwhMCoARqCcnOFAFgBAAGJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6mqFd2FrdTID"
	psi_bs_enr = "-Jq4QCeXiHyMKcbWSA5F-NWp4PiHDMcfukz3irHoIwKMePJzJwOKSrB1IwGeHWFL7mIr5kwGuvYcqwcovcEeeqbq3VyGAZb3wmq3gmlkgnY0gmlwhMCoARqCcnOFAFkBAAGJc2VjcDI1NmsxoQKNNjhPvRAVb8pSV4ssOmKJ7xncEJn69ztPqazHXT01Q4N0Y3CC6nSFd2FrdTID"
	node_key = '4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5'
	host = "192.168.1.26"
	client = PSIClient(setup_bs_enr, psi_bs_enr, node_key, host)
	client.start()
