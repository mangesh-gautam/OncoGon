import type {
  AudioChunk,
  OmiConnectionState,
  OmiDevice,
  OmiTransport,
  Transcript,
} from "./types";

type Listener<T> = (value: T) => void;

export class OmiClient {
  private device: OmiDevice | null = null;
  private state: OmiConnectionState = "idle";

  private stateListeners = new Set<Listener<OmiConnectionState>>();
  private audioListeners = new Set<Listener<AudioChunk>>();
  private transcriptListeners = new Set<Listener<Transcript>>();

  constructor(private readonly transport: OmiTransport) {
    transport.onConnectionChange((state) => {
      this.state = state;
      this.stateListeners.forEach((listener) => listener(state));
    });

    transport.onAudio((chunk) => {
      this.audioListeners.forEach((listener) => listener(chunk));

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

  receiveTranscript(transcript: Transcript) {
    this.transcriptListeners.forEach((listener) => listener(transcript));
  }

  getState() {
    return this.state;
  }

  getDevice() {
    return this.device;
  }

  onState(listener: Listener<OmiConnectionState>) {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  onAudio(listener: Listener<AudioChunk>) {
    this.audioListeners.add(listener);
    return () => this.audioListeners.delete(listener);
  }

  onTranscript(listener: Listener<Transcript>) {
    this.transcriptListeners.add(listener);
    return () => this.transcriptListeners.delete(listener);
  }

  destroy() {
    this.transport.destroy();
  }
}
