from bleak.backends import device as bleak_device
from bleak.backends import scanner as bleak_scanner


class BluetoothAdvertisement:
    def __init__(
        self,
        device: bleak_device.BLEDevice,
        advertising_data: bleak_scanner.AdvertisementData,
    ):
        self._device = device
        self._data = advertising_data

    @property
    def device(self) -> bleak_device.BLEDevice:
        return self._device

    @property
    def data(self) -> bleak_scanner.AdvertisementData:
        return self._data

    def is_vendor(self, company_id: int) -> bool:
        if not self.data.manufacturer_data:
            return False
        return company_id in self.data.manufacturer_data
