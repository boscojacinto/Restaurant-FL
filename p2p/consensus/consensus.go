package main

/*
#include <cgo_utils.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>

// The possible returned values for the functions that return int
static const int RET_OK = 0;
static const int RET_ERR = 1;
static const int RET_MISSING_CALLBACK = 2;

typedef void (*ConsensusCallBack) (int ret_code, const char* msg, void * user_data);
*/
import "C"
import (
 "os"
 "fmt"
 "flag"
 "time"
 "sync"
 "unsafe"
 "errors"
 "context"
 "path/filepath"
 "github.com/dgraph-io/badger"
 "github.com/spf13/viper"

 abci "github.com/tendermint/tendermint/abci/types"
 cfg "github.com/tendermint/tendermint/config"
 tmflags "github.com/tendermint/tendermint/libs/cli/flags"
 "github.com/tendermint/tendermint/libs/log"
 nm "github.com/tendermint/tendermint/node"
 "github.com/tendermint/tendermint/p2p"
 "github.com/tendermint/tendermint/privval"
 "github.com/tendermint/tendermint/proxy"
 rpclocal "github.com/tendermint/tendermint/rpc/client/local"
 "google.golang.org/protobuf/proto"
)

type ConsensusInstance struct {
	ctx context.Context
	cancel context.CancelFunc
	ID uint
	configFile string
	db *badger.DB 
	node *nm.Node
	rpc *rpclocal.Local	
}

const Version = "1.0.0"

var cInstances map[uint]*ConsensusInstance
var cInstanceMutex sync.RWMutex

func main() {}

//export Init
func Init(configPath *C.char) unsafe.Pointer {
	cInstanceMutex.Lock()
	defer cInstanceMutex.Unlock()

	cid := C.malloc(C.size_t(unsafe.Sizeof(uintptr(0))))
	pid := (*uint)(cid)
	cInstances = make(map[uint]*ConsensusInstance)
	cInstance := &ConsensusInstance{
		ID: uint(len(cInstances)),
	}
	
	flag.StringVar(&cInstance.configFile, "config", C.GoString(configPath) + "/config.toml", "Path to config.toml")
	cInstances[0] = cInstance
	///home/boscojacinto/projects/TasteBot/Restaurant-FL/p2p/consensus/config/config.toml
	fmt.Println("Config File:", cInstance.configFile)
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

	db, err := badger.Open(badger.DefaultOptions(dir + "/tmp/badger"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open badger db: %v", err)
		os.Exit(1)
	}

	instance.db = db

	app := NewInferSyncApp(db)

	flag.Parse()

	node, err := newTendermint(app, instance.configFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v", err)
		os.Exit(2)
	}

	instance.node = node 
	instance.rpc = rpclocal.New(node)
	//			   instance.rpc.Subscribe(instance.ctx, "tm.event = 'NewBlock'")	
	instance.node.Start()
	return onError(nil, onErr, userData)
}

//export Stop
func Stop(ctx unsafe.Pointer, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	instance, err := getInstance(ctx)
	if err != nil {
		return onError(errors.New("Cannot stop"), onErr, userData)
	}

	instance.db.Close()

	instance.node.Stop()
	instance.node.Wait()

	return onError(nil, onErr, userData)
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

func makeTxOrder(proof []byte, time string, identity string) ([]byte, error) {
	
	req := &SyncRequest{
		Type: &SyncRequest_Order{
				Order: &OrderRequest{
					Proof: &Proof{Buf: proof},
					Timestamp: &Timestamp{Now: time},
					Identity: &Identity{PublicKey: identity},
				},
			},
		}
	tx, err := proto.Marshal(req)

	return tx, err
}

//export SendOrder
func SendOrder(ctx unsafe.Pointer, proof *C.char, onErr C.ConsensusCallBack, userData unsafe.Pointer) C.int {

	instance, err := getInstance(ctx)
	if err != nil {
		return onError(errors.New("Cannot stop"), onErr, userData)
	}

	c := context.Background()

	len := C.strlen(proof)
	proofBytes := C.GoBytes(unsafe.Pointer(proof), C.int(len))
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	identity := "4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5"

	tx, err := makeTxOrder(proofBytes, timestamp, identity)
	if err != nil {
		return onError(errors.New("Cannot create order "), onErr, userData)
	}

	code, err := instance.rpc.BroadcastTxAsync(c, tx) //BroadcastTxCommit(c, tx)
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

func newTendermint(app abci.Application, configFile string) (*nm.Node, error) {
	// read config
	config := cfg.DefaultConfig()
	config.RootDir = filepath.Dir(filepath.Dir(configFile))
	viper.SetConfigFile(configFile)
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

	return node, nil
}
