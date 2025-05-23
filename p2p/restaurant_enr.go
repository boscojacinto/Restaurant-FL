package main

import (
    "fmt"
    "net"
    "bytes"
    "encoding/base64"
    "encoding/hex"
    "crypto/ecdsa"
    "github.com/ethereum/go-ethereum/p2p/enr"
    "github.com/ethereum/go-ethereum/p2p/enode"
    "github.com/ethereum/go-ethereum/crypto"
    "github.com/ethereum/go-ethereum/p2p/dnsdisc"
    "github.com/libp2p/go-libp2p/core/peer"
    "github.com/decred/dcrd/dcrec/secp256k1/v4"
    p2pcrypto "github.com/libp2p/go-libp2p/core/crypto"
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

func main() {
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

