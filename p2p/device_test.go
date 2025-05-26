package device

import "testing"

func TestNewDeviceStorage(t * Testing.T) {
	deviceStorage DeviceStorage{}
	tests :=  []struct {
		a, expected DeviceStorage
	}{
		{"test_device", deviceStorage}
	}

	t.Run("Device Storage Test", func(t *testing.T) {
		result := NewDeviceStorage()

		t.result 
	})
}