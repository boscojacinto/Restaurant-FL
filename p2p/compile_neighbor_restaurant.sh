#!/bin/bash
python3 -m grpc_tools.protoc -I../venv/lib/python3.12/site-packages/private_set_intersection/proto/ -I. --python_out=. --grpc_python_out=. psi.proto restaurant.proto && cp psi_pb2.py ../venv/lib/python3.12/site-packages/private_set_intersection/proto/psi_python_proto_pb/private_set_intersection/proto/ &&
mv psi_pb2.py ../venv/lib/python3.12/site-packages/private_set_intersection/proto/psi_python_proto_pb/private_set_intersection/proto/
 