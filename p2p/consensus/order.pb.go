// Code generated by protoc-gen-go. DO NOT EDIT.
// versions:
// 	protoc-gen-go v1.36.6
// 	protoc        v3.21.12
// source: order.proto

package main

import (
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	reflect "reflect"
	sync "sync"
	unsafe "unsafe"
)

const (
	// Verify that this generated code is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(20 - protoimpl.MinVersion)
	// Verify that runtime/protoimpl is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(protoimpl.MaxVersion - 20)
)

type Proof struct {
	state         protoimpl.MessageState `protogen:"open.v1"`
	Buf           []byte                 `protobuf:"bytes,1,opt,name=buf,proto3" json:"buf,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *Proof) Reset() {
	*x = Proof{}
	mi := &file_order_proto_msgTypes[0]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *Proof) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*Proof) ProtoMessage() {}

func (x *Proof) ProtoReflect() protoreflect.Message {
	mi := &file_order_proto_msgTypes[0]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use Proof.ProtoReflect.Descriptor instead.
func (*Proof) Descriptor() ([]byte, []int) {
	return file_order_proto_rawDescGZIP(), []int{0}
}

func (x *Proof) GetBuf() []byte {
	if x != nil {
		return x.Buf
	}
	return nil
}

type Timestamp struct {
	state         protoimpl.MessageState `protogen:"open.v1"`
	Now           string                 `protobuf:"bytes,1,opt,name=now,proto3" json:"now,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *Timestamp) Reset() {
	*x = Timestamp{}
	mi := &file_order_proto_msgTypes[1]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *Timestamp) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*Timestamp) ProtoMessage() {}

func (x *Timestamp) ProtoReflect() protoreflect.Message {
	mi := &file_order_proto_msgTypes[1]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use Timestamp.ProtoReflect.Descriptor instead.
func (*Timestamp) Descriptor() ([]byte, []int) {
	return file_order_proto_rawDescGZIP(), []int{1}
}

func (x *Timestamp) GetNow() string {
	if x != nil {
		return x.Now
	}
	return ""
}

type Identity struct {
	state         protoimpl.MessageState `protogen:"open.v1"`
	ID            string                 `protobuf:"bytes,1,opt,name=ID,proto3" json:"ID,omitempty"`
	ENR           *string                `protobuf:"bytes,2,opt,name=ENR,proto3,oneof" json:"ENR,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *Identity) Reset() {
	*x = Identity{}
	mi := &file_order_proto_msgTypes[2]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *Identity) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*Identity) ProtoMessage() {}

func (x *Identity) ProtoReflect() protoreflect.Message {
	mi := &file_order_proto_msgTypes[2]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use Identity.ProtoReflect.Descriptor instead.
func (*Identity) Descriptor() ([]byte, []int) {
	return file_order_proto_rawDescGZIP(), []int{2}
}

func (x *Identity) GetID() string {
	if x != nil {
		return x.ID
	}
	return ""
}

func (x *Identity) GetENR() string {
	if x != nil && x.ENR != nil {
		return *x.ENR
	}
	return ""
}

type IdlePeers struct {
	state         protoimpl.MessageState `protogen:"open.v1"`
	Url           string                 `protobuf:"bytes,1,opt,name=url,proto3" json:"url,omitempty"`
	SubDomain     []string               `protobuf:"bytes,2,rep,name=subDomain,proto3" json:"subDomain,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *IdlePeers) Reset() {
	*x = IdlePeers{}
	mi := &file_order_proto_msgTypes[3]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *IdlePeers) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*IdlePeers) ProtoMessage() {}

