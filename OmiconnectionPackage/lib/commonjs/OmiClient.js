"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.OmiClient = void 0;
class OmiClient {
  device = null;
  state = "idle";
  stateListeners = new Set();
  audioListeners = new Set();
  transcriptListeners = new Set();
  constructor(transport) {
    this.transport = transport;
    transport.onConnectionChange(state => {
      this.state = state;
      this.stateListeners.forEach(listener => listener(state));
    });
    transport.onAudio(chunk => {
      this.audioListeners.forEach(listener => listener(chunk));

      // Send `chunk` to your Astra API here.
      // The server should assemble/decode audio and return transcripts.
    });
  }
  async connect() {
    this.device = await this.transport.scanAndConnect();
    return this.device;
  }
  async disconnect() {
    await this.transport.disconnect();
    this.device = null;
  }
  startAudio() {
    return this.transport.startAudioStream();
  }
  stopAudio() {
    return this.transport.stopAudioStream();
  }
  receiveTranscript(transcript) {
    this.transcriptListeners.forEach(listener => listener(transcript));
  }
  getState() {
    return this.state;
  }
  getDevice() {
    return this.device;
  }
  onState(listener) {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }
  onAudio(listener) {
    this.audioListeners.add(listener);
    return () => this.audioListeners.delete(listener);
  }
  onTranscript(listener) {
    this.transcriptListeners.add(listener);
    return () => this.transcriptListeners.delete(listener);
  }
  destroy() {
    this.transport.destroy();
  }
}
exports.OmiClient = OmiClient;
//# sourceMappingURL=OmiClient.js.map