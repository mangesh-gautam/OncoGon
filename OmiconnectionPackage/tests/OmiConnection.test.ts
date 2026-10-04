import { OmiConnection } from "../src/OmiConnection";
import {
  BATTERY_LEVEL_CHARACTERISTIC_UUID,
  BATTERY_SERVICE_UUID,
  OMI_AUDIO_CODEC_CHARACTERISTIC_UUID,
  OMI_SERVICE_UUID,
} from "../src/protocol";

const removable = { remove: jest.fn() };

describe("OmiConnection diagnostic", () => {
  it("connects and validates codec and battery services", async () => {
    const codec = { uuid: OMI_AUDIO_CODEC_CHARACTERISTIC_UUID, value: "AQ==", read: jest.fn() };
    codec.read.mockResolvedValue(codec);
    const battery = { uuid: BATTERY_LEVEL_CHARACTERISTIC_UUID, value: "WA==", read: jest.fn() };
    battery.read.mockResolvedValue(battery);
    const device = {
      id: "omi-1", name: "Omi", rssi: -40,
      discoverAllServicesAndCharacteristics: jest.fn().mockResolvedValue(undefined),
      onDisconnected: jest.fn().mockReturnValue(removable),
      cancelConnection: jest.fn().mockResolvedValue(undefined),
      services: jest.fn().mockResolvedValue([
        { uuid: OMI_SERVICE_UUID, characteristics: jest.fn().mockResolvedValue([codec]) },
        { uuid: BATTERY_SERVICE_UUID, characteristics: jest.fn().mockResolvedValue([battery]) },
      ]),
    };
    const manager = {
      state: jest.fn().mockResolvedValue("PoweredOn"),
      stopDeviceScan: jest.fn(),
      connectToDevice: jest.fn().mockResolvedValue(device),
      destroy: jest.fn(),
    };
    const logger = { debug: jest.fn(), info: jest.fn(), warn: jest.fn(), error: jest.fn() };
    const omi = new OmiConnection(manager as any, { logger });

    await expect(omi.diagnose("omi-1")).resolves.toEqual({
      device: { id: "omi-1", name: "Omi", rssi: -40 },
      bluetoothState: "PoweredOn",
      audioCodec: "pcm8",
      batteryLevel: 88,
    });
    expect(logger.info).toHaveBeenCalledWith("[Omi] Connection diagnostic passed:", expect.any(Object));
  });
});
