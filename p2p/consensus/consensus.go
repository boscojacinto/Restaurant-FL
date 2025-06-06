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
 "flag"
 "time"
 "bytes"
 "sync"
 "unsafe"
 "errors"
 "context"
 "crypto/ecdsa"
 "path/filepath"
 "encoding/json"
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

type ConsensusInstance struct {
	ctx context.Context
	cancel context.CancelFunc
	ID uint
	configFile string
	orderDb *badger.DB
	registerDb *badger.DB 
	node *nm.Node
	rpc *rpclocal.Local
	cb unsafe.Pointer	
	subscription EventListener
	config *cfg.Config // Do not access after stopping node
	height int64 
	key *ecdsa.PrivateKey
	sharedKey *ecdsa.PrivateKey
}

type EventListener struct {
	ctx context.Context
	eventCh <-chan ctypes.ResultEvent
}

type SignalData struct {
	Type  string      `json:"type"`
	Event interface{} `json:"event"`
}

type SignalNewBlock struct {
	Height int64 `json:"height"`
}

type Peer struct {
	ID           peer.ID        `json:"peerID"`
	Protocols    []protocol.ID  `json:"protocols"`
	Addrs        []ma.Multiaddr `json:"addrs"`
	Connected    bool           `json:"connected"`
	PubsubTopics []string       `json:"pubsubTopics"`
	IdleTimestamp time.Time     `json:"idleTimestamp"`
}

const Version = "1.0.0"
const IdleCutOffPercentage = 5

var cInstances map[uint]*ConsensusInstance
var cInstanceMutex sync.RWMutex

func main() {}

//export Init
func Init(configPath *C.char, key *C.char) unsafe.Pointer {
	cInstanceMutex.Lock()
	defer cInstanceMutex.Unlock()

	cid := C.malloc(C.size_t(unsafe.Sizeof(uintptr(0))))
	pid := (*uint)(cid)
	cInstances = make(map[uint]*ConsensusInstance)
	cInstance := &ConsensusInstance{
		ID: uint(len(cInstances)),
	}
	cInstance.key, _ = crypto.ToECDSA([]byte (C.GoString(key)))
	cInstance.sharedKey, _ = crypto.GenerateKey()
	flag.StringVar(&cInstance.configFile, "config", C.GoString(configPath) + "/config.toml", "Path to config.toml")
	cInstances[0] = cInstance
	*pid = cInstance.ID

	return cid
}

