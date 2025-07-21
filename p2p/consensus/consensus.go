package main

/*
#include <cgo_utils.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <stdbool.h>

// The possible returned values for the functions that return int
static const int RET_OK = 0;
static const int RET_ERR = 1;
static const int RET_MISSING_CALLBACK = 2;

extern bool ConsensusSendSignal(void *cb, const char *jsonEvent);
typedef void (*ConsensusCallBack) (int ret_code, const char* msg, void * user_data);
*/
import "C"
import (
 "os"
 "fmt"
 //"flag"
 "time"
 "bytes"
 "sync"
 "sort"
 "strconv"
 "unsafe"
 "errors"
 "context"
 "crypto/ecdsa"
 "path/filepath"
 "encoding/json"
 "encoding/hex"
 "github.com/dgraph-io/badger"
 "github.com/spf13/viper"

 abci "github.com/tendermint/tendermint/abci/types"
 cfg "github.com/tendermint/tendermint/config"
 tmflags "github.com/tendermint/tendermint/libs/cli/flags"
 ctypes "github.com/tendermint/tendermint/rpc/core/types"
 "github.com/tendermint/tendermint/libs/log"
 nm "github.com/tendermint/tendermint/node"
 "github.com/tendermint/tendermint/p2p"
 "github.com/tendermint/tendermint/privval"
 "github.com/tendermint/tendermint/proxy"
 rpclocal "github.com/tendermint/tendermint/rpc/client/local"
 "google.golang.org/protobuf/proto"
 "github.com/tendermint/tendermint/types"
 "github.com/ethereum/go-ethereum/crypto"
 ma "github.com/multiformats/go-multiaddr"
 "github.com/libp2p/go-libp2p/core/peer"
 "github.com/libp2p/go-libp2p/core/protocol"
)

const (
	CheckTxEventType = "order_tx_check"
	DeliverTxEventType = "order_tx_deliver"
)

type ValidatorKey struct {
    Address string
    PublicKey string
    PrivateKey string
    PrivateKeyEcdsa *ecdsa.PrivateKey
}

type ConsensusInstance struct {
	ctx context.Context
	cancel context.CancelFunc

	ID uint

	rootDir string
	height int64 
	node *nm.Node
	config *cfg.Config
	rpc *rpclocal.Local

	orderDb *badger.DB
	registerDb *badger.DB 
	peersDb *badger.DB

	cb unsafe.Pointer	
	subscription EventListener
	key ValidatorKey
	sharedKey *ecdsa.PrivateKey
	nodePeerAddr Peer

	bundle *Bundle
}

type CheckTxEvent struct {
	Query  string              `json:"query"`
	Events map[string][]string `json:"events"`
}

type EventListener struct {
	ctx context.Context
	newBlockCh <-chan ctypes.ResultEvent
	deliverTxCh <-chan ctypes.ResultEvent
	checkTxCh chan CheckTxEvent
}

type SignalData struct {
	Type  string      `json:"type"`
	Event interface{} `json:"event"`
}

type NewBlock struct {
	Height  int64 `json:"height,omitempty"`
	Time time.Time `json:"time"`
	LastBlockID types.BlockID `json:"last_block_id"`
	DataHash []byte `json:"data_hash,omitempty"`
	AppHash []byte `json:"app_hash,omitempty"`
	ProposerAddress []byte `json:"proposer_address,omitempty"`
	Signatures []types.CommitSig `json:"signatures"`
}

type OrderTx struct {
	OrderInfo OrderInfo `json:"orderInfo"`
	Status string `json:"status"`
} 

type Peer struct {
	ID           peer.ID        `json:"peerID"`
	Protocols    []protocol.ID  `json:"protocols"`
	Addrs        []ma.Multiaddr `json:"addrs"`
	Connected    bool           `json:"connected"`
	PubsubTopics []string       `json:"pubsubTopics"`
	Timestamp time.Time     	`json:"timestamp"`
	Signature 	 string         `json:"signature"`
}

const Version = "1.0.0"
const IdleCutOffPercentage = 5

var cInstances map[uint]*ConsensusInstance
var cInstanceMutex sync.RWMutex

func main() {}

