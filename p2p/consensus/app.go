package main

import (
	"fmt"
	"errors"
	"unsafe"
	"hash"
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
}

type OrderInfo struct {
	ProofHash string	`json:"proofHash"`
	NumOfOrders uint64	`json:"proofhash"`
	NodeId string	`json:"nodeId"`
	NodeEnr string	`json:"nodeEnr"`
	NodeAddrInfo string `json:"nodeAddrInfo"`
	PeerUrl string	`json:"peerUrl"`
	PeerDomain string `json:"peerDomain"`
	PeerSubDomains []string `json:"peerSubDomains"`
	InferenceMode string `json:"inferenceMode"`
	NodePublicKey ecdsa.PublicKey
	Approved bool `json:"approved"`
}

type InferSyncApp struct {
	cCtx unsafe.Pointer
	orderDb *badger.DB
	registerDb *badger.DB
	peersDb *badger.DB
	currentOrders *badger.Txn
	currentPeers *badger.Txn
	currentRegisters *badger.Txn
	state State
	nodeSubDomain string
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

func NewInferSyncApp(cCtx unsafe.Pointer, orderDb *badger.DB,
	registerDb *badger.DB, peersDb *badger.DB) *InferSyncApp {
	state := loadState(dbm.NewMemDB())
	return &InferSyncApp{
		orderDb: orderDb,
		registerDb: registerDb,
		peersDb: peersDb,
		state: state,
		cCtx: cCtx,
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
	
	_, orderInfo, err := app.isTxValid(req.Tx)
	if err != nil {
		code = uint32(3)
		return abcitypes.ResponseCheckTx{Code: code, Codespace: "order.tx.check"}
	}

	orderInfoBytes, err := json.Marshal(orderInfo)
	if err != nil {
		return abcitypes.ResponseCheckTx{Code: uint32(3), Codespace: "order.tx.check"}
	}

	//tm.event='Tx' AND tx.hash='%X'
	var status string
	switch orderInfo.InferenceMode {
		case "solo": {
			status = "solo.start"
		}
		case "assist": {
			if isAssistPeer(app, orderInfo) == true &&
			   app.nodeSubDomain != orderInfo.PeerDomain {
				status = "assist.ping"
			} else if isRoutePeer(app, orderInfo) == true {
				status = "assist.route"
			} else {
				status = "assist.start"
			}
		}		
		default: {
			status = "solo.start"		
		}
	}
	
	var events []abcitypes.Event
	events = []abcitypes.Event {
	        {
	            Type: "order.tx.check",
	            Attributes: []abcitypes.EventAttribute{
	                {Key: []byte("orderinfo"), Value: orderInfoBytes, Index: true},
	                {Key: []byte("status"), Value: []byte(status), Index: true},
	            },
	        },
	    }

	return abcitypes.ResponseCheckTx{Code: code, Codespace: "order.tx.check", Events: events}
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
			valid = true

			err = makeRegisterPeerKV(app, orderInfo)
			if err != nil {
				break
			}

			err = makeIdlePeerKV(app, orderInfo)
			if err != nil {
				break
			}

		}

		case *SyncRequest_Dummy: {
			fmt.Println("DeliverTX:SyncRequest_Dummy")			
		}

		default: {
			fmt.Println("DeliverTX:default")			
		}	
	}

	var status string
	switch orderInfo.InferenceMode {
		case "solo": {
			status = "solo.done"
		}
		case "assist": {
			if isAssistPeer(app, orderInfo) == true &&
			   app.nodeSubDomain != orderInfo.PeerDomain {
				status = "assist.done"
			} else if isRoutePeer(app, orderInfo) == true {
				status = "assist.done"
			} else {
				status = "assist.done"
			}
		}		
		default: {
			status = "solo.done"	
		}
	}

	orderInfoBytes, err := json.Marshal(orderInfo)
	if err != nil {
		return abcitypes.ResponseDeliverTx{Code: uint32(3), Codespace: "order.tx.deliver"}
	}

	var events []abcitypes.Event
	fmt.Println("\nSending event\n")
	events = []abcitypes.Event {
	        {
	            Type: "order.tx.deliver",
	            Attributes: []abcitypes.EventAttribute{
	                {Key: []byte("orderinfo"), Value: orderInfoBytes, Index: true},
	                {Key: []byte("status"), Value: []byte(status), Index: true},
	            },
	        },
	    }

	if valid == true {
		app.state.NumOrders++ 
		saveState(app.state)
		fmt.Println("\nSaving state\n")
	}

	return abcitypes.ResponseDeliverTx{Code: 0, Codespace: "order.tx.deliver", Events: events}
}

