import React, { createContext, useEffect, useMemo, useState } from "react";
import { BleOmiTransport } from "./BleOmiTransport";
import { OmiClient } from "./OmiClient";
import type { OmiConnectionState, OmiDevice, Transcript } from "./types";

type OmiContextValue = {
  client: OmiClient;
  state: OmiConnectionState;
  device: OmiDevice | null;
  transcripts: Transcript[];
  connect: () => Promise<OmiDevice>;
  disconnect: () => Promise<void>;
  startAudio: () => Promise<void>;
  stopAudio: () => Promise<void>;
};

export const OmiContext = createContext<OmiContextValue | null>(null);

export function OmiProvider({ children }: React.PropsWithChildren) {
  const client = useMemo(() => new OmiClient(new BleOmiTransport()), []);
  const [state, setState] = useState<OmiConnectionState>(client.getState());
  const [device, setDevice] = useState<OmiDevice | null>(client.getDevice());
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);

  useEffect(() => {
    const unsubscribeState = client.onState(setState);
    const unsubscribeTranscript = client.onTranscript((item) =>
      setTranscripts((current) => [item, ...current]),
    );

    return () => {
      unsubscribeState();
      unsubscribeTranscript();
      client.destroy();
    };
  }, [client]);

  const value: OmiContextValue = {
    client,
    state,
    device,
    transcripts,
    connect: async () => {
      const connectedDevice = await client.connect();
      setDevice(connectedDevice);
      return connectedDevice;
    },
    disconnect: async () => {
      await client.disconnect();
      setDevice(null);
    },
    startAudio: () => client.startAudio(),
    stopAudio: () => client.stopAudio(),
  };

  return <OmiContext.Provider value={value}>{children}</OmiContext.Provider>;
}