//export Init
func Init(rootDir *C.char, key *C.char) unsafe.Pointer {

	cInstanceMutex.Lock()
	defer cInstanceMutex.Unlock()

	cid := C.malloc(C.size_t(unsafe.Sizeof(uintptr(0))))
	pid := (*uint)(cid)
	
	cInstances = make(map[uint]*ConsensusInstance)
	cInstance := &ConsensusInstance{
		ID: uint(len(cInstances)),
	}
	cInstance.rootDir = C.GoString(rootDir)

	kHex, _ := hex.DecodeString(C.GoString(key))
	cInstance.key, _ = validatorKeyFromECDSA(kHex)
	cInstance.sharedKey, _ = crypto.GenerateKey()

	cInstances[0] = cInstance
	*pid = cInstance.ID

	return cid
}

//export UpdateNodeAddr
func UpdateNodeAddr(ctx unsafe.Pointer, address *C.char, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {
	instance, err := getInstance(ctx)

	if err != nil {
		return onError(errors.New("Cannot add node address"), onErr, userData)
	}

	var nodeAddress Peer
	addressStr := C.GoString(address)
	err = json.Unmarshal([]byte (addressStr), &nodeAddress)
	if err != nil {
		fmt.Println("err:", err)
		return onError(errors.New("Cannot parse address"), onErr, userData)
	}
	instance.nodePeerAddr = nodeAddress

	return onError(nil, onErr, userData)

}

//export Start
func Start(ctx unsafe.Pointer, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	instance, err := getInstance(ctx)

	if err != nil {
		return onError(errors.New("Cannot start"), onErr, userData)
	}

	instance.ctx, instance.cancel = context.WithCancel(context.Background())
	dir := filepath.Join(instance.rootDir, "/data")	

	err = os.MkdirAll(dir + "/tmp/order", 0755)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to create tmp/order: %v", err)
		os.Exit(1)
	}

	orderDb, err := badger.Open(badger.DefaultOptions(dir + "/tmp/order"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open order db: %v", err)
		os.Exit(1)
	}
	instance.orderDb = orderDb

	err = os.MkdirAll(dir + "/tmp/register", 0755)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to create tmp/register: %v", err)
		os.Exit(1)
	}

	registerDb, err := badger.Open(badger.DefaultOptions(dir + "/tmp/register"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open register db: %v", err)
		os.Exit(1)
	}
	instance.registerDb = registerDb

	err = os.MkdirAll(dir + "/tmp/peers", 0755)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to create tmp/peers: %v", err)
		os.Exit(1)
	}

	peersDb, err := badger.Open(badger.DefaultOptions(dir + "/tmp/peers"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open register db: %v", err)
		os.Exit(1)
	}
	instance.peersDb = peersDb
	instance.height = 0

	instance.bundle, _ = createBundle(instance.key.PrivateKeyEcdsa, string(instance.height))

	appSubsEvents := []string{ CheckTxEventType }
	app := NewInferSyncApp(ctx, orderDb, registerDb, peersDb, appSubsEvents)

	//flag.Parse()

	node, err := newTendermint(instance, app)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v", err)
		os.Exit(2)
	}

	instance.node = node 
	instance.rpc = rpclocal.New(node)

	ch_0, _ := instance.rpc.Subscribe(instance.ctx, "tastebot-subscribe", "tm.event='NewBlock'")
	ch_1, _ := instance.rpc.Subscribe(instance.ctx, "tastebot-subscribe", "tm.event='Tx' AND " + DeliverTxEventType + " EXISTS") //
	ch_2 := make(chan CheckTxEvent)

	instance.subscription = EventListener{
		ctx: instance.ctx,
	}	
	
	instance.subscription.newBlockCh = ch_0
	instance.subscription.deliverTxCh = ch_1
	instance.subscription.checkTxCh = ch_2
		
	go instance.listenOnEvents()
	instance.node.Start()
	return onError(nil, onErr, userData)
}

//export SetEventCallback
func SetEventCallback(ctx unsafe.Pointer, cb C.ConsensusCallBack) C.int {
	instance, err := getInstance(ctx)
	if err != nil {
		return 1
	}
	
	instance.cb = unsafe.Pointer(cb)

	return 0
}