func (app *InferSyncApp) Commit() abcitypes.ResponseCommit {
	
	fmt.Println("COMMIT")
	var appHash = make([]byte, 8)
	binary.PutVarint(appHash, app.state.NumOrders)
	saveState(app.state)

    fmt.Println("APPHASH:", appHash)
	app.currentOrders.Commit()
	app.currentPeers.Commit()
	app.currentRegisters.Commit()
	return abcitypes.ResponseCommit{Data: appHash}
}

func (app *InferSyncApp) Query(reqQuery abcitypes.RequestQuery) (resQuery abcitypes.ResponseQuery) {
	resQuery.Key = reqQuery.Data

	var cb = func(txn *badger.Txn) error {
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
		}

	if reqQuery.Path == "orders" {

		err := app.orderDb.View(cb)
		if err != nil {
			panic(err)
		}
		return resQuery

	} else if reqQuery.Path == "peers" {

		err := app.peersDb.View(cb)
		if err != nil {
			panic(err)
		}
		return resQuery		
	} else if reqQuery.Path == "registers" {

		err := app.registerDb.View(cb)
		if err != nil {
			panic(err)
		}
		return resQuery
	}

	return resQuery
}

func (InferSyncApp) InitChain(req abcitypes.RequestInitChain) abcitypes.ResponseInitChain {
	return abcitypes.ResponseInitChain{}
}

func (app *InferSyncApp) BeginBlock(req abcitypes.RequestBeginBlock) abcitypes.ResponseBeginBlock {
	fmt.Println("\nin BeginBlock:prev Height:\n", req.Header.Height)
	app.currentOrders = app.orderDb.NewTransaction(true)
	app.currentPeers = app.peersDb.NewTransaction(true)
	app.currentRegisters = app.registerDb.NewTransaction(true)
	return abcitypes.ResponseBeginBlock{}
}

