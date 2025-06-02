package main

import (
    "fmt"
    "io"
    "net"
    "bytes"
    "time"
    "context"
    "strconv"
    "encoding/base32"
    "encoding/base64"    
    "encoding/hex"
    "crypto/ecdsa"
    "crypto/rand"  
    "golang.org/x/crypto/sha3"      
    "github.com/ethereum/go-ethereum/p2p/enr"
    "github.com/ethereum/go-ethereum/p2p/enode"
    "github.com/ethereum/go-ethereum/crypto"
    "github.com/ethereum/go-ethereum/crypto/ecies"
    "github.com/ethereum/go-ethereum/p2p/dnsdisc"
    "github.com/libp2p/go-libp2p/core/peer"
    "github.com/decred/dcrd/dcrec/secp256k1/v4"
    p2pcrypto "github.com/libp2p/go-libp2p/core/crypto"
    ma "github.com/multiformats/go-multiaddr"
)

/*hostAddr, err := net.ResolveTCPAddr("tcp", fmt.Sprintf("%s:%d", *config.Host, *config.Port))
params.hostAddr = hostAddr
hostAddrMA, err := manet.FromNetAddr(hostAddr)
params.multiAddr = append(params.multiAddr, hostAddrMA)
*/
func createENR(privateKey *ecdsa.PrivateKey, ip net.IP, udpPort, tcpPort uint16) (*enr.Record, error) {
    var flags uint8
    record := &enr.Record{}
    fmt.Println("ip:", ip)
    record.Set(enr.IPv4(ip))
    //record.Set(enr.TCP(udpPort))
    record.Set(enr.TCP(tcpPort))
    //flags |= (1 << 3) // lightpush
    //flags |= (1 << 2) // filter
    flags |= (1 << 1) // store
    flags |= (1 << 0) // relay
    record.Set(enr.WithEntry("waku2", flags))
    
/*    // Set the public key in the record
    pubkey := &privateKey.PublicKey
    record.Set(enr.WithEntry("secp256k1", base64.RawURLEncoding.EncodeToString(crypto.CompressPubkey(pubkey))))
*/
    // Sign the record
    enode.SignV4(record, privateKey)
    
    //signature := record.Signature()

    if err := record.VerifySignature(enode.V4ID{}); err != nil {
        fmt.Println("Error")
        return nil, err
    }

    return record, nil
}

func encodeENRToLeaf(record *enr.Record) (string, error) {
    var buf bytes.Buffer
    if err := record.EncodeRLP(&buf); err != nil {
        return "", err
    }

    return "enr:" + base64.RawURLEncoding.EncodeToString(buf.Bytes()), nil
}

func createNodes(rec []string) []*enode.Node {
    fmt.Println()
    var ns []*enode.Node
    for _, r := range rec {
        var n enode.Node
        if err := n.UnmarshalText([]byte(r)); err != nil {
            fmt.Println("Error creating node:", err)
        }
        ns = append(ns, &n)
    }
    return ns
}

func createLocalNode(privateKey *ecdsa.PrivateKey, ip net.IP, udpPort, tcpPort int) (*enode.Node, error) {
    ipAddr := &net.TCPAddr{
        IP:   ip,
        Port: tcpPort,
    }
    
    db, _ := enode.OpenDB("")
    
    localnode := enode.NewLocalNode(db, privateKey)
    localnode.SetStaticIP(ipAddr.IP)
    localnode.Set(enr.TCP(uint16(ipAddr.Port)))
    localnode.SetFallbackIP(net.IP{127, 0, 0, 1})
    localnode.SetFallbackUDP(0)

    var flags uint8
    flags |= (1 << 1) // store
    flags |= (1 << 0) // relay    
    localnode.Set(enr.WithEntry("waku2", flags))

    return localnode.Node(), nil
}

func CreateTree() {
    type Node struct {
        ip string
        udpPort uint16
        tcpPort uint16
    }

    nodes := []Node{
        {"192.168.1.26", 60000, 60000}, //L1
        {"192.168.1.26", 60001, 60001}, //L2
        {"192.168.1.26", 60002, 60002}, //L3
        {"192.168.1.26", 60003, 60003}, //L4
    }
    domain := "nodes.restaurants.com"
    seq := uint(1)

    signingKey, _ := crypto.GenerateKey()

    var leafRecords []string

    for _, node := range nodes {

        key, _ := crypto.GenerateKey()        
        record, _ := createENR(key, net.ParseIP(node.ip), node.udpPort, node.tcpPort)
        p2pKey := (*p2pcrypto.Secp256k1PrivateKey)(secp256k1.PrivKeyFromBytes(key.D.Bytes()))
        peerId, _ := peer.IDFromPublicKey(p2pKey.GetPublic())

        leaf, _ := encodeENRToLeaf(record)
        fmt.Println("\nnode:", node)
        fmt.Println("PrivateKey:" + "0x" + hex.EncodeToString(crypto.FromECDSA(key)))
        fmt.Println("PeerId:", peerId)
        fmt.Println("Enr:", leaf)

        leafRecords = append(leafRecords, leaf)
    }

    eNodes := createNodes(leafRecords)
    tree, err := dnsdisc.MakeTree(seq, eNodes, nil)
    if err != nil {
        fmt.Println("Error making tree:", err)
    }

    url, err := tree.Sign(signingKey, domain)
    if err != nil {
        fmt.Printf("Error signing tree:", err)
    }

    fmt.Println("url:", url)
    fmt.Println(tree.ToTXT(domain))
}