//export Stop
func Stop(ctx unsafe.Pointer, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	instance, err := getInstance(ctx)
	if err != nil {
		return onError(errors.New("Cannot stop"), onErr, userData)
	}

	instance.orderDb.Close()
	instance.registerDb.Close()

	instance.node.Stop()
	instance.node.Wait()

	return onError(nil, onErr, userData)
}

//export SendOrder
func SendOrder(ctx unsafe.Pointer, proof *C.char, id *C.char, enr *C.char,
	peers *C.char, mode *C.char, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	if unsafe.Pointer(proof) == nil ||
	   unsafe.Pointer(id) == nil ||
	   unsafe.Pointer(enr) == nil ||
	   unsafe.Pointer(mode) == nil {
		return onError(errors.New("Proof, id, enr, mode invalid"), onErr, userData)
	}

	modeStr := C.GoString(mode)
	if !(modeStr == "solo" || modeStr == "assist") {
		return onError(errors.New("Invalid inference mode"), onErr, userData)
	}

	instance, err := getInstance(ctx)
	if err != nil {
		return onError(errors.New("Cannot stop"), onErr, userData)
	}

	c := context.Background()

	proofBytes := C.GoBytes(unsafe.Pointer(proof), C.int(C.strlen(proof)))
	idStr := C.GoString(id)
	enrString := C.GoString(enr)
	timestampStr := time.Now().Format("2006-01-02 15:04:05")
	
	var nodeEnr string
	var url string
	var peerSubDomains []string
	var peerSignatures []string

	if unsafe.Pointer(peers) != nil {
		nodeEnr, url, peerSubDomains, peerSignatures, err = 
			createPeerSubDomains(instance, enrString, peers, modeStr)
		if err != nil {
			return onError(errors.New("Failed to add peers"), onErr, userData)			
		}
	}

	tx, err := makeTxOrder(instance, proofBytes, idStr, nodeEnr, timestampStr,
						url, peerSubDomains, peerSignatures, modeStr)
	if err != nil {
		return onError(errors.New("Cannot create order "), onErr, userData)
	}

	_, err = instance.rpc.BroadcastTxAsync(c, tx)

	return onError(nil, onErr, userData)
}

//export Query
func Query(ctx unsafe.Pointer, path *C.char, key *C.char, cb C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	instance, err := getInstance(ctx)
	if err != nil {
		return onError(errors.New("Cannot stop"), cb, userData)
	}

	c := context.Background()

	abciPath := C.GoString(path)
	abciKey := []byte(C.GoString(key))

	result, err := queryKV(instance, c, abciPath, abciKey)
	return onSuccesfulResponse(result, cb, userData)
}

func queryKV(instance *ConsensusInstance, c context.Context,
		path string, key []byte) (string, error) {

	qres, err := instance.rpc.ABCIQuery(c, path, key)
	if err != nil {
		return "", errors.New("Cannot query")
	}

	if qres.Response.IsErr() {
		return "", errors.New("Query response error")
	}
	if !bytes.Equal(qres.Response.Key, key) {
		return "", errors.New("returned key does not match queried key")
	}
	
	result := string(qres.Response.Value)
	return result, nil
}

func createPeerGroup(seq uint, domain string, privKey *ecdsa.PrivateKey,
	pAddrs [][]ma.Multiaddr, pIds []peer.ID, sharedKey *ecdsa.PrivateKey, 
	nodeEnr string) (string, string, []string, error) {

    // TODO: use safe int64 to uint
    var url string
    var subDomains []string		
	url, subDomains = createLocalPeer(seq, domain, privKey,
						pAddrs, pIds, sharedKey)

	fmt.Println("URL:", url)
	fmt.Println("subDomains:", subDomains)

	nodeAddrInfo, err := EnodeToPeerInfo(nodeEnr)
	if err != nil {
		return "", "", nil, err
	}

    var newNodeEnr string

	newNodeEnr, err = createLocalRegisterPeer(seq, domain, 
		nodeAddrInfo.Addrs,  nodeAddrInfo.ID, sharedKey)		
	fmt.Println("newNodeEnr:", newNodeEnr)
	fmt.Println("\n\nENRR:", CreatePeerSubDomain(newNodeEnr))

	return newNodeEnr, url, subDomains, nil
}