func (app *InferSyncApp) EndBlock(req abcitypes.RequestEndBlock) abcitypes.ResponseEndBlock {
	fmt.Println("in END of block:", req.Height)
	nodeSubDomain, err := createNodeSubDomain(app.cCtx, req.Height+1)
	if err != nil {
		panic(err)
	}
	app.nodeSubDomain = nodeSubDomain
	fmt.Println("nodeSubDomain:", nodeSubDomain)
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

func createNodeSubDomain(cCtx unsafe.Pointer, height int64) (string, error) {
	
	instance, err := getInstance(cCtx)
	domain := "nodes.restaurant.idle.com"

	if uint(instance.height) != uint(height) {
		return "", nil
	}

	nodeEnr, err := createLocalRegisterPeer(uint(height), domain, instance.nodePeerAddr.Addrs,
		instance.nodePeerAddr.ID, instance.sharedKey)
	if err != nil {
		return "", errors.New("Unable to create local subdomain") 
	}

	nodeSubDomain := CreatePeerSubDomain(nodeEnr)	

	return nodeSubDomain, nil
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

func verifyOrderInfo(app *InferSyncApp, req *OrderRequest) (*OrderInfo, error) {

	var orderInfo = &OrderInfo{}

	// Verify Node Id
	orderInfo.NodeId = req.GetIdentity().GetID()
	orderInfo.Approved = false

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

	orderInfo.InferenceMode = req.GetInference().GetMode()

	// Verify Url of Enr tree of the peers
    peers := req.GetPeers() 
    if peers != nil {
    	mode := req.GetInference().GetMode()
    	fmt.Println("Verify Idle Peers")
    	
    	idlePeers := req.GetPeers()
		peerUrl := idlePeers.GetUrl()
		peerSubDomains := idlePeers.GetSubDomain()
		peerSignatures := idlePeers.GetApproval().GetSignature()
		
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

		var keccak hash.Hash
		var peerEnr string

		orderInfo.Approved = true
		if mode == "assist" {
	    	fmt.Println("Verify Assist Peers")		

	    	orderInfo.Approved = true
			for i, subDomain := range(peerSubDomains) {
				keccak = sha3.NewLegacyKeccak256()
				keccak.Write([]byte(subDomain))

				peerEnr, err = getPeerInRegisterDb(app, subDomain)
				if err != nil {
					orderInfo.Approved = false
					break
				}
				if !verifyPeerSignature(keccak.Sum(nil),
						peerSignatures[i], peerEnr) {
					orderInfo.Approved = false
					break
				}
			}			
		} else {
			orderInfo.Approved = true
		}

		orderInfo.PeerUrl = peerUrl
		orderInfo.PeerDomain = domain
		orderInfo.PeerSubDomains = peerSubDomains
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

func isAssistPeer(app *InferSyncApp, info *OrderInfo) bool {

	fmt.Println("isAssistPeer:PeerURL:", info.PeerUrl)
	fmt.Println("isAssistPeer:len(PeerSubDomains):", len(info.PeerSubDomains))
	fmt.Println("isAssistPeer:app.nodeSubDomain:", app.nodeSubDomain)
	fmt.Println("isAssistPeer.PeerSubDomains:", info.PeerSubDomains)

	for _, peerSubDomain := range(info.PeerSubDomains) {

		if peerSubDomain == app.nodeSubDomain {
			fmt.Println("Matched with local NodeSubdomain")
			return true
		}
	}

	return false
}

func isRoutePeer(app *InferSyncApp, info *OrderInfo) bool {

	fmt.Println("isRoutePeer:app.nodeSubDomain:", app.nodeSubDomain)
	fmt.Println("isRoutePeer.PeerDomain:", info.PeerDomain)

	if info.PeerDomain == app.nodeSubDomain {
		fmt.Println("Matched PeerDomain with local NodeSubdomain")
		return true
	}

	return false
}

func getPeerInRegisterDb(app *InferSyncApp, peerSubDomain string) (string, error) {

	key := []byte(peerSubDomain + "-" + "register")
	var value []byte

	var cb = func(txn *badger.Txn) error {
			item, err := txn.Get(key)
			if err != nil && err != badger.ErrKeyNotFound {
				return err
			}
			if err == badger.ErrKeyNotFound {
			} else {
				value = make([]byte, item.ValueSize())
				_, _ = item.ValueCopy(value)
				return nil
			}
			return nil
		}

	err := app.registerDb.View(cb)
	if err != nil {
		return "", err
	}

	return string(value), nil
}

/*func presentInPeerDb(app *InferSyncApp, info *OrderInfo) bool {

	var value []byte 

	var cb = func(txn *badger.Txn) error {
			item, err := txn.Get(reqQuery.Data)
			if err != nil && err != badger.ErrKeyNotFound {
				return err
			}
			if err == badger.ErrKeyNotFound {
			} else {
				return item.Value(func(val []byte) error {
					value = val
					return nil
				})
			}
			return nil
		}

	err := app.peersDb.View(cb)
	if err != nil {
		panic(err)
	}
	return resQuery

	fmt.Println("isAssistPeer:PeerURL:", info.PeerUrl)
	fmt.Println("isAssistPeer:len(PeerSubDomains):", len(info.PeerSubDomains))
	fmt.Println("isAssistPeer:app.nodeSubDomain:", app.nodeSubDomain)
	fmt.Println("isAssistPeer.PeerSubDomains:", info.PeerSubDomains)

	for _, peerSubDomain := range(info.PeerSubDomains) {

		if peerSubDomain == app.nodeSubDomain {
			fmt.Println("Matched with local NodeSubdomain")
			return true
		}
	}

	return false
}
*/
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

			orderInfo, err := verifyOrderInfo(app, req.GetOrder())
			if err != nil {
				return nil, nil, errors.New("Invalid tx")
			}

			if orderInfo.Approved == false {
				return nil, nil, errors.New("Assist not approved")				
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
