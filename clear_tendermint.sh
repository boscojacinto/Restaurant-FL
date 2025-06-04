#!/bin/bash
rm -rf ./p2p/consensus/config && rm -rf ./p2p/consensus/data \
&& cp -rf $HOME/.tendermint/config ./p2p/consensus/ \
&& cp -rf $HOME/.tendermint/data ./p2p/consensus/ \
&& chown -R boscojacinto:boscojacinto ./p2p/consensus/config \
&& chown -R boscojacinto:boscojacinto ./p2p/consensus/data \
&& mkdir ./p2p/consensus/config/tmp \
&& chown -R boscojacinto:boscojacinto ./p2p/consensus/config/tmp