func createPeerSubDomains(instance *ConsensusInstance, nodeEnr string, peers *C.char,
	mode string) (string, string, []string, []string, error) {

	var idleCutoffTime time.Time
	c := context.Background()

	block, err := instance.rpc.Block(c, &instance.height)
	if err == nil {
		blockTime := block.Block.Header.Time
		blockInterval := instance.config.Consensus.TimeoutCommit
		graceTime := blockInterval * IdleCutOffPercentage/100
		idleCutoffTime = blockTime.Add(blockInterval-graceTime)
		fmt.Println("blockTime:", blockTime)
		fmt.Println("blockInterval:", blockInterval)
		fmt.Println("graceTime:", graceTime)
		fmt.Println("idleCutoffTime:", idleCutoffTime)
	}

	qres, err := instance.rpc.Validators(c, nil, nil, nil)
	fmt.Println("qres:", qres)
	fmt.Println("instance.key.Address:", instance.key.Address)

/*	if err != nil {
		return "", "", []string{}, errors.New("Cannot query validators")
	}

	if qres.Count == 0 || qres.Total == 0 {
		return "", "", []string{}, errors.New("ABCIQuery failed")
	}
	if !bytes.Equal(qres.Response.Key, "validators") {
		return "", "", []string{}, errors.New("returned key does not match queried key")
	}
	
	var validatorAddr []byte
	lastCommitHeight := block.Block.LastCommit.Height
	validatorsSig := block.Block.LastCommit.Signatures
	for i, validator := range(validatorsSig) {
		validatorAddr = validator.ValidatorAddress
		if len(validatorAddr) != 20 {
			continue
		}
	}
*/

	var peerIds []Peer
	peerList := C.GoString(peers)

	if len(peerList) == 0 {
		return "", "", nil, nil, errors.New("Peers not provided")
	}

	err = json.Unmarshal([]byte(peerList), &peerIds)
	if err != nil {
		fmt.Println("err:", err)
		return "", "", nil, nil, errors.New("Parsing peers failed")
	}

	var pAddrs [][]ma.Multiaddr
	var pIds []peer.ID
	var pSignatures []string

	for i, p := range peerIds {
        fmt.Printf("Peer %d:\n", i+1)
        fmt.Printf("  PeerID: %s\n", p.ID)
        fmt.Printf("  Protocols: %v\n", p.Protocols)
        fmt.Printf("  Addrs: %v\n", p.Addrs)
        fmt.Printf("  Connected: %v\n", p.Connected)
        fmt.Printf("  PubsubTopics: %v\n", p.PubsubTopics)
        fmt.Printf("  Timestamp: %v\n", p.Timestamp)
        fmt.Printf("  Signature: %v\n", p.Signature)

        //if idleCutoffTime != (0 * time.Second) {
	        //if p.Timestamp.Compare(idleCutoffTime) >= 0  {
	        //	pAddrs = append(pAddrs, p.Addrs)
	        //}        	
        //} else {
	        pAddrs = append(pAddrs, p.Addrs)        
	        pIds = append(pIds, p.ID)        	
	        pSignatures = append(pSignatures, p.Signature)
        //}
    }

    var domain string 
	var newNodeEnr string
    var url string
    var subDomains []string		

	if mode == "solo" {
		domain = "nodes.restaurant.idle.com"
	} else if mode == "assist" {
		domain = "nodes.restaurant.assist.com"
		// check for signature
	} else {
		return "", "", nil, nil, errors.New("Invalid mode") 		
	}

	newNodeEnr, url, subDomains, err = createPeerGroup(
		uint(instance.height), domain, 
		instance.key.PrivateKeyEcdsa,
		pAddrs, pIds, instance.sharedKey,
		nodeEnr)

	return newNodeEnr, url, subDomains, pSignatures, err 
}

func extractBlockFromTxEvent(data types.EventDataNewBlock) (*NewBlock, error) {
	block := data.Block
	return &NewBlock{
		Height: block.Header.Height,
		Time: block.Header.Time,
		LastBlockID: block.Header.LastBlockID,
		DataHash: block.Header.DataHash,
		AppHash: block.Header.AppHash,
		ProposerAddress: block.Header.ProposerAddress,
		Signatures: block.LastCommit.Signatures,
	}, nil
}

