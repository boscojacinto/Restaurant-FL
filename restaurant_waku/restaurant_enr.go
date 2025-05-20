package main

import (
    "fmt"
    "net"
    "bytes"
    "strings"
    "encoding/base32"
    "encoding/base64"
    "crypto/ecdsa"
    "github.com/ethereum/go-ethereum/p2p/enr"
    "github.com/ethereum/go-ethereum/p2p/enode"
    "github.com/ethereum/go-ethereum/crypto"
)

type nodeInfo struct {
    privateKey *ecdsa.PrivateKey
    enrRecord  *enr.Record
    node       *enode.Node
}

func createENR(privateKey *ecdsa.PrivateKey, ip net.IP, udpPort, tcpPort uint16) (*enr.Record, error) {
    record := &enr.Record{}
    record.Set(enr.IP(ip))
    record.Set(enr.UDP(udpPort))
    record.Set(enr.TCP(tcpPort))
    
    // Set the public key in the record
    pubkey := &privateKey.PublicKey
    record.Set(enr.WithEntry("secp256k1", base32.StdEncoding.EncodeToString(crypto.CompressPubkey(pubkey))))

    // Sign the record
    enode.SignV4(record, privateKey)
    
    //signature := record.Signature()

    if err := record.VerifySignature(enode.V4ID{}); err != nil {
        fmt.Println("Error")
        return nil, err
    }

    fmt.Println("\nrecord:", record)
    return record, nil
}

func encodeENRToLeaf(record *enr.Record) (string, error) {
    var buf bytes.Buffer
    if err := record.EncodeRLP(&buf); err != nil {
        return "", err
    }
    //fmt.Println("Buf:", base64.RawURLEncoding.EncodeToString(buf.Bytes()))
    return "enr:" + base64.RawURLEncoding.EncodeToString(buf.Bytes()), nil
}

func createBranchRecord(enrs []string) (string, []string) {
    var hashes []string
    for _, enr := range enrs {
        hash := crypto.Keccak256Hash([]byte(enr)).Bytes()
        base32Hash := base32.StdEncoding.WithPadding(base32.NoPadding).EncodeToString(hash)
        hashes = append(hashes, base32Hash)
    }
    return "enrtree-branch:" + strings.Join(hashes, ","), hashes
}

func createRootRecord(enrBranchHash string, seq uint64, privateKey *ecdsa.PrivateKey) (string, error) {
    content := fmt.Sprintf("enrtree-root:v1 e=%s l=%s seq=%d", enrBranchHash, enrBranchHash, seq)
    hash := crypto.Keccak256Hash([]byte(content))
    sig, err := crypto.Sign(hash[:], privateKey)
    if err != nil {
        return "", err
    }
    return fmt.Sprintf("%s sig=%s", content, base64.RawURLEncoding.EncodeToString(sig)), nil
}

func main() {
    type Node struct {
        ip string
        udpPort uint16
        tcpPort uint16
    }

    nodes := []Node{
        {"127.0.0.60", 60000, 60000},
        {"127.0.0.61", 60001, 60001},
    }
    domain := "nodes.restaurants.com"
    seq := uint64(1)

    signingKey, _ := crypto.GenerateKey()
    pubKey := base32.StdEncoding.EncodeToString(crypto.CompressPubkey(&signingKey.PublicKey))
fmt.Println("pubKey:", crypto.CompressPubkey(&signingKey.PublicKey))

    var leafRecords []string

    for _, node := range nodes {

        key, _ := crypto.GenerateKey()
        record, _ := createENR(key, net.ParseIP(node.ip), node.udpPort, node.tcpPort)

        leaf, _ := encodeENRToLeaf(record)

        leafRecords = append(leafRecords, leaf)
    }

    fmt.Println("leafRecords:", leafRecords)

    branchContent, leafHashes := createBranchRecord(leafRecords)

    branchHash := base32.StdEncoding.WithPadding(base32.NoPadding).EncodeToString(
        crypto.Keccak256Hash([]byte(branchContent)).Bytes(),
    )
    fmt.Println("branchContent:", branchContent)
    fmt.Println("leafHashes:", leafHashes)
    fmt.Println("branchHash:", branchHash)

    rootRecord, _ := createRootRecord(branchHash, seq, signingKey)

    fmt.Printf("Root TXT record (%s): %s\n", domain, rootRecord)
    fmt.Printf("Branch TXT record (%s.%s): %s\n", branchHash, domain, branchContent)
    for i, leaf := range leafRecords {
        fmt.Printf("Leaf TXT record (%s.%s): %s\n", leafHashes[i], domain, leaf)
    }
    fmt.Printf("enrtree URL: enrtree://%s@%s\n", pubKey, domain)
}

