package main

import (
	"fmt"
	"bytes"
	"golang.org/x/crypto/sha3"
	"github.com/dgraph-io/badger"
	"google.golang.org/protobuf/proto"
	abcitypes "github.com/tendermint/tendermint/abci/types"
)

const AppVersion = 1
const PUBLIC_KEY = "4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5"

type InferSyncApp struct {
	db *badger.DB
	currentBatch *badger.Txn
}

var _ abcitypes.Application = (*InferSyncApp)(nil)
var localOrderFound = false

func NewInferSyncApp(db *badger.DB) *InferSyncApp {
	return &InferSyncApp{
		db: db,
	}
}

func (InferSyncApp) Info(req abcitypes.RequestInfo) abcitypes.ResponseInfo {
	return abcitypes.ResponseInfo{
		Version: Version,
		AppVersion: AppVersion,
	}
}

func (InferSyncApp) SetOption(req abcitypes.RequestSetOption) abcitypes.ResponseSetOption {
	return abcitypes.ResponseSetOption{}
}

func (app *InferSyncApp) CheckTx(req abcitypes.RequestCheckTx) abcitypes.ResponseCheckTx {
	code := uint32(0)
	
	_, valid := app.isValid(req.Tx)
	if valid == false {
		code = uint32(3)
	}

	return abcitypes.ResponseCheckTx{Code: code, Codespace: "sync", GasWanted: 1}
}

func (app *InferSyncApp) DeliverTx(req abcitypes.RequestDeliverTx) abcitypes.ResponseDeliverTx {

	syncReq, valid := app.isValid(req.Tx)
	if valid == false {
		return abcitypes.ResponseDeliverTx{Code: 3, Codespace: "sync"}
	}

	var key []byte
	var value []byte

	switch syncReq.Type.(type) {
		case *SyncRequest_Order: {
			fmt.Println("DeliverTX:SyncRequest_Order")
			
			// Check if order proof belongs to us
			if matchOrder(syncReq) {				
				key, value = makeOrderKV(syncReq.GetOrder())
				valid = true
			}
		}

		case *SyncRequest_Dummy: {
			fmt.Println("DeliverTX:SyncRequest_Dummy")			
		}

		default: {
			fmt.Println("DeliverTX:default")			
		}	
	}

	if valid {
		err := app.currentBatch.Set(key, value)
		fmt.Println("Added key")
		if err != nil {
			panic(err)
		}		
	}

	return abcitypes.ResponseDeliverTx{Code: 0, Codespace: "sync"}
}

func (app *InferSyncApp) Commit() abcitypes.ResponseCommit {
	app.currentBatch.Commit()
	return abcitypes.ResponseCommit{Data: []byte{}}
}

func (app *InferSyncApp) Query(reqQuery abcitypes.RequestQuery) (resQuery abcitypes.ResponseQuery) {
	resQuery.Key = reqQuery.Data
	err := app.db.View(func(txn *badger.Txn) error {
		item, err := txn.Get(reqQuery.Data)
		if err != nil && err != badger.ErrKeyNotFound {
			return err
		}
		if err == badger.ErrKeyNotFound {
			resQuery.Log = "does not exist"
		} else {
			return item.Value(func(val []byte) error {
				resQuery.Log = "exists"
				resQuery.Value = val
				return nil
			})
		}
		return nil
	})
	if err != nil {
		panic(err)
	}
	return
}

func (InferSyncApp) InitChain(req abcitypes.RequestInitChain) abcitypes.ResponseInitChain {
	return abcitypes.ResponseInitChain{}
}

func (app *InferSyncApp) BeginBlock(req abcitypes.RequestBeginBlock) abcitypes.ResponseBeginBlock {
	app.currentBatch = app.db.NewTransaction(true)
	return abcitypes.ResponseBeginBlock{}
}

func (InferSyncApp) EndBlock(req abcitypes.RequestEndBlock) abcitypes.ResponseEndBlock {
	return abcitypes.ResponseEndBlock{}
}

func (InferSyncApp) ListSnapshots(abcitypes.RequestListSnapshots) abcitypes.ResponseListSnapshots {
	return abcitypes.ResponseListSnapshots{}
}

func (InferSyncApp) OfferSnapshot(abcitypes.RequestOfferSnapshot) abcitypes.ResponseOfferSnapshot {
	return abcitypes.ResponseOfferSnapshot{}
}

func (InferSyncApp) LoadSnapshotChunk(abcitypes.RequestLoadSnapshotChunk) abcitypes.ResponseLoadSnapshotChunk {
	return abcitypes.ResponseLoadSnapshotChunk{}
}

func (InferSyncApp) ApplySnapshotChunk(abcitypes.RequestApplySnapshotChunk) abcitypes.ResponseApplySnapshotChunk {
	return abcitypes.ResponseApplySnapshotChunk{}
}

func matchOrder(req *SyncRequest) (bool) {

	// Match identity
	order := req.GetOrder()
	identity := order.GetIdentity()
	publicKey := identity.GetPublicKey()

	if publicKey == PUBLIC_KEY {
		fmt.Println("\nMatch")
		localOrderFound = true
	}

	return true
}

func verifyOrder(req *OrderRequest) (bool) {
	proof := req.GetProof()
	
	proof=proof
	// Verify proof

	return true
}

func makeOrderKV(req *OrderRequest) ([]byte, []byte) {
	proof := req.GetProof()
	keccak := sha3.NewLegacyKeccak256()
	keccak.Write(proof.GetBuf())
	hash := fmt.Sprintf("%x", keccak.Sum(nil))
	fmt.Println("Order Hash:", hash)
	
	k := []byte("order")
	v := []byte(hash)
	return k, v
}

func (app *InferSyncApp) isValid(tx []byte) (req *SyncRequest, valid bool) {
	
	valid = false
	var key []byte
	var value []byte

	req = &SyncRequest{}

	if err := proto.Unmarshal(tx, req); err != nil {
		panic(err)
	}

    switch d := req.Type.(type) {
	    case *SyncRequest_Order:{
	    	fmt.Printf("Order:%s\n", d.Order)
			if verifyOrder(req.GetOrder()) {
				key, value = makeOrderKV(req.GetOrder())
				valid = true
			}
	    }
	    case *SyncRequest_Dummy:{
	    	fmt.Printf("Dummy:%s\n", d.Dummy)
			valid = true
		}
		default:
			valid = false
			return req, valid
	}

	if !valid {
		return req, valid
	}

	// check if the same key=value already exists
	err := app.db.View(func(txn *badger.Txn) error {
		item, err := txn.Get(key)
		if err != nil && err != badger.ErrKeyNotFound {
			return err
		}
		if err == nil {
			return item.Value(func(val []byte) error {
				if !bytes.Equal(val, value) {
					valid = true 
				}
				return nil
			})
		}
		return nil
	})
	if err != nil {
		panic(err)
	}

	return req, valid
}