func extractOrderFromTxEvent(eventType string, events map[string][]string) (*OrderTx, error) {
	var orderInfo OrderInfo
	var status string
	var keysFound uint = 0

	orderInfoKey := eventType + ".orderInfo"
    statusKey := eventType + ".status"

    for key, values := range events {

        if key == orderInfoKey {
        	json.Unmarshal([]byte(values[0]), &orderInfo)
        	keysFound++
        } else if key == statusKey {
        	status = values[0]
        	keysFound++
        }
    }

    if keysFound == 2 {
    	return &OrderTx{ OrderInfo: orderInfo, Status: status }, nil
    }

    return nil, errors.New("No valid keys found in event")
}

func createAndSendSignal(instance *ConsensusInstance, eventType string, msg interface{}) {
	
	fmt.Println("in createAndSendSignal:", eventType)
	if eventType == "NewBlock" {
		data := msg.(ctypes.ResultEvent).Data.(types.EventDataNewBlock) 
		
		newBlock, _ := extractBlockFromTxEvent(data)
		
		instance.height = newBlock.Height
		
		sendSignal(instance, "NewBlock", newBlock)

	} else if eventType == CheckTxEventType {
		events := msg.(CheckTxEvent).Events
		
		order, err := extractOrderFromTxEvent(eventType, events)
		if err != nil {
			return
		}

		sendSignal(instance, eventType, order)

	} else if eventType == DeliverTxEventType {
		fmt.Println("\nmsg deliver:")
		events := msg.(ctypes.ResultEvent).Events
		
		order, err := extractOrderFromTxEvent(eventType, events)
		if err != nil {
			return
		}

		sendSignal(instance, eventType, order)
	}
}

func (instance *ConsensusInstance) listenOnEvents() {
	for {
		select {
		case <-instance.ctx.Done():
			return
		case msg := <-instance.subscription.newBlockCh:
			fmt.Println("CH0 EVENT:", msg.Query)

			if msg.Query == "tm.event='NewBlock'" {
				instance.height = msg.Data.(types.EventDataNewBlock).Block.Height
				createAndSendSignal(instance, "NewBlock", msg)
			}

		case msg := <-instance.subscription.deliverTxCh:
			fmt.Println("CH1 EVENT:", msg.Query)

			if msg.Query == "tm.event='Tx' AND " + DeliverTxEventType + " EXISTS" {
				fmt.Println("\norder.tx.deliver = solo.done\n")
				createAndSendSignal(instance, DeliverTxEventType, msg)			
			}

		case msg := <-instance.subscription.checkTxCh:
			fmt.Println("CH3 EVENT:", msg.Query)

			if msg.Query == "tm.event='Tx' AND "+ CheckTxEventType + " EXISTS" {
				createAndSendSignal(instance, CheckTxEventType, msg)	
			}
		}			
	}
}

func getInstance(ctx unsafe.Pointer) (*ConsensusInstance, error) {
	cInstanceMutex.RLock()
	defer cInstanceMutex.RUnlock()

	pid := (*uint)(ctx)
	if pid == nil {
		return nil, errors.New("invalid context")
	}

	instance, ok := cInstances[*pid]
	if !ok {
		return nil, errors.New("instance not found")
	}

	return instance, nil
}

func sendSignal(instance *ConsensusInstance, eventType string, event interface{}) {
	signal := SignalData{
		Type: eventType,
		Event: event,
	}
	data, err := json.Marshal(&signal)
	if err != nil {
		fmt.Println("marshal signal error", err)
		return
	}

	dataStr := string(data)
	str := C.CString(dataStr)
	C.ConsensusSendSignal(instance.cb, str)
	C.free(unsafe.Pointer(str))
}

func makeTxOrder(instance *ConsensusInstance, proof []byte, id string,
	enr string, timestamp string, url string, peerSubDomains []string,
	peerSignatures []string, mode string) ([]byte, error) {
	
	var req *SyncRequest
	var peers Peers

	if len(url) != 0 && len(peerSubDomains) != 0 {
		if mode == "assist" {
			peers = Peers{ Url: url, SubDomain: peerSubDomains,
					   Approval: &Approval{ Signature: peerSignatures } }
		} else {
			peers = Peers{ Url: url, SubDomain: peerSubDomains }
		}
	}

	req = &SyncRequest{
		Type: &SyncRequest_Order{
				Order: &OrderRequest{
					Proof: &Proof{Buf: proof},
					Timestamp: &Timestamp{Now: timestamp},
					Inference: &Inference{Mode: mode},
					Identity: &Identity{ID: id, ENR: enr, Bundle: instance.bundle},
					Peers: &peers,
				},
		},
	}

	tx, err := proto.Marshal(req)

	return tx, err
}