//export Start
func Start(ctx unsafe.Pointer, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	instance, err := getInstance(ctx)

	if err != nil {
		return onError(errors.New("Cannot start"), onErr, userData)
	}

	instance.ctx, instance.cancel = context.WithCancel(context.Background())
	dir := filepath.Dir(instance.configFile)	

	orderDb, err := badger.Open(badger.DefaultOptions(dir + "/tmp/order"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open order db: %v", err)
		os.Exit(1)
	}
	instance.orderDb = orderDb

	registerDb, err := badger.Open(badger.DefaultOptions(dir + "/tmp/register"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open register db: %v", err)
		os.Exit(1)
	}
	instance.registerDb = registerDb

	instance.height = 0

	app := NewInferSyncApp(orderDb, registerDb)

	flag.Parse()

	node, err := newTendermint(instance, app)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v", err)
		os.Exit(2)
	}

	instance.node = node 
	instance.rpc = rpclocal.New(node)
	eventCh, _ := instance.rpc.Subscribe(instance.ctx, "tastebot-subscribe", "tm.event='NewBlock'")
	
	instance.subscription = EventListener{
		ctx: instance.ctx,
		eventCh: eventCh,
	}	
	
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
	peers *C.char, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	instance, err := getInstance(ctx)
	if err != nil {
		return onError(errors.New("Cannot stop"), onErr, userData)
	}

	c := context.Background()

	len := C.strlen(proof)
	proofBytes := C.GoBytes(unsafe.Pointer(proof), C.int(len))
	idStr := C.GoString(id)
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	
	var url string
	var subdomains []string

	if unsafe.Pointer(peers) != nil {
		url, subdomains, err = addPeers(instance, peers)
		if err != nil {
			return onError(errors.New("Failed to add peers"), onErr, userData)			
		}
	}

	var enrString string
	if enr != nil {
		enrString = C.GoString(enr)
	}

	tx, err := makeTxOrder(proofBytes, timestamp, idStr,
							enrString, url, subdomains)
	if err != nil {
		return onError(errors.New("Cannot create order "), onErr, userData)
	}

	code, err := instance.rpc.BroadcastTxAsync(c, tx)
	fmt.Println("After BroadcastTxCommit1.0, code:", code)
/*	if !bres.CheckTx.IsOK() {
		err = errors.New("Tx commit error") 
	}

	if !bres.DeliverTx.IsOK() {
		err = errors.New("Tx deliver error") 
	}
*/	//fmt.Println("After BroadcastTxCommit1.1")

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

	qres, err := instance.rpc.ABCIQuery(c, abciPath, abciKey)
	if err != nil {
		return onError(errors.New("Cannot stop"), cb, userData)
	}

	if qres.Response.IsErr() {
		return onError(errors.New("ABCIQuery failed"), cb, userData)
	}
	if !bytes.Equal(qres.Response.Key, abciKey) {
		return onError(errors.New("returned key does not match queried key"), cb, userData)
	}
	
	result := string(qres.Response.Value)
	return onSuccesfulResponse(result, cb, userData)
}

func addPeers(instance *ConsensusInstance, peers *C.char) (string, []string, error) {

	c := context.Background()

	block, err := instance.rpc.Block(c, &instance.height)
	if err != nil {
		return "", []string{}, errors.New("Cannot get block")		
	}

	if block.Block == nil {
		return "", []string{}, errors.New("Block is empty")		
	}

	blockTime := block.Block.Header.Time
	fmt.Println("blockTime:", blockTime)

	blockInterval := instance.config.Consensus.TimeoutCommit
	fmt.Println("blockInterval:", blockInterval)
	graceTime := blockInterval * IdleCutOffPercentage/100
	fmt.Println("graceTime:", graceTime)
	idleCutoffTime := blockTime.Add(blockInterval-graceTime)

	fmt.Println("idleCutoffTime:", idleCutoffTime)

	var peerIds []Peer
	peer_list := C.GoString(peers)

	err = json.Unmarshal([]byte(peer_list), &peerIds)
	if err != nil {
		fmt.Println("err:", err)
		errors.New("Parsing peers failed")
	}

	var pAddrs [][]ma.Multiaddr

	for i, p := range peerIds {
        fmt.Printf("Peer %d:\n", i+1)
        fmt.Printf("  PeerID: %s\n", p.ID)
        fmt.Printf("  Protocols: %v\n", p.Protocols)
        fmt.Printf("  Addrs: %v\n", p.Addrs)
        fmt.Printf("  Connected: %v\n", p.Connected)
        fmt.Printf("  PubsubTopics: %v\n", p.PubsubTopics)
        fmt.Printf("  IdleTimestamp: %v\n", p.IdleTimestamp)

        if p.IdleTimestamp.Compare(idleCutoffTime) >= 0  {
        	pAddrs = append(pAddrs, p.Addrs)
        }
    }

    // TODO: use safe int64 to uint
	url, subdomains, _ := createLocalPeer(uint(instance.height), 
	"nodes.restaurant.idle.com", instance.key, pAddrs, instance.sharedKey)

	fmt.Println("URL:", url)
	fmt.Println("Subdomains:", subdomains)
	//fmt.Println("sEnrs:", sEnrs)

	return url, subdomains, nil 
}

func (instance *ConsensusInstance) listenOnEvents() {
	for {
		select {
		case <-instance.ctx.Done():
			return
		case msg := <-instance.subscription.eventCh:
			fmt.Println("EVENT:", msg.Query)
			if msg.Query == "tm.event='NewBlock'" {
				block := msg.Data.(types.EventDataNewBlock).Block
				height := block.Height
				instance.height = height
				signal := SignalNewBlock{
					Height: height,
				}
				sendSignal(instance, "NewBlock", signal)
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

func makeTxOrder(proof []byte, time string, id string,
	enr string, url string, subdomains []string) ([]byte, error) {
	
	var identity Identity
	var idlePeers IdlePeers

	if len(enr) != 0 {
		identity = Identity{ID: id, ENR: &enr}
	} else {
		identity = Identity{ID: id}		
	}

	if len(url) != 0 && len(subdomains) != 0 {
		idlePeers = IdlePeers{Url: url, SubDomain: subdomains}
	}

	req := &SyncRequest{
		Type: &SyncRequest_Order{
				Order: &OrderRequest{
					Proof: &Proof{Buf: proof},
					Timestamp: &Timestamp{Now: time},
					Identity: &identity,
					IdlePeers: &idlePeers,
				},
			},
		}
	tx, err := proto.Marshal(req)

	return tx, err
}


func newTendermint(instance *ConsensusInstance, app abci.Application) (*nm.Node, error) {
	// read config
	config := cfg.DefaultConfig()
	config.RootDir = filepath.Dir(filepath.Dir(instance.configFile))
	config.Consensus.CreateEmptyBlocks = false
	config.Consensus.TimeoutCommit = (10 * time.Second)

	viper.SetConfigFile(instance.configFile)
	if err := viper.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("viper failed to read config file: %w", err)
	}
	if err := viper.Unmarshal(config); err != nil {
		return nil, fmt.Errorf("viper failed to unmarshal config: %w", err)
	}
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
		return nil, fmt.Errorf("failed to create new Tendermint node: %w", err)
	}

	instance.config = config

	return node, nil
}
