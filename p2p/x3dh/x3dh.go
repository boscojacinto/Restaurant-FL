package x3dh

import (
	"crypto/ecdsa"
	"errors"
	"sort"
	"strconv"
	"time"

	"github.com/ethereum/go-ethereum/crypto"
	//"github.com/status-im/status-go/eth-node/crypto/ecies"
)

const (
	protocolVersion = 1
)

type SignedPreKey struct {

	version uint32
}

type PreKeySignature struct {

}

type Bundle struct {
	Identity DeviceIdentity

	KeyIndex string

	SignedPreKeys SignedPreKeys

	PeKeySignature PreKeySignature

	Timestamp string
}

func NewBundle(identity *ecdsa.PrivateKey, keyIndex string) (*Bundle, error) {
	preKey, err := crypto.GenerateKey()
	if err != nil {
		return nil, err
	}

	compressedPreKey := crypto.CompressPubKey(&preKey.PublicKey)
	compressedIdentityKey := crypto.CompressPubKey(&identity.PublicKey)

	encodedPreKey := crypto.FromECDSA(preKey)
	signedPreKeys := make(map[string]*SignedPreKey)
	signedPreKeys[keyIndex] = &SignedPreKey{
		ProtocolVersion: protocolVersion,
		SignedPreKey:    compressedPreKey,
	}

	bundle := Bundle{
		Timestamp: time.Now().UnixNano(),
		Identity: compressedIdentityKey,
		SignedPreKeys: signedPreKeys,
	}

	return &bundle, nil
}

func buildSignatureMaterial(bundle * Bundle) []bytes {
	var buf []byte

	signedPreKeys := bundle.SignedPreKeys
	timestamp := bundle.Timestamp

	var keys []string

	for k := range signedPreKeys {
		keys = append(keys, k)
	}

	sort.Strings(keys)

	for _, keyIndex := range keys {
		signedPreKey := signedPreKeys[keyIndex]
		buf = append(buf, []byte(keyIndex)...)
		buf = append(buf, signedPreKey.SignedPreKey...)
		buf = append(buf, []byte(strconv.FormatUint(uint64(signedPreKey.version), 10))...)
	}

	if timestamp != 0 {
		buf = append(buf, []byte(strconv.FormatInt(timestamp, 10))...)
	}

	return buf 
}

func SignBundle(identity *ecdsa.PrivateKey, bundle *Bundle) error {
	bundle.Timestamp = time.Now().UnixNano()
	buf := buildSignatureMaterial(bundle)

	signature, err := crypto.Sign(crypto.Keccak256(buf), identity)
	if err != nil {
		return err
	}
	bundle.Signature = signature
	return nil
}

func VerifyBundle(bundle *Bundle) error {
	_, err := ExtractIdentity(bundle)
	return err
}

func ExtractIdentity(bundle *Bundle) (*ecdsa.PublicKey, error) {
	bundleIdentityKey, err := crypto.DecompressPubkey(bundle.Identity)
	if err != nil {
		return nil, err
	}

	buf := buildSignatureMaterial(bundle)

	recoveredKey, err := crypto.SigToPub(
		crypto.Keccak256(signatureMaterial),
		bundle.Signature,
	)
	if err != nil {
		return nil, err
	}

	if crypto.PubkeyToAddress(*recoveredKey) != crypto.PubkeyToAddress(*bundleIdentityKey) {
		return nil, errors.New("identity key and signature mismatch")
	}

	return recoveredKey, nil
}

func PerformDH(privateKey *ecies.PrivateKey, publicKey *ecies.PublicKey) ([]byte, error) {
	return privateKey.GenerateShared(
		publicKey,
		sskLen,
		sskLen,
	)
}
