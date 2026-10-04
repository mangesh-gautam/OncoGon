import React, { createContext, useEffect, useMemo, useState } from "react";
import { BleOmiTransport } from "./BleOmiTransport";
import { OmiClient } from "./OmiClient";
export const OmiContext = /*#__PURE__*/createContext(null);
export function OmiProvider({
  children
}) {
  const client = useMemo(() => new OmiClient(new BleOmiTransport()), []);
  const [state, setState] = useState(client.getState());
  const [device, setDevice] = useState(client.getDevice());
  const [transcripts, setTranscripts] = useState([]);
  useEffect(() => {
    const unsubscribeState = client.onState(setState);
    const unsubscribeTranscript = client.onTranscript(item => setTranscripts(current => [item, ...current]));
    return () => {
      unsubscribeState();
      unsubscribeTranscript();
      client.destroy();
    };
  }, [client]);
  const value = {
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
    stopAudio: () => client.stopAudio()
  };
  return /*#__PURE__*/React.createElement(OmiContext.Provider, {
    value: value
  }, children);
}
//# sourceMappingURL=OmiProvider.js.map