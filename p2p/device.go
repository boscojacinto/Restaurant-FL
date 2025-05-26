package device

import (
	"database/sql"
	"log"
	_ "github.com/mattn/go-sqlite3"
	"github.com/ethereum/go-ethereum/crypto"
)


type DeviceMetadata struct {
	Name string `json:"name"`
	DeviceType string `json:"deviceType"`
}

type DeviceStorage struct {
	DB *sql.DB
}

type DeviceIdentity struct {
	PublicKey string `json:"publicKey"`
	Timestamp string `json:"timestamp"`	
}

type Device struct {
	Identity DeviceIdentity
	Metadata DeviceMetadata
	Storage DeviceStorage
}

func NewDeviceStorage() *DeviceStorage {
	return &DeviceStorage{
		DB: sql.Open("device_storage.db"),
	}
}

func New(myIdentityKey *ecdsa.PrivateKey, config *Config) *Device {
	return &Device{
		storage: NewDeviceStorage(),
		identity: NewDeviceStorage()
	}
}