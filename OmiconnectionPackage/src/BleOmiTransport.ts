import { BleManager, Device, Subscription } from "react-native-ble-plx";
import type {
  AudioChunk,
  OmiConnectionState,
  OmiDevice,
  OmiTransport,
} from "./types";
import { decodeBase64 } from "./base64";
import {
  OMI_AUDIO_DATA_CHARACTERISTIC_UUID,
  OMI_SERVICE_UUID,
} from "./protocol";

const OMI_DEVICE_NAME = "OMI";

export class BleOmiTransport implements OmiTransport {
  private manager = new BleManager();
  private device: Device | null = null;
  private audioSubscription: Subscription | null = null;
  private audioListeners = new Set<(chunk: AudioChunk) => void>();
  private stateListeners = new Set<(state: OmiConnectionState) => void>();
  private sequence = 0;

  async scanAndConnect(): Promise<OmiDevice> {
    this.emitState("scanning");

    const foundDevice = await new Promise<Device>((resolve, reject) => {
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

        if (device?.name === OMI_DEVICE_NAME) {
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

    return { id: this.device.id, name: this.device.name };
  }

  async startAudioStream(): Promise<void> {
    if (!this.device) {
      throw new Error("Connect an OMI device before starting audio.");
    }

    this.audioSubscription = this.device.monitorCharacteristicForService(
      OMI_SERVICE_UUID,
      OMI_AUDIO_DATA_CHARACTERISTIC_UUID,
      (error, characteristic) => {
        if (error) {
          this.emitState("error");
          return;
        }

        if (!characteristic?.value) return;

        // `value` is Base64 from react-native-ble-plx.
        // Replace this with OMI's packet parser if packets include headers.
        const chunk: AudioChunk = {
          deviceId: this.device!.id,
          sequence: this.sequence++,
          timestamp: Date.now(),
          base64: characteristic.value,
          data: decodeBase64(characteristic.value).slice(3),
        };

        this.audioListeners.forEach((listener) => listener(chunk));
      },
    );

  }

  async stopAudioStream(): Promise<void> {
    this.audioSubscription?.remove();
    this.audioSubscription = null;
  }

  async disconnect(): Promise<void> {
    await this.stopAudioStream();

    if (this.device) {
      await this.device.cancelConnection();
      this.device = null;
    }

    this.emitState("disconnected");
  }

  onAudio(listener: (chunk: AudioChunk) => void) {
    this.audioListeners.add(listener);
    return () => this.audioListeners.delete(listener);
  }

  onConnectionChange(listener: (state: OmiConnectionState) => void) {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  destroy() {
    this.audioSubscription?.remove();
    this.manager.destroy();
  }

  private emitState(state: OmiConnectionState) {
    this.stateListeners.forEach((listener) => listener(state));
  }
}