func CreateTreeFromLocalNode() {
    type Node struct {
        ip string
        udpPort int
        tcpPort int
    }

    nodes := []Node{
        {"192.168.1.26", 60000, 60000}, //L1
        {"192.168.1.26", 60001, 60001}, //L2
    }
    domain := "nodes.restaurants.com"
    seq := uint(1)

    signingKey, _ := crypto.GenerateKey()

    var eNodes [](*enode.Node)

    for _, node := range nodes {

        key, _ := crypto.GenerateKey()
        leaf, _ := createLocalNode(key, net.ParseIP(node.ip), node.udpPort, node.tcpPort)
        p2pKey := (*p2pcrypto.Secp256k1PrivateKey)(secp256k1.PrivKeyFromBytes(key.D.Bytes()))
        peerId, _ := peer.IDFromPublicKey(p2pKey.GetPublic())
        fmt.Println("\nnode:", node)
        fmt.Println("PrivateKey:" + "0x" + hex.EncodeToString(crypto.FromECDSA(signingKey)))
        fmt.Println("PeerId:", peerId)
        fmt.Println("Enr:", leaf)
 
        eNodes = append(eNodes, leaf)
    }

    //eNodes := createNodes(leafRecords)
    
    tree, err := dnsdisc.MakeTree(seq, eNodes, nil)
    if err != nil {
        fmt.Println("Error making tree:", err)
    }

    url, err := tree.Sign(signingKey, domain)
    if err != nil {
        fmt.Printf("Error signing tree:", err)
    }

    fmt.Println("url:", url)
    fmt.Println(tree.ToTXT(domain))
}

func TestTree() {
    fmt.Println("hello")

    resolver := &net.Resolver{
        PreferGo: false, // Use Go's DNS resolver instead of the system's
        Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
            // Dial 192.168.1.26:53 for DNS queries
            d := net.Dialer{
                Timeout: 20 * time.Second, // Set a timeout for DNS queries
            }
            conn, err := d.DialContext(ctx, "udp", "192.168.1.26:53")
            fmt.Println("RET:", conn)
            return conn, err
        },
    }

    client := dnsdisc.NewClient(dnsdisc.Config{Resolver: resolver})

    domain, pubkey, err := dnsdisc.ParseURL("enrtree://ANXEZXZA6FE7C56VORF77F2ZLCD72U3QST4XD27EWBOSXVKLIDLRC@nodes.restaurants.com") //enrtree://AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI@test.waku.nodes.status.im
    if err != nil {
        fmt.Println("Error resolving enrtree:", err)
        return
    }
    fmt.Println("domain:", domain)
    fmt.Println("pubkey:", pubkey)
          
/*    txts, err := client.cfg.Resolver.LookupTXT("FDXN3SN67NA5DKA4J2GOK7BVQI.nodes.restaurants.com")
    fmt.Println("txts:", txts)
*/                                          //AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI
    tree, err := client.SyncTree("enrtree://ANXEZXZA6FE7C56VORF77F2ZLCD72U3QST4XD27EWBOSXVKLIDLRC@nodes.restaurants.com") //enrtree://AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI@test.waku.nodes.status.im
    if err != nil {
        fmt.Println("Error syncing enrtree:", err)
        return
    }
    fmt.Println("tree:", tree.ToTXT("nodes.restaurants.com"))

/*    for _, enr := range nodes {
        fmt.Println("Resolved ENR:", enr.String())
    }
*/}

func extractIP(addr ma.Multiaddr) (*net.TCPAddr, error) {
    ipStr, err := addr.ValueForProtocol(ma.P_IP4)
    if err != nil {
        return nil, err
    }

    portStr, err := addr.ValueForProtocol(ma.P_TCP)
    if err != nil {
        return nil, err
    }
    port, err := strconv.Atoi(portStr)
    if err != nil {
        return nil, err
    }
    return &net.TCPAddr{
        IP:   net.ParseIP(ipStr),
        Port: port,
    }, nil
}

func createLocalPeer(seq uint, domain string, signingKey *ecdsa.PrivateKey,
    addrs [][]ma.Multiaddr, sharedKeys []*ecdsa.PrivateKey) (string, []string, [][]byte) {

    var enrs []*enode.Node 
    var node *enode.Node
    var tcpAddr *net.TCPAddr
    var err error

    for _, addr := range(addrs) {
        for _, a := range(addr) {
            tcpAddr, err = extractIP(a)
            if err == nil {
                break
            }
        }

        key, _ := crypto.GenerateKey()

        node, err = createLocalNode(key, tcpAddr.IP, 0, tcpAddr.Port)    
        if err == nil {
            enrs = append(enrs, node)
        }
    }

    tree, err := dnsdisc.MakeTree(seq, enrs, nil)
    if err != nil {
        fmt.Println("Error making tree:", err)
    }

    url, err := tree.Sign(signingKey, domain)
    if err != nil {
        fmt.Printf("Error signing tree:", err)
    }

    fmt.Println("url:", url)
    fmt.Println(tree.ToTXT(domain))
    fmt.Println("tree.nodes:", tree.Nodes())    

    b32format := base32.StdEncoding.WithPadding(base32.NoPadding)
    var subdomains []string
    var encyptedEnrs [][]byte

    for _, sKey := range(sharedKeys) {

        eSKey := ecies.ImportECDSA(sKey)
        
        for _, e := range(tree.Nodes()) {

            h := sha3.NewLegacyKeccak256()
            io.WriteString(h, e.String())
            ids := b32format.EncodeToString(h.Sum(nil)[:16]) 
            fmt.Println("ID:", ids)
            subdomains = append(subdomains, ids) 

            enrString, err := e.MarshalText()

            eEnr, err := ecies.Encrypt(rand.Reader, &eSKey.PublicKey, enrString, nil, nil)
            if err != nil {
                panic(err)
            }   
            fmt.Println("eEnr:%x\n", eEnr)            
            encyptedEnrs = append(encyptedEnrs, eEnr)
        }
    }

    return url, subdomains, encyptedEnrs
}