import { useCallback, useEffect, useRef, useState } from "react";
/** React hook for controlling an Omi audio stream. It always stops on unmount. */
export function useOmiAudioStream(connection, onAudio, includePacketHeader = false) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const stopRef = useRef(null);
  const stop = useCallback(() => {
    var _stopRef$current;
    (_stopRef$current = stopRef.current) === null || _stopRef$current === void 0 || _stopRef$current.call(stopRef);
    stopRef.current = null;
    connection === null || connection === void 0 || connection.stopAudioStream();
    setIsStreaming(false);
  }, [connection]);
  const start = useCallback(async () => {
    if (!connection) {
      const reason = new Error("Connect an Omi device before starting the audio stream.");
      setError(reason);
      throw reason;
    }
    stop();
    try {
      stopRef.current = await connection.startAudioStream(onAudio, includePacketHeader);
      setError(null);
      setIsStreaming(true);
    } catch (cause) {
      const reason = cause instanceof Error ? cause : new Error(String(cause));
      setError(reason);
      throw reason;
    }
  }, [connection, includePacketHeader, onAudio, stop]);
  useEffect(() => stop, [stop]);
  return {
    isStreaming,
    error,
    start,
    stop
  };
}
//# sourceMappingURL=useOmiAudioStream.js.map