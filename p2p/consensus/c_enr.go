package main

import (
    "fmt"
    "io"
    "net"
    "bytes"
    "time"
    "context"
    "errors"
    "strings"
    "strconv"
    "encoding/base32"
    "encoding/base64"
    "encoding/binary"     
    "encoding/hex"
    "crypto/ecdsa"
    "crypto/sha256"
    "golang.org/x/crypto/sha3"      
    "github.com/ethereum/go-ethereum/p2p/enr"
    "github.com/ethereum/go-ethereum/p2p/enode"
    "github.com/ethereum/go-ethereum/crypto"
    "github.com/ethereum/go-ethereum/p2p/dnsdisc"
    "github.com/libp2p/go-libp2p/core/peer"
    "github.com/decred/dcrd/dcrec/secp256k1/v4"
    p2pcrypto "github.com/libp2p/go-libp2p/core/crypto"
    ma "github.com/multiformats/go-multiaddr"
    "golang.org/x/crypto/ripemd160"    
)

/*hostAddr, err := net.ResolveTCPAddr("tcp", fmt.Sprintf("%s:%d", *config.Host, *config.Port))
params.hostAddr = hostAddr
hostAddrMA, err := manet.FromNetAddr(hostAddr)
params.multiAddr = append(params.multiAddr, hostAddrMA)
*/
func createENR(privateKey *ecdsa.PrivateKey, ip net.IP, udpPort, tcpPort int, seq uint, peerId peer.ID) (*enr.Record, error) {
    //var flags uint8
    record := &enr.Record{}
    fmt.Println("ip:", ip)
    record.Set(enr.IPv4(ip))
    //record.Set(enr.TCP(udpPort))
    record.Set(enr.TCP(tcpPort))
    //flags |= (1 << 3) // lightpush
    //flags |= (1 << 2) // filter
    //flags |= (1 << 1) // store
    //flags |= (1 << 0) // relay
    //record.Set(enr.WithEntry("waku2", flags))
    
    // Set the public key in the record
    pubkey := &privateKey.PublicKey
    record.Set(enr.WithEntry("secp256k1", base64.RawURLEncoding.EncodeToString(crypto.CompressPubkey(pubkey))))

    // Set the waku peerId in the record
    record.Set(enr.WithEntry("waku2-peerid", peerId.String()))

    record.SetSeq(uint64(seq))

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

/*func CreateTree() {
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

    for i, node := range nodes {

        key, _ := crypto.GenerateKey()        
        record, _ := createENR(key, net.ParseIP(node.ip), node.udpPort, node.tcpPort, seq, peer.ID{string(i)})
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
*/
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
    addrs [][]ma.Multiaddr, peerIds []peer.ID, sharedKey *ecdsa.PrivateKey) (string, []string) {

    var nodeEnrs []*enode.Node 
    var node *enode.Node
    var tcpAddr *net.TCPAddr
    var nodeRecord *enr.Record
    var err error

    for i, addr := range(addrs) {
        for _, a := range(addr) {
            tcpAddr, err = extractIP(a)
            if err == nil {
                break
            }
        }

        //node, err = createLocalNode(sharedKey, tcpAddr.IP, 0, tcpAddr.Port)    
        nodeRecord, err = createENR(sharedKey, tcpAddr.IP, 0, tcpAddr.Port, seq, peerIds[i])
        node, err = enode.New(enode.V4ID{}, nodeRecord)
        fmt.Println("\ni:", i)
        fmt.Println(" seq:", seq)
        fmt.Println(" peerId:", peerIds[i])
        fmt.Println(" tcpAddr.IP:", tcpAddr.IP)
        fmt.Println(" tcpAddr.Port:", tcpAddr.Port)
        fmt.Println(" node.string():", node.String())
        //node, err = encodeENRToLeaf(nodeRecord)        
        if err == nil {
            nodeEnrs = append(nodeEnrs, node)
        }
    }

    tree, err := dnsdisc.MakeTree(seq, nodeEnrs, nil)
    if err != nil {
        fmt.Println("Error making tree:", err)
    }

    url, err := tree.Sign(signingKey, domain)
    if err != nil {
        fmt.Printf("Error signing tree:", err)
    }

    //fmt.Println(tree.ToTXT(domain))

    b32format := base32.StdEncoding.WithPadding(base32.NoPadding)
    var subDomains []string
    
    for _, enr := range(tree.Nodes()) {

        enrHash := sha3.NewLegacyKeccak256()
        io.WriteString(enrHash, enr.String())
        subdomain := b32format.EncodeToString(enrHash.Sum(nil)[:16]) 
        subDomains = append(subDomains, subdomain)
    }

    return url, subDomains
}

func createLocalRegisterPeer(seq uint, domain string, addr []ma.Multiaddr,
    peerId peer.ID, sharedKey *ecdsa.PrivateKey) (string, error) {

    var node *enode.Node
    var tcpAddr *net.TCPAddr
    var nodeRecord *enr.Record
    var err error

    tcpAddr, err = extractIP(addr[0])
    if err != nil {
        return "", err
    }

    nodeRecord, err = createENR(sharedKey, tcpAddr.IP, 0, tcpAddr.Port, seq, peerId)
    node, err = enode.New(enode.V4ID{}, nodeRecord)
    fmt.Println("\nNODE:")
    fmt.Println(" seq:", seq)
    fmt.Println(" peerId:", peerId)
    fmt.Println(" tcpAddr.IP:", tcpAddr.IP)
    fmt.Println(" tcpAddr.Port:", tcpAddr.Port)
    fmt.Println(" node.string():", node.String())

/*    enrHash := sha3.NewLegacyKeccak256()
    io.WriteString(enrHash, node.String())
    regDomain := b32format.EncodeToString(enrHash.Sum(nil)[:16]) 
*/
    return node.String(), nil
}

func createIDFromSecp256k1Bytes(publicKey []byte) (peer.ID) {

    pubKey, err := p2pcrypto.UnmarshalSecp256k1PublicKey(publicKey)

    if err != nil {
        fmt.Println("ERROR")
        panic(err)
    }

    peerId, err := peer.IDFromPublicKey(pubKey)

    if err != nil {
        fmt.Println("ERROR")
        panic(err)
    }

    return peerId
} 

func createIDFromEcdsaPublicKey(publicKey *ecdsa.PublicKey) (peer.ID, error) {

    pubKey := ecdsaPubKeyToSecp256k1PublicKey(publicKey)
    peerID, err := peer.IDFromPublicKey(pubKey)
    if err != nil {
        return "", err
    }

    return peerID, nil
} 

func isIPv6(str string) bool {
    ip := net.ParseIP(str)
    return ip != nil && strings.Contains(str, ":")
}

func ecdsaPubKeyToSecp256k1PublicKey(pubKey *ecdsa.PublicKey) *p2pcrypto.Secp256k1PublicKey {
    xFieldVal := &secp256k1.FieldVal{}
    yFieldVal := &secp256k1.FieldVal{}
    xFieldVal.SetByteSlice(pubKey.X.Bytes())
    yFieldVal.SetByteSlice(pubKey.Y.Bytes())
    return (*p2pcrypto.Secp256k1PublicKey)(secp256k1.NewPublicKey(xFieldVal, yFieldVal))
}

func enodeToMultiAddr(node *enode.Node) (ma.Multiaddr, error) {
    pubKey := ecdsaPubKeyToSecp256k1PublicKey(node.Pubkey())
    peerID, err := peer.IDFromPublicKey(pubKey)
    if err != nil {
        return nil, err
    }

    ipType := "ip4"
    portNumber := node.TCP()

    if portNumber == 0 {
        return nil, errors.New("port not available")
    }

    if isIPv6(node.IP().String()) {
        ipType = "ip6"
        var port enr.TCP6
        if err := node.Record().Load(&port); err != nil {
            return nil, err
        }
        portNumber = int(port)
    }

    return ma.NewMultiaddr(fmt.Sprintf("/%s/%s/tcp/%d/p2p/%s", ipType, node.IP(), portNumber, peerID))
}

// Multiaddress is used to extract all the multiaddresses that are part of a ENR record
func getMultiaddress(node *enode.Node) (peer.ID, []ma.Multiaddr, error) {
    pubKey := ecdsaPubKeyToSecp256k1PublicKey(node.Pubkey())
    peerID, err := peer.IDFromPublicKey(pubKey)
    if err != nil {
        return "", nil, err
    }

    var result []ma.Multiaddr

    addr, err := enodeToMultiAddr(node)
    if err != nil {
        if !errors.Is(err, errors.New("port not available")) {
            return "", nil, err
        }
    } else {
        result = append(result, addr)
    }

    var multiaddrRaw []byte
    if err := node.Record().Load(enr.WithEntry("multiaddrs", &multiaddrRaw)); err != nil {
        if !enr.IsNotFound(err) {
            return "", nil, err
        }
        // No multiaddr entry on enr
        return peerID, result, nil
    }

    if len(multiaddrRaw) < 2 {
        // There was no error loading the multiaddr field, but its length is incorrect
        return peerID, result, nil
    }

    offset := 0
    for {
        maSize := binary.BigEndian.Uint16(multiaddrRaw[offset : offset+2])
        if len(multiaddrRaw) < offset+2+int(maSize) {
            return "", nil, errors.New("invalid multiaddress field length")
        }
        maRaw := multiaddrRaw[offset+2 : offset+2+int(maSize)]
        addr, err := ma.NewMultiaddrBytes(maRaw)
        if err != nil {
            // The value is not a multiaddress. Ignoring...
            continue
        }

        hostInfoStr := fmt.Sprintf("/p2p/%s", peerID.String())
        _, pID := peer.SplitAddr(addr)
        if pID != "" && pID != peerID {
            // Addresses in the ENR that contain a p2p component are circuit relay addr
            hostInfoStr = "/p2p-circuit" + hostInfoStr
        }

        hostInfo, err := ma.NewMultiaddr(hostInfoStr)
        if err != nil {
            return "", nil, err
        }
        result = append(result, addr.Encapsulate(hostInfo))

        offset += 2 + int(maSize)
        if offset >= len(multiaddrRaw) {
            break
        }
    }

    return peerID, result, nil
}

func EnodeToPeerInfo(enr string) (*peer.AddrInfo, error) {
    var node = new(enode.Node)

    err := node.UnmarshalText([]byte(enr))
    if err != nil {
        return nil, err
    }

    _, addresses, err := getMultiaddress(node)

    if err != nil {
        return nil, err
    }

    res, err := peer.AddrInfosFromP2pAddrs(addresses...)

    if err != nil {
        return nil, err
    }

    if len(res) == 0 {
        return nil, errors.New("could not retrieve peer addresses from enr")
    }
    return &res[0], nil
}

func CheckURL(url string, idStr string) (string, *ecdsa.PublicKey, error) {

    domain, pubkey, err := dnsdisc.ParseURL(url)
    fmt.Println("pubkey:", pubkey)

    if err != nil {
        return "", nil, err
    }

    pubKey := ecdsaPubKeyToSecp256k1PublicKey(pubkey)
    peerId, err := peer.IDFromPublicKey(pubKey)
    fmt.Println("pId:", peerId)

    if err != nil {
        return "", nil, err                
    }

    id, err := peer.Decode(idStr)
    fmt.Println("iid:", id)
    fmt.Println("err:", err)
    if err != nil {
        return "", nil, err
    }

    if peerId != id {
        return "", nil, errors.New("Peer ids dont match")
    }

    return domain, pubkey, nil
}

func CreatePeerSubDomain(enr string) (string) {
    b32format := base32.StdEncoding.WithPadding(base32.NoPadding)
    
    keccak := sha3.NewLegacyKeccak256()
    io.WriteString(keccak, enr)
    peerSubDomain := b32format.EncodeToString(keccak.Sum(nil)[:16])
    return peerSubDomain
}

func validatorKeyFromECDSA(key []byte) (ValidatorKey, error) {
    privateKey := (*p2pcrypto.Secp256k1PrivateKey)(secp256k1.PrivKeyFromBytes(key))    
    privateKeyEcdsa, _ := crypto.ToECDSA(key)
    privateKeyBytes, _ := privateKey.Raw()
    publicKeyBytes, _ := privateKey.GetPublic().Raw()
    //compPubKeyBytes := crypto.CompressPubkey(&privateKey.PublicKey)
    fmt.Printf("Private Key: %s\n", hex.EncodeToString(privateKeyBytes))
    fmt.Printf("Public Key: %s\n", hex.EncodeToString(publicKeyBytes))

    privateKeyBase64 := base64.StdEncoding.EncodeToString(privateKeyBytes)
    publicKeyBase64 := base64.StdEncoding.EncodeToString(publicKeyBytes)
    address := getAddress(publicKeyBytes)

    vKey := ValidatorKey{
        Address: hex.EncodeToString(address),
        PublicKey: publicKeyBase64,
        PrivateKey: privateKeyBase64,
        PrivateKeyEcdsa: privateKeyEcdsa,
    }

    return vKey, nil
}

func getAddress(pubBytes []byte) []byte {
    hasherSHA256 := sha256.New()
    _, _ = hasherSHA256.Write(pubBytes)
    sha := hasherSHA256.Sum(nil)

    hasherRIPEMD160 := ripemd160.New()
    _, _ = hasherRIPEMD160.Write(sha)

    return hasherRIPEMD160.Sum(nil)
}
