#!/bin/bash
rm -rf ./p2p/consensus/config_$1/* && rm -rf ./p2p/consensus/data_$1/* \
&& cp -rf $HOME/.tendermint/config/* ./p2p/consensus/config_$1/ \
&& cp -rf $HOME/.tendermint/data/* ./p2p/consensus/data_$1/ \
&& chown -R boscojacinto:boscojacinto ./p2p/consensus/config_$1 \
&& chown -R boscojacinto:boscojacinto ./p2p/consensus/data_$1 \
&& mkdir ./p2p/consensus/data_$1/tmp \
&& chown -R boscojacinto:boscojacinto ./p2p/consensus/data_$1/tmp