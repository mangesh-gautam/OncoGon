import { OmiClient } from "../src/OmiClient";
import type { AudioChunk, OmiConnectionState, OmiDevice, OmiTransport } from "../src/types";

class FakeTransport implements OmiTransport {
  private stateListener: ((state: OmiConnectionState) => void) | undefined;
  private audioListener: ((chunk: AudioChunk) => void) | undefined;
  readonly device: OmiDevice = { id: "omi-1", name: "Omi", rssi: -45 };
  async scanAndConnect(): Promise<OmiDevice> { this.stateListener?.("connected"); return this.device; }
  async disconnect(): Promise<void> { this.stateListener?.("disconnected"); }
  async startAudioStream(): Promise<void> {}
  async stopAudioStream(): Promise<void> {}
  destroy(): void {}
  onAudio(listener: (chunk: AudioChunk) => void): () => void { this.audioListener = listener; return () => { this.audioListener = undefined; }; }
  onConnectionChange(listener: (state: OmiConnectionState) => void): () => void { this.stateListener = listener; return () => { this.stateListener = undefined; }; }
  emitAudio(chunk: AudioChunk): void { this.audioListener?.(chunk); }
}

describe("OmiClient", () => {
  it("tracks its device and connection lifecycle", async () => {
    const transport = new FakeTransport();
    const client = new OmiClient(transport);
    const states: OmiConnectionState[] = [];
    client.onState((state) => states.push(state));

    await expect(client.connect()).resolves.toEqual(transport.device);
    expect(client.getDevice()).toEqual(transport.device);
    expect(client.getState()).toBe("connected");

    await client.disconnect();
    expect(client.getDevice()).toBeNull();
    expect(states).toEqual(["connected", "disconnected"]);
  });

  it("forwards audio notifications to subscribers", async () => {
    const transport = new FakeTransport();
    const client = new OmiClient(transport);
    const listener = jest.fn();
    client.onAudio(listener);
    transport.emitAudio({ deviceId: "omi-1", sequence: 0, timestamp: 1, base64: "AQID", data: new Uint8Array([1, 2, 3]) });
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
