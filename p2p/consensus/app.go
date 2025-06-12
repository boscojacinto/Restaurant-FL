package main

import (
	"fmt"
	"errors"
	"crypto/ecdsa"
	"math/big"
	"encoding/binary"
	"encoding/json"
	"golang.org/x/crypto/sha3"
	"github.com/dgraph-io/badger"
	dbm "github.com/tendermint/tm-db"	
	"google.golang.org/protobuf/proto"
	abcitypes "github.com/tendermint/tendermint/abci/types"
)

const AppVersion = 1
//const PUBLIC_KEY = "4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5"
const ID = "4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5"
var StateKey = []byte("stateKey")

type State struct {
	db dbm.DB
	NumOrders int64  `json:"num_orders"`
	Height  int64  `json:"height"`
}

type OrderInfo struct {
	ProofHash string
	NumOfOrders uint64
	NodeId string
	NodeEnr string
	NodeAddrInfo string
	PeerUrl string
	PeerDomain string
	PeerSubDomains []string
	NodePublicKey ecdsa.PublicKey 	
}

type InferSyncApp struct {
	orderDb *badger.DB
	registerDb *badger.DB
	currentOrders *badger.Txn
	currentPeers *badger.Txn
	currentRegisters *badger.Txn
	state State
}

var _ abcitypes.Application = (*InferSyncApp)(nil)
var localOrderFound = false

func loadState(db dbm.DB) State {
	var state State
	state.db = db
	stateBytes, err := db.Get(StateKey)
	if err != nil {
		panic(err)
	}
	if len(stateBytes) == 0 {
		return state
	}
	err = json.Unmarshal(stateBytes, &state)
	if err != nil {
		panic(err)
	}
	return state
}

func saveState(state State) {
	stateBytes, err := json.Marshal(state)
	if err != nil {
		panic(err)
	}
	err = state.db.Set(StateKey, stateBytes)
	if err != nil {
		panic(err)
	}
}

func NewInferSyncApp(orderDb *badger.DB, registerDb *badger.DB) *InferSyncApp {
	state := loadState(dbm.NewMemDB())
	return &InferSyncApp{
		orderDb: orderDb,
		registerDb: registerDb,
		state: state,
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

	var valid bool = false
	syncReq, orderInfo, err := app.isTxValid(req.Tx)
	if err != nil {
		return abcitypes.ResponseDeliverTx{Code: 3, Codespace: "sync"}
	}

	switch syncReq.Type.(type) {
		case *SyncRequest_Order: {
			fmt.Println("DeliverTX:SyncRequest_Order")
			
			_, v, err := getOrderKV(app, orderInfo)

			err = makeOrderKV(app, orderInfo, v)
			if err != nil {
				break
			}

			err = makeRegisterPeerKV(app, orderInfo)
			if err != nil {
				break
			}

			err = makeIdlePeerKV(app, orderInfo)
			if err != nil {
				break
			}

			valid = true
		}

		case *SyncRequest_Dummy: {
			fmt.Println("DeliverTX:SyncRequest_Dummy")			
		}

		default: {
			fmt.Println("DeliverTX:default")			
		}	
	}

	if valid == true {
		app.state.NumOrders++ 
		saveState(app.state)
	}

	return abcitypes.ResponseDeliverTx{Code: 0, Codespace: "sync"}
}

func (app *InferSyncApp) Commit() abcitypes.ResponseCommit {
	
	fmt.Println("COMMIT")
	var appHash = make([]byte, 8)
	binary.PutVarint(appHash, app.state.NumOrders)
	app.state.Height++
	saveState(app.state)

    fmt.Println("APPHASH:", appHash)
	app.currentOrders.Commit()
	app.currentPeers.Commit()
	app.currentRegisters.Commit()
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
	app.currentRegisters = app.registerDb.NewTransaction(true)
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

func verifyOrderProof(req *OrderRequest) (string, uint64, error) {

	orderProof := req.GetProof()

	// TODO Verify order proof
	keccak := sha3.NewLegacyKeccak256()
	keccak.Write(orderProof.GetBuf())
	orderProofHash := fmt.Sprintf("%x", keccak.Sum(nil))
	fmt.Println("Initial Order Proof Hash:", orderProofHash)
	
	numOfOrders := uint64(1)

	return orderProofHash, numOfOrders, nil
}

func verifyOrderInfo(req *OrderRequest) (*OrderInfo, error) {

	var orderInfo = &OrderInfo{}

	// Verify Node Id
	orderInfo.NodeId = req.GetIdentity().GetID()
	
	// Verify Node ENR
	nodeEnr := req.GetIdentity().GetENR()
	fmt.Println("Node ENR is:", nodeEnr)
	if nodeEnr == "" {
		return nil, errors.New("Empty node Enr")
	}
	orderInfo.NodeEnr = nodeEnr

	nodeAddrInfo, err := EnodeToPeerInfo(nodeEnr)
	if err != nil {
		return nil, err
	}		

	orderInfo.NodeAddrInfo = nodeAddrInfo.String()

	// Verify Url of Enr tree of the peers

    idle := req.GetPeers().GetIdle() 
    if idle == true {
    	fmt.Println("Verify Idle Peers")
    	
    	idlePeers := req.GetPeers()
		peerUrl := idlePeers.GetUrl()
		peerSubDomains := idlePeers.GetSubDomain()
		
		// TODO: Check is subdomains correspond to unlisted idle peers 
		nodeId := req.GetIdentity().GetID()
		domain, pubKey, err := CheckURL(peerUrl, nodeId)
		if err != nil {
			return nil, err
		}

		orderInfo.NodePublicKey = ecdsa.PublicKey{
	  		Curve: pubKey.Curve,
	        X:     new(big.Int).Set(pubKey.X),
	        Y:     new(big.Int).Set(pubKey.Y),			
		}

		orderInfo.PeerUrl = peerUrl
		orderInfo.PeerDomain = domain
		orderInfo.PeerSubDomains = peerSubDomains
	} else {
    	fmt.Println("Verify Busy Peers")		
	}

	return orderInfo, nil
}

func getOrderKV(app *InferSyncApp, info *OrderInfo) ([]byte, []byte, error) {

	key := []byte(info.NodeId + "-" + "order")
	fmt.Println("Key:", info.NodeId + "-" + "order")
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
		_, err = item.ValueCopy(value)

		return err
	})
	if err != nil {
		return nil, nil, err
	}

	if len(value) == 0 {
		return key, nil, err		
	}

	return key, value, err
}

