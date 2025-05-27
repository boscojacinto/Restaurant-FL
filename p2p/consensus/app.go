package main

import (
	"bytes"
	//"time"
	"fmt"
	"github.com/dgraph-io/badger"
	abcitypes "github.com/tendermint/tendermint/abci/types"
	"google.golang.org/protobuf/proto"
	"golang.org/x/crypto/sha3"
)

const AppVersion = 1
const PUBLIC_KEY = "4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5"

type InferSyncApp struct {
	db *badger.DB
	currentBatch *badger.Txn
}

var _ abcitypes.Application = (*InferSyncApp)(nil)
var idleState = false

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

func (app *InferSyncApp) DeliverTx(req abcitypes.RequestDeliverTx) abcitypes.ResponseDeliverTx {
	reqType, valid := app.isValid(req.Tx)
	if valid == false {
		return abcitypes.ResponseDeliverTx{Code: 3, Codespace: "sync"}
	}
	
	switch t := reqType.(type) {
		case *SyncRequest_Order: {

			// Check if order proof belongs to us
			order := t.Order
			identity := order.GetIdentity()
			publicKey := identity.GetPublicKey()
			if publicKey == PUBLIC_KEY {
				idleState = true
			}		
		}

		case *SyncRequest_Dummy: {
		}	
	}

/*	err := app.currentBatch.Set(key, value)
	if err != nil {
		panic(err)
	}
*/
	return abcitypes.ResponseDeliverTx{Code: 3, Codespace: "sync"}
}

func getOrderHash(req *OrderRequest) (hash string) {
	proof := req.GetProof()
	keccak := sha3.NewLegacyKeccak256()
	keccak.Write(proof.GetBuf())
	hash = fmt.Sprintf("%x", keccak.Sum(nil))
	return hash
}

func (app *InferSyncApp) isValid(tx []byte) (reqType isSyncRequest_Type, valid bool) {
	
	valid = false
	var key []byte
	var value []byte

	req := &SyncRequest{}

	if err := proto.Unmarshal(tx, req); err != nil {
		panic(err)
	}

    switch d := req.Type.(type) {
	    case *SyncRequest_Order:{
	    	fmt.Printf("Order:%s\n", d.Order)
			valid = true
			copy(key, "order-hash")
			copy(value, getOrderHash(req.GetOrder()))    	
	    }
	    case *SyncRequest_Dummy:{
	    	fmt.Printf("Dummy:%s\n", d.Dummy)
			valid = true
			copy(key, "dummy-hash")			
		}
		default:
			valid = false
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

	return req.Type, valid
}

func (app *InferSyncApp) CheckTx(req abcitypes.RequestCheckTx) abcitypes.ResponseCheckTx {
	code := uint32(0)
	
	_, valid := app.isValid(req.Tx)
	if valid == false {
		code = uint32(3)
	}

	return abcitypes.ResponseCheckTx{Code: code, Codespace: "sync", GasWanted: 1}
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