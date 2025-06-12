package main

import (
    "crypto/sha256"
    "encoding/hex"
    //"encoding/base64"
    "fmt"
    //"github.com/ethereum/go-ethereum/crypto"
    //"github.com/decred/dcrd/dcrec/secp256k1/v4"    
    //p2pcrypto "github.com/libp2p/go-libp2p/core/crypto"    
    "golang.org/x/crypto/ripemd160"
)

func main() {
    key, err := crypto.GenerateKey()
    if err != nil {
        panic(err)
    }

    privateKey := (*p2pcrypto.Secp256k1PrivateKey)(secp256k1.PrivKeyFromBytes(key.D.Bytes()))

    privateKeyBytes, _ := privateKey.Raw()
    publicKeyBytes, _ := privateKey.GetPublic().Raw()
    //compPubKeyBytes := crypto.CompressPubkey(&privateKey.PublicKey)
    fmt.Printf("Private Key: %s\n", hex.EncodeToString(privateKeyBytes))
    fmt.Printf("Public Key: %s\n", hex.EncodeToString(publicKeyBytes))

    privateKeyBase64 := base64.StdEncoding.EncodeToString(privateKeyBytes)
    publicKeyBase64 := base64.StdEncoding.EncodeToString(publicKeyBytes)
    fmt.Printf("Private Key(base64): %s\n", privateKeyBase64)
    fmt.Printf("Public Key(base64): %s\n", publicKeyBase64)
    address := getAddress(publicKeyBytes)
    fmt.Printf("Address: %s\n", hex.EncodeToString(address))

    var pubKey []byte = []byte("+3KIXFVLgIMskPU6D4hFVpCQZxImxNwFsUyu0fjOhhd/wdFLFAimMWw+utrgMXFqTKN4h6B1+ILcO7DpqSVGZg==")
    addr := getAddressEd25519(pubKey)
    node_id := getTmNodeId(addr)
    fmt.Println("Node ID:", node_id)
}

func getAddress(pubBytes []byte) []byte {
    hasherSHA256 := sha256.New()
    _, _ = hasherSHA256.Write(pubBytes)
    sha := hasherSHA256.Sum(nil)

    hasherRIPEMD160 := ripemd160.New()
    _, _ = hasherRIPEMD160.Write(sha)

    return hasherRIPEMD160.Sum(nil)
}

func getAddressEd25519(pubBytes []byte) []byte {
    hasherSHA256 := sha256.New()
    _, _ = hasherSHA256.Write(pubBytes)
    sha := hasherSHA256.Sum(nil)

    return sha[:20]
}

func getTmNodeId(addr []byte) string {
    return hex.EncodeToString(addr)
}