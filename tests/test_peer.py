from dataclasses import dataclass
from typing import List
from dataclasses_json import dataclass_json

# Define the dataclass for the peer object
@dataclass_json
@dataclass
class Peer:
    peerID: str
    protocols: List[str]
    addrs: List[str]
    connected: bool
    pubsubTopics: List[str]

# Example JSON string (as provided)
json_string = '''[
    {"peerID": "16Uiu2HAmS6jHWtpHD3LCsH2p25st68JA1wpqgu2YjQAiWzRfJ7N1",
     "protocols": [],
     "addrs": ["/ip4/192.168.1.26/tcp/60021/p2p/16Uiu2HAmS6jHWtpHD3LCsH2p25st68JA1wpqgu2YjQAiWzRfJ7N1"],
     "connected": False,
     "pubsubTopics": []
    },
    {"peerID": "16Uiu2HAmHk5rdpnfYGDh2XchPsQxvqB3j4zb9owzfFjV7fMWbQNs",
     "protocols": ["/ipfs/id/1.0.0", "/ipfs/id/push/1.0.0", "/meshsub/1.0.0", "/floodsub/1.0.0", "/libp2p/circuit/relay/0.2.0/stop", "/vac/waku/store/2.0.0-beta4", "/ipfs/ping/1.0.0", "/vac/waku/filter-push/2.0.0-beta1", "/vac/waku/metadata/1.0.0", "/vac/waku/peer-exchange/2.0.0-alpha1", "/vac/waku/relay/2.0.0", "/libp2p/autonat/1.0.0", "/meshsub/1.1.0"],
     "addrs": ['/ip4/192.168.1.26/tcp/60020/p2p/16Uiu2HAmHk5rdpnfYGDh2XchPsQxvqB3j4zb9owzfFjV7fMWbQNs'],
     "connected": True,
     "pubsubTopics": ['/waku/2/rs/89/0']
    }
]
'''

# Parse JSON string into a list of Peer objects
peers = Peer.schema().loads(json_string, many=True)

# Example: Print the parsed objects
for peer in peers:
    print(f"Peer ID: {peer.peerID}")
    print(f"Protocols: {peer.protocols}")
    print(f"Addresses: {peer.addrs}")
    print(f"Connected: {peer.connected}")
    print(f"Pubsub Topics: {peer.pubsubTopics}")
    print("---")

# Example: Convert back to JSON
json_output = Peer.schema().dumps(peers, many=True, indent=2)
print("Serialized JSON:")
print(json_output)