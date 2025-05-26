package rsenr

import (
    "fmt"
    "net"
    "bytes"
    "crypto/ecdsa"
    "encoding/hex"
    "encoding/base64"
    "github.com/libp2p/go-libp2p/core/peer"
    p2pcrypto "github.com/libp2p/go-libp2p/core/crypto"
    "github.com/decred/dcrd/dcrec/secp256k1/v4"
    "github.com/ethereum/go-ethereum/p2p/enr"
    "github.com/ethereum/go-ethereum/p2p/enode"
    "github.com/ethereum/go-ethereum/crypto"
    "github.com/ethereum/go-ethereum/p2p/dnsdisc"
)

func createENR(privateKey *ecdsa.PrivateKey, ip net.IP, udpPort, tcpPort uint16) (*enr.Record, error) {
    var flags uint8
    record := &enr.Record{}
    record.Set(enr.IPv4(ip))
    record.Set(enr.TCP(tcpPort))
    //record.Set(enr.UDP(0))

    //flags |= (1 << 3) // lightpush
    //flags |= (1 << 2) // filter
    flags |= (1 << 1) // store
    flags |= (1 << 0) // relay
    record.Set(enr.WithEntry("waku2", flags))

    // Sign the record
    enode.SignV4(record, privateKey)
    
    //signature := record.Signature()

    if err := record.VerifySignature(enode.V4ID{}); err != nil {
        fmt.Println("Error")
        return nil, err
    }

    return record, nil
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

func main1() {
    type Node struct {
        ip string
        udpPort int
        tcpPort int
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