func makeOrderKV(app *InferSyncApp, info *OrderInfo,
	prevOrderHash []byte) error {
	
	fmt.Println("Initial Order Hash:", info.ProofHash)
	
	if string(prevOrderHash) != "" {
		keccak := sha3.NewLegacyKeccak256()
		keccak.Write(prevOrderHash)
		keccak.Write([]byte(info.ProofHash))
		aggHash := fmt.Sprintf("%x", keccak.Sum(nil))
		info.ProofHash = aggHash
	}

	fmt.Println("Final Order Hash:", info.ProofHash)

	k := []byte(info.NodeId + "-" + "order")
	v := []byte([]byte(info.ProofHash))

	err := app.currentOrders.Set(k, v)
	fmt.Println("Adding order key")

	return err
}

type RestaurantPeersKV struct {
	Subdomains []string
}

func makeRegisterPeerKV(app *InferSyncApp, info *OrderInfo) error {

	peerSubDomain := CreatePeerSubDomain(info.NodeEnr)
	k := []byte(peerSubDomain + "-" + "register")
	v := []byte(info.NodeEnr)		
	fmt.Println("Peer Register Key:", string(k))		

	err := app.currentRegisters.Set(k, v)
	if err != nil {
		errors.New("Could not set in current register")
	}
	fmt.Println("Added key to register DB")

	return err 	
}

func makeIdlePeerKV(app *InferSyncApp, info *OrderInfo) error {

	fmt.Println("makeIdlePeerKV:", info.PeerUrl)
	fmt.Println("len(info.PeerSubDomains):", len(info.PeerSubDomains))

	if info.PeerUrl == "" || len(info.PeerSubDomains) == 0 {
		return errors.New("Invalid peer url or peer subdomain")
	}

	var k []byte
	var v []byte
	var rKey []byte
	var rFound bool = false

	k = []byte(info.PeerUrl + "-" + "peers")
	for _, peerSubDomain := range(info.PeerSubDomains) {
		fmt.Println("Peer Subdomain:", peerSubDomain)

		rKey = []byte(peerSubDomain + "-" + "register")
		_, err := app.currentRegisters.Get(rKey)
		if err == nil {
			rFound = true
			break
		}
		v = append(v, peerSubDomain...)
	}

	if rFound == false {
		return errors.New("Peer subdomain not registered")
	}

	err := app.currentPeers.Set(k, v)
	if err != nil {
		errors.New("Could not set in current peer")
	}
	fmt.Println("Added key to peer DB")		

	return err
}

func (app *InferSyncApp) isTxValid(tx []byte) (*SyncRequest, *OrderInfo, error) {
	
	req := &SyncRequest{}

	if err := proto.Unmarshal(tx, req); err != nil {
		panic(err)
	}

    switch d := req.Type.(type) {
	    case *SyncRequest_Order:{
	    	fmt.Printf("Order:%s\n", d.Order)
			
			orderProofHash, numOfOrders, err := verifyOrderProof(
												req.GetOrder())
			if err != nil {
				return nil, nil, errors.New("Invalid order proof")
			}

			orderInfo, err := verifyOrderInfo(req.GetOrder())
			if err != nil {
				return nil, nil, errors.New("Invalid tx")
			}

			orderInfo.ProofHash = orderProofHash	
			orderInfo.NumOfOrders = numOfOrders	

			return req, orderInfo, nil
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
