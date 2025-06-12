#!/bin/bash
rm -rf ./p2p/consensus/client_$1/data/tmp/* \
&& rm -rf ./p2p/consensus/client_$1/data/blockstore.db \
&& rm -rf ./p2p/consensus/client_$1/data/evidence.db	\
&& rm -rf ./p2p/consensus/client_$1/data/state.db	\
&& rm -rf ./p2p/consensus/client_$1/data/tx_index.db \
&& rm -rf ./p2p/consensus/client_$1/data/priv_validator_state.json \
&& cp -rf ./p2p/consensus/priv_validator_state.json ./p2p/consensus/client_$1/data/ \
&& rm -rf ./p2p/consensus/client_$1/data/cs.wal/wal
