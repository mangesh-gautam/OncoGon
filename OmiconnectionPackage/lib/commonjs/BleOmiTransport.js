"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.BleOmiTransport = void 0;
var _reactNativeBlePlx = require("react-native-ble-plx");
var _base = require("./base64");
var _protocol = require("./protocol");
const OMI_DEVICE_NAME = "OMI";
class BleOmiTransport {
  manager = new _reactNativeBlePlx.BleManager();
  device = null;
  audioSubscription = null;
  audioListeners = new Set();
  stateListeners = new Set();
  sequence = 0;
  async scanAndConnect() {
    this.emitState("scanning");
    const foundDevice = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.manager.stopDeviceScan();
        reject(new Error("OMI device not found within 20 seconds."));
      }, 20_000);
      this.manager.startDeviceScan(null, null, (error, device) => {
        if (error) {
          clearTimeout(timer);
          this.manager.stopDeviceScan();
          reject(error);
          return;
        }
        if ((device === null || device === void 0 ? void 0 : device.name) === OMI_DEVICE_NAME) {
          clearTimeout(timer);
          this.manager.stopDeviceScan();
          resolve(device);
        }
      });
    });
    this.emitState("connecting");
    this.device = await foundDevice.connect();
    await this.device.discoverAllServicesAndCharacteristics();
    this.device.onDisconnected(() => {
      this.device = null;
      this.emitState("disconnected");
    });
    this.emitState("connected");
    return {
      id: this.device.id,
      name: this.device.name
    };
  }
  async startAudioStream() {
    if (!this.device) {
      throw new Error("Connect an OMI device before starting audio.");
    }
    this.audioSubscription = this.device.monitorCharacteristicForService(_protocol.OMI_SERVICE_UUID, _protocol.OMI_AUDIO_DATA_CHARACTERISTIC_UUID, (error, characteristic) => {
      if (error) {
        this.emitState("error");
        return;
      }
      if (!(characteristic !== null && characteristic !== void 0 && characteristic.value)) return;

      // `value` is Base64 from react-native-ble-plx.
      // Replace this with OMI's packet parser if packets include headers.
      const chunk = {
        deviceId: this.device.id,
        sequence: this.sequence++,
        timestamp: Date.now(),
        base64: characteristic.value,
        data: (0, _base.decodeBase64)(characteristic.value).slice(3)
      };
      this.audioListeners.forEach(listener => listener(chunk));
    });
  }
  async stopAudioStream() {
    var _this$audioSubscripti;
    (_this$audioSubscripti = this.audioSubscription) === null || _this$audioSubscripti === void 0 || _this$audioSubscripti.remove();
    this.audioSubscription = null;
  }
  async disconnect() {
    await this.stopAudioStream();
    if (this.device) {
      await this.device.cancelConnection();
      this.device = null;
    }
    this.emitState("disconnected");
  }
  onAudio(listener) {
    this.audioListeners.add(listener);
    return () => this.audioListeners.delete(listener);
  }
  onConnectionChange(listener) {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }
  destroy() {
    var _this$audioSubscripti2;
    (_this$audioSubscripti2 = this.audioSubscription) === null || _this$audioSubscripti2 === void 0 || _this$audioSubscripti2.remove();
    this.manager.destroy();
  }
  emitState(state) {
    this.stateListeners.forEach(listener => listener(state));
  }
}
exports.BleOmiTransport = BleOmiTransport;
//# sourceMappingURL=BleOmiTransport.js.map