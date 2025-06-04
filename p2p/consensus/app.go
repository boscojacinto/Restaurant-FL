package main

import (
	"fmt"
	"bytes"
	"encoding/gob"
	"golang.org/x/crypto/sha3"
	"github.com/dgraph-io/badger"
	"google.golang.org/protobuf/proto"
	abcitypes "github.com/tendermint/tendermint/abci/types"
)

const AppVersion = 1
//const PUBLIC_KEY = "4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5"
const ID = "4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5"

type InferSyncApp struct {
	db *badger.DB
	currentBatch *badger.Txn
}

type State struct {
	NumOrders uint64  `json:"num_orders"`
	Height  int64  `json:"height"`
	OrdersHash []byte `json:"orders_hash"`
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
	var k []byte
	var v []byte

	switch syncReq.Type.(type) {
		case *SyncRequest_Order: {
			fmt.Println("DeliverTX:SyncRequest_Order")
			
			k, v, _ = getOrderKV(app, syncReq.GetOrder())
			k=k
			// Check if order proof belongs to us
			//if matchOrder(syncReq) {				
			key, value = makeOrderKV(syncReq.GetOrder(), v)
			valid = true
			//}
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
	
	keccak := sha3.NewLegacyKeccak256()
	var appHash = []byte{}

	err := app.db.View(func(txn *badger.Txn) error {
        opts := badger.DefaultIteratorOptions
        opts.PrefetchValues = false
        
        it := txn.NewIterator(opts)
        defer it.Close()

        var keys [][]byte
        var rCount = uint64(0)
        for it.Rewind(); it.Valid(); it.Next() {
            key := it.Item().KeyCopy(nil)
            keys = append(keys, key)
        }

        for _, key := range keys {
            fmt.Println("KEY:", string(key))
			keccak.Write(key)
			rCount = rCount + uint64(1)
        }

        if rCount != 0 {
			appHash = []byte(fmt.Sprintf("%x", keccak.Sum(nil)))
        }
        
        return nil
    })
    if err != nil {
        fmt.Println("Could not create app hash:", err)
    }

    fmt.Println("APPHASH:", appHash)
	app.currentBatch.Commit()
	return abcitypes.ResponseCommit{Data: appHash}
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
	id := string(identity.GetID())

	if id == ID {
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

type RestaurantOrderKV struct {
	Id string
	HashOrders string
	NumOrders uint64
}

func getOrderKV(app *InferSyncApp, req *OrderRequest) ([]byte, []byte, error) {

	identity := req.GetIdentity()
	id := string(identity.GetID())
	key := []byte(id + "-" + "order")
	fmt.Println("Key:", id + "-" + "order")
	var value []byte

	err := app.db.View(func(txn *badger.Txn) error {
		item, err := txn.Get(key)
		if err != nil && err != badger.ErrKeyNotFound {
			return err
		}

		if item == nil {
			return nil			
		}

		value = make([]byte, item.ValueSize())
		_, e := item.ValueCopy(value)

		return e
	})
	if err != nil {
		return nil, nil, err
	}

	if len(value) == 0 {
		return key, nil, err		
	}

	return key, value, err
}

func makeOrderKV(req *OrderRequest, prevOrderBytes []byte) ([]byte, []byte) {
	var curOrder bytes.Buffer
	
	proof := req.GetProof()
	keccak := sha3.NewLegacyKeccak256()
	keccak.Write(proof.GetBuf())
	hash := fmt.Sprintf("%x", keccak.Sum(nil))
	fmt.Println("Initial Order Hash:", hash)
	numOrders := uint64(1)
	identity := req.GetIdentity()
	id := string(identity.GetID())

	var prevOrderKV RestaurantOrderKV

	if prevOrderBytes != nil {
		prevOrder := bytes.NewBuffer(prevOrderBytes)
		dec := gob.NewDecoder(prevOrder)
		err := dec.Decode(&prevOrderKV)
		if err != nil {
			return nil, nil
		}
	}

	if prevOrderKV.HashOrders != "" && prevOrderKV.NumOrders > 1 {
		keccak = sha3.NewLegacyKeccak256()
		keccak.Write([]byte(prevOrderKV.HashOrders))
		keccak.Write([]byte(hash))
		hash = fmt.Sprintf("%x", keccak.Sum(nil))
		numOrders = prevOrderKV.NumOrders + 1
	}

	fmt.Println("Final Order Hash:", hash)

	orderData := RestaurantOrderKV{
		Id: id,
		HashOrders: hash,
		NumOrders: numOrders,
	}

	enc := gob.NewEncoder(&curOrder)
	err := enc.Encode(orderData)
	if err != nil {
		return nil, nil
	}

	k := []byte(id + "-" + "order")
	v := []byte(curOrder.Bytes())
	return k, v
}

func (app *InferSyncApp) isValid(tx []byte) (req *SyncRequest, valid bool) {
	
	valid = false

	req = &SyncRequest{}

	if err := proto.Unmarshal(tx, req); err != nil {
		panic(err)
	}

    switch d := req.Type.(type) {
	    case *SyncRequest_Order:{
	    	fmt.Printf("Order:%s\n", d.Order)
			if verifyOrder(req.GetOrder()) {
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
	// No need to check duplicate tx since 
	// nullifier in proof verfication already does that
	return req, valid
}