func (x *IdlePeers) ProtoReflect() protoreflect.Message {
	mi := &file_order_proto_msgTypes[3]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use IdlePeers.ProtoReflect.Descriptor instead.
func (*IdlePeers) Descriptor() ([]byte, []int) {
	return file_order_proto_rawDescGZIP(), []int{3}
}

func (x *IdlePeers) GetUrl() string {
	if x != nil {
		return x.Url
	}
	return ""
}

func (x *IdlePeers) GetSubDomain() []string {
	if x != nil {
		return x.SubDomain
	}
	return nil
}

type OrderRequest struct {
	state         protoimpl.MessageState `protogen:"open.v1"`
	Proof         *Proof                 `protobuf:"bytes,1,opt,name=proof,proto3" json:"proof,omitempty"`
	Timestamp     *Timestamp             `protobuf:"bytes,2,opt,name=timestamp,proto3" json:"timestamp,omitempty"`
	Identity      *Identity              `protobuf:"bytes,3,opt,name=identity,proto3" json:"identity,omitempty"`
	IdlePeers     *IdlePeers             `protobuf:"bytes,4,opt,name=idlePeers,proto3,oneof" json:"idlePeers,omitempty"`
	unknownFields protoimpl.UnknownFields
	sizeCache     protoimpl.SizeCache
}

func (x *OrderRequest) Reset() {
	*x = OrderRequest{}
	mi := &file_order_proto_msgTypes[4]
	ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
	ms.StoreMessageInfo(mi)
}

func (x *OrderRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*OrderRequest) ProtoMessage() {}

func (x *OrderRequest) ProtoReflect() protoreflect.Message {
	mi := &file_order_proto_msgTypes[4]
	if x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use OrderRequest.ProtoReflect.Descriptor instead.
func (*OrderRequest) Descriptor() ([]byte, []int) {
	return file_order_proto_rawDescGZIP(), []int{4}
}

func (x *OrderRequest) GetProof() *Proof {
	if x != nil {
		return x.Proof
	}
	return nil
}

func (x *OrderRequest) GetTimestamp() *Timestamp {
	if x != nil {
		return x.Timestamp
	}
	return nil
}

func (x *OrderRequest) GetIdentity() *Identity {
	if x != nil {
		return x.Identity
	}
	return nil
}

func (x *OrderRequest) GetIdlePeers() *IdlePeers {
	if x != nil {
		return x.IdlePeers
	}
	return nil
}

var File_order_proto protoreflect.FileDescriptor

const file_order_proto_rawDesc = "" +
	"\n" +
	"\vorder.proto\x12\x04main\"\x19\n" +
	"\x05Proof\x12\x10\n" +
	"\x03buf\x18\x01 \x01(\fR\x03buf\"\x1d\n" +
	"\tTimestamp\x12\x10\n" +
	"\x03now\x18\x01 \x01(\tR\x03now\"9\n" +
	"\bIdentity\x12\x0e\n" +
	"\x02ID\x18\x01 \x01(\tR\x02ID\x12\x15\n" +
	"\x03ENR\x18\x02 \x01(\tH\x00R\x03ENR\x88\x01\x01B\x06\n" +
	"\x04_ENR\";\n" +
	"\tIdlePeers\x12\x10\n" +
	"\x03url\x18\x01 \x01(\tR\x03url\x12\x1c\n" +
	"\tsubDomain\x18\x02 \x03(\tR\tsubDomain\"\xce\x01\n" +
	"\fOrderRequest\x12!\n" +
	"\x05proof\x18\x01 \x01(\v2\v.main.ProofR\x05proof\x12-\n" +
	"\ttimestamp\x18\x02 \x01(\v2\x0f.main.TimestampR\ttimestamp\x12*\n" +
	"\bidentity\x18\x03 \x01(\v2\x0e.main.IdentityR\bidentity\x122\n" +
	"\tidlePeers\x18\x04 \x01(\v2\x0f.main.IdlePeersH\x00R\tidlePeers\x88\x01\x01B\f\n" +
	"\n" +
	"_idlePeersB\tZ\a./;mainb\x06proto3"

var (
	file_order_proto_rawDescOnce sync.Once
	file_order_proto_rawDescData []byte
)

func file_order_proto_rawDescGZIP() []byte {
	file_order_proto_rawDescOnce.Do(func() {
		file_order_proto_rawDescData = protoimpl.X.CompressGZIP(unsafe.Slice(unsafe.StringData(file_order_proto_rawDesc), len(file_order_proto_rawDesc)))
	})
	return file_order_proto_rawDescData
}

var file_order_proto_msgTypes = make([]protoimpl.MessageInfo, 5)
var file_order_proto_goTypes = []any{
	(*Proof)(nil),        // 0: main.Proof
	(*Timestamp)(nil),    // 1: main.Timestamp
	(*Identity)(nil),     // 2: main.Identity
	(*IdlePeers)(nil),    // 3: main.IdlePeers
	(*OrderRequest)(nil), // 4: main.OrderRequest
}
var file_order_proto_depIdxs = []int32{
	0, // 0: main.OrderRequest.proof:type_name -> main.Proof
	1, // 1: main.OrderRequest.timestamp:type_name -> main.Timestamp
	2, // 2: main.OrderRequest.identity:type_name -> main.Identity
	3, // 3: main.OrderRequest.idlePeers:type_name -> main.IdlePeers
	4, // [4:4] is the sub-list for method output_type
	4, // [4:4] is the sub-list for method input_type
	4, // [4:4] is the sub-list for extension type_name
	4, // [4:4] is the sub-list for extension extendee
	0, // [0:4] is the sub-list for field type_name
}

func init() { file_order_proto_init() }
func file_order_proto_init() {
	if File_order_proto != nil {
		return
	}
	file_order_proto_msgTypes[2].OneofWrappers = []any{}
	file_order_proto_msgTypes[4].OneofWrappers = []any{}
	type x struct{}
	out := protoimpl.TypeBuilder{
		File: protoimpl.DescBuilder{
			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
			RawDescriptor: unsafe.Slice(unsafe.StringData(file_order_proto_rawDesc), len(file_order_proto_rawDesc)),
			NumEnums:      0,
			NumMessages:   5,
			NumExtensions: 0,
			NumServices:   0,
		},
		GoTypes:           file_order_proto_goTypes,
		DependencyIndexes: file_order_proto_depIdxs,
		MessageInfos:      file_order_proto_msgTypes,
	}.Build()
	File_order_proto = out.File
	file_order_proto_goTypes = nil
	file_order_proto_depIdxs = nil
}
