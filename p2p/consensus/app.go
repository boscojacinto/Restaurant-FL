package main

import (
	"fmt"
	"bytes"
	"errors"
	"crypto/ecdsa"
	"math/big"
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
	orderDb *badger.DB
	registerDb *badger.DB
	currentOrders *badger.Txn
	currentPeers *badger.Txn
	registerPeers *badger.Txn
}

type State struct {
	NumOrders uint64  `json:"num_orders"`
	Height  int64  `json:"height"`
	OrdersHash []byte `json:"orders_hash"`
}

var _ abcitypes.Application = (*InferSyncApp)(nil)
var localOrderFound = false

func NewInferSyncApp(orderDb *badger.DB, registerDb *badger.DB) *InferSyncApp {
	return &InferSyncApp{
		orderDb: orderDb,
		registerDb: registerDb,
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
	
	_, _, err := app.isTxValid(req.Tx)
	if err != nil {
		code = uint32(3)
	}

	return abcitypes.ResponseCheckTx{Code: code, Codespace: "sync", GasWanted: 1}
}

func (app *InferSyncApp) DeliverTx(req abcitypes.RequestDeliverTx) abcitypes.ResponseDeliverTx {

	syncReq, orderInfo, err := app.isTxValid(req.Tx)
	if err != nil {
		return abcitypes.ResponseDeliverTx{Code: 3, Codespace: "sync"}
	}

	var orderKey []byte
	var orderValue []byte
	var peersKeys [][]byte
	var peersValues [][]byte

	switch syncReq.Type.(type) {
		case *SyncRequest_Order: {
			fmt.Println("DeliverTX:SyncRequest_Order")
			
			orderKey, orderValue, _ = getOrderKV(app, orderInfo)
			orderKey=orderKey
			
			orderKey, orderValue = makeOrderKV(orderInfo, orderValue)
			peersKeys, peersValues = makePeersKV(orderInfo)

			err := app.currentOrders.Set(orderKey, orderValue)
			fmt.Println("Adding order key")
			if err != nil {
				panic(err)
			}		

			var v []byte
			for i, k := range(peersKeys) {

				v = peersValues[i]
				if string(v) != "" {
					if i == 0 && len(peersKeys) == 1 {
						err := app.registerPeers.Set(k, v)
						fmt.Println("Added key to register DB")
						if err != nil {
							panic(err)
						}
						break						
					}
				} else {
					err := app.registerDb.View(func(txn *badger.Txn) error {
				        opts := badger.DefaultIteratorOptions
				        opts.PrefetchValues = false
				        
				        it := txn.NewIterator(opts)
				        defer it.Close()

				        var keys [][]byte
				        for it.Rewind(); it.Valid(); it.Next() {
				            key := it.Item().KeyCopy(nil)
				            keys = append(keys, key)
				        }

				        fmt.Println("Peer KEY:", string(k))
				        for _, key := range keys {
				            fmt.Println("ENR KEY:", string(key))

				            if string(k) == string(key) {

								item, err := txn.Get(key)
								if err != nil && err != badger.ErrKeyNotFound {
									fmt.Println("Item not found")
									panic(err)
								}

				            	v = make([]byte, item.ValueSize())
								_, e := item.ValueCopy(v)
								e=e
								err = app.currentPeers.Set(k, v)
								fmt.Println("Added peer key to order DB")
								if err != nil {
									panic(err)
								}
								break
				            } 
				        }
				        return nil
				    })
				    if err != nil {
				        fmt.Println("Could not create app hash:", err)
				    }
				}
			}
		}

		case *SyncRequest_Dummy: {
			fmt.Println("DeliverTX:SyncRequest_Dummy")			
		}

		default: {
			fmt.Println("DeliverTX:default")			
		}	
	}

	return abcitypes.ResponseDeliverTx{Code: 0, Codespace: "sync"}
}

func (app *InferSyncApp) Commit() abcitypes.ResponseCommit {
	
	keccak := sha3.NewLegacyKeccak256()
	var appHash = []byte{}

	err := app.orderDb.View(func(txn *badger.Txn) error {
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
	app.currentOrders.Commit()
	app.currentPeers.Commit()
	app.registerPeers.Commit()
	return abcitypes.ResponseCommit{Data: appHash}
}

func (app *InferSyncApp) Query(reqQuery abcitypes.RequestQuery) (resQuery abcitypes.ResponseQuery) {
	resQuery.Key = reqQuery.Data
	err := app.orderDb.View(func(txn *badger.Txn) error {
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
	app.currentOrders = app.orderDb.NewTransaction(true)
	app.currentPeers = app.orderDb.NewTransaction(true)
	app.registerPeers = app.registerDb.NewTransaction(true)
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

type SyncOrderInfo struct {
	ProofHash string
	NumOrders uint64
	NodeID string
	NodePeerAddr string
	NodeURL string
	NodeENR string
	NodeDomain string
	NodeSubDomains []string
	NodePublicKey ecdsa.PublicKey 	
}

func verifyOrder(req *OrderRequest) (*SyncOrderInfo, error) {

	var orderInfo = &SyncOrderInfo{}
	proof := req.GetProof()
	// TODO Verify proof
	keccak := sha3.NewLegacyKeccak256()
	keccak.Write(proof.GetBuf())
	hash := fmt.Sprintf("%x", keccak.Sum(nil))
	fmt.Println("Initial Order Hash:", hash)
	orderInfo.ProofHash = hash
	orderInfo.NumOrders = uint64(1)
	orderInfo.NodeID = req.GetIdentity().GetID()
	
	// Verify ENR
	enr := req.GetIdentity().GetENR()
	fmt.Println("ENR is:", enr)

	if enr != "" {
		peerAddrInfo, err := EnodeToPeerInfo(enr)
		if err != nil {
			return nil, err
		}		

		orderInfo.NodeENR = req.GetIdentity().GetENR()
		orderInfo.NodePeerAddr = peerAddrInfo.String()
		fmt.Println("peerAddrInfo.ID:", peerAddrInfo.ID)
		fmt.Println("peerAddrInfo.Addrs:", peerAddrInfo.Addrs)
	}

	// Verify Url of enr tree(peers)
	idlePeers := req.GetIdlePeers()

	if idlePeers != nil {
		url := idlePeers.GetUrl()
		subdomains := idlePeers.GetSubDomain()
		
		// TODO: Check is subdomains correspond to 
		// unlisted idle peers 

		idStr := req.GetIdentity().GetID()
		domain, pubKey, err := CheckURL(url, idStr)
		if err != nil {
			return nil, err
		}
		orderInfo.NodeURL = url
		orderInfo.NodeDomain = domain
		orderInfo.NodeSubDomains = subdomains
		orderInfo.NodePublicKey = ecdsa.PublicKey{
	  		Curve: pubKey.Curve,
	        X:     new(big.Int).Set(pubKey.X),
	        Y:     new(big.Int).Set(pubKey.Y),			
		}
	}

	return orderInfo, nil
}

type RestaurantOrderKV struct {
	Id string
	HashOrders string
	NumOrders uint64
}

func getOrderKV(app *InferSyncApp, info *SyncOrderInfo) ([]byte, []byte, error) {

	key := []byte(info.NodeID + "-" + "order")
	fmt.Println("Key:", info.NodeID + "-" + "order")
	var value []byte

	err := app.orderDb.View(func(txn *badger.Txn) error {
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

func makeOrderKV(info *SyncOrderInfo, prevOrderBytes []byte) ([]byte, []byte) {
	var curOrder bytes.Buffer
	var prevOrderKV RestaurantOrderKV
	
	fmt.Println("Initial Order Hash:", info.ProofHash)

	if prevOrderBytes != nil {
		prevOrder := bytes.NewBuffer(prevOrderBytes)
		dec := gob.NewDecoder(prevOrder)
		err := dec.Decode(&prevOrderKV)
		if err != nil {
			return nil, nil
		}
	}
	
	var hash string

	if prevOrderKV.HashOrders != "" && prevOrderKV.NumOrders > 1 {
		keccak := sha3.NewLegacyKeccak256()
		keccak.Write([]byte(prevOrderKV.HashOrders))
		keccak.Write([]byte(info.ProofHash))
		hash = fmt.Sprintf("%x", keccak.Sum(nil))
		info.NumOrders = prevOrderKV.NumOrders + 1
	}

	fmt.Println("Final Order Hash:", hash)

	orderData := RestaurantOrderKV{
		Id: info.NodeID,
		HashOrders: info.ProofHash,
		NumOrders: info.NumOrders,
	}

	enc := gob.NewEncoder(&curOrder)
	err := enc.Encode(orderData)
	if err != nil {
		return nil, nil
	}

	k := []byte(info.NodeID + "-" + "order")
	v := []byte(curOrder.Bytes())
	return k, v
}

type RestaurantPeersKV struct {
	Subdomains []string
}

func makePeersKV(info *SyncOrderInfo) ([][]byte, [][]byte) {
	var keys [][]byte
	var values [][]byte

	if info.NodeENR != "" {
		subdomain := CreateSubDomain(info.NodeENR)		
		k := []byte(subdomain + "-" + "peer")
		v := []byte(info.NodeENR)		
		keys = append(keys, k)
		values = append(values, v)

	} else if len(info.NodeSubDomains) != 0 {

		for _, subdomain := range(info.NodeSubDomains) {
			k := []byte(subdomain + "-" + "peer")
			v := []byte("")	
			keys = append(keys, k)
			values = append(values, v)			
		}
	} 

	return keys, values
}

func (app *InferSyncApp) isTxValid(tx []byte) (*SyncRequest, *SyncOrderInfo, error) {
	
	req := &SyncRequest{}

	if err := proto.Unmarshal(tx, req); err != nil {
		panic(err)
	}

    switch d := req.Type.(type) {
	    case *SyncRequest_Order:{
	    	fmt.Printf("Order:%s\n", d.Order)
			orderInfo, err := verifyOrder(req.GetOrder())
			if err != nil {
				return req, orderInfo, nil
			}
	    }
	    case *SyncRequest_Dummy:{
	    	fmt.Printf("Dummy:%s\n", d.Dummy)
			return nil, nil, errors.New("Invalid tx")
		}
		default:
			return nil, nil, errors.New("Invalid tx")
	}

	// check if the same key=value already exists
	// No need to check duplicate tx since 
	// nullifier in proof verfication already does that
	return nil, nil, errors.New("Invalid tx")
}