func newTendermint(instance *ConsensusInstance, app abci.Application) (*nm.Node, error) {
	// read config
	config := cfg.DefaultConfig()

	dir := filepath.Join(instance.rootDir, "/config/config.toml")	

	viper.SetConfigFile(dir)
	if err := viper.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("viper failed to read config file: %w", err)
	}
	if err := viper.Unmarshal(config); err != nil {
		return nil, fmt.Errorf("viper failed to unmarshal config: %w", err)
	}

	config.RootDir = instance.rootDir
	config.SetRoot(config.RootDir)
	
	config.Consensus.CreateEmptyBlocks = false
	config.Consensus.TimeoutCommit = (10 * time.Second)

	if err := config.ValidateBasic(); err != nil {
		return nil, fmt.Errorf("config is invalid: %w", err)
	}

	// create logger
	logger := log.NewTMLogger(log.NewSyncWriter(os.Stdout))
	var err error
	logger, err = tmflags.ParseLogLevel(config.LogLevel, logger, cfg.DefaultLogLevel)
	if err != nil {
		return nil, fmt.Errorf("failed to parse log level: %w", err)
	}

	// read private validator
	pv := privval.LoadFilePV(
	config.PrivValidatorKeyFile(),
	config.PrivValidatorStateFile(),
	)

	// read node key
	nodeKey, err := p2p.LoadNodeKey(config.NodeKeyFile())
	if err != nil {
		return nil, fmt.Errorf("failed to load node's key: %w", err)
	}

	// create node
	node, err := nm.NewNode(
	config,
	pv,
	nodeKey,
	proxy.NewLocalClientCreator(app),
	nm.DefaultGenesisDocProviderFunc(config),
	nm.DefaultDBProvider,
	nm.DefaultMetricsProvider(config.Instrumentation),
	logger)
	if err != nil {
		fmt.Println("ERROR:", err)
		return nil, fmt.Errorf("failed to create new Tendermint node: %w", err)
	}

	instance.config = config

	return node, nil
}

func buildBundleSignMaterial(bundle *Bundle) []byte {
	signedPreKeys := bundle.GetSignedPreKeys()
	timestamp := bundle.GetTimestamp()
	var keys []string

	for k := range signedPreKeys {
		keys = append(keys, k)
	}
	var sMaterial []byte

	sort.Strings(keys)

	for _, instalID := range keys {
		signedPreKey := signedPreKeys[instalID]
		sMaterial = append(sMaterial, []byte(instalID)...)
		sMaterial = append(sMaterial, signedPreKey.SignedPreKey...)
	}

	if timestamp != 0 {
		sMaterial = append(sMaterial, []byte(strconv.FormatInt(timestamp, 10))...)
	}

	return sMaterial
}

func signBundle(identity *ecdsa.PrivateKey, bundle *Bundle) error {
	bundle.Timestamp = time.Now().UnixNano()
	sMaterial := buildBundleSignMaterial(bundle)

	signature, err := crypto.Sign(crypto.Keccak256(sMaterial), identity)
	if err != nil {
		return err
	}
	bundle.Signature = signature
	return nil
}

func createBundle(identity *ecdsa.PrivateKey, installationID string) (*Bundle, error) {
	preKey, err := crypto.GenerateKey()
	if err != nil {
		return nil, err
	}

	compressedPreKey := crypto.CompressPubkey(&preKey.PublicKey)
	compressedIdentityKey := crypto.CompressPubkey(&identity.PublicKey)

	signedPreKeys := make(map[string]*SignedPreKey)
	signedPreKeys[installationID] = &SignedPreKey{
		SignedPreKey: compressedPreKey,
	}

	bundle := &Bundle{
		Identity: compressedIdentityKey,
		SignedPreKeys: signedPreKeys,
		Timestamp: time.Now().UnixNano(),
	}

	err = signBundle(identity, bundle)
	if err != nil {
		return nil, errors.New("Failed to sign bundle")	
	}

	return bundle, nil
}