package main

import (
    "fmt"
    "net"
    "bytes"
    "encoding/base64"
    "crypto/ecdsa"
    "github.com/ethereum/go-ethereum/p2p/enr"
    "github.com/ethereum/go-ethereum/p2p/enode"
    "github.com/ethereum/go-ethereum/crypto"
    "github.com/ethereum/go-ethereum/p2p/dnsdisc"
)

func createENR(privateKey *ecdsa.PrivateKey, ip net.IP, udpPort, tcpPort uint16) (*enr.Record, error) {
    record := &enr.Record{}
    record.Set(enr.IP(ip))
    record.Set(enr.UDP(udpPort))
    record.Set(enr.TCP(tcpPort))
    
    // Set the public key in the record
    pubkey := &privateKey.PublicKey
    record.Set(enr.WithEntry("secp256k1", base64.RawURLEncoding.EncodeToString(crypto.CompressPubkey(pubkey))))

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
        {"127.0.0.60", 60000, 60000}, //L1
        {"127.0.0.61", 60001, 60001}, //L2
        {"127.0.0.62", 60002, 60002}, //L3
        {"127.0.0.63", 60003, 60003}, //L4
    }
    domain := "nodes.restaurants.com"
    seq := uint(1)

    signingKey, _ := crypto.GenerateKey()
    //pubKey := base32.StdEncoding.EncodeToString(crypto.CompressPubkey(&signingKey.PublicKey))

    var leafRecords []string

    for _, node := range nodes {

        key, _ := crypto.GenerateKey()
        record, _ := createENR(key, net.ParseIP(node.ip), node.udpPort, node.tcpPort)

        leaf, _ := encodeENRToLeaf(record)

        leafRecords = append(leafRecords, leaf)
        fmt.Println("leaf:", leaf)
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

