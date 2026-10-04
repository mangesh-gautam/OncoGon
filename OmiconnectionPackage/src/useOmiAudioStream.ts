import { useCallback, useEffect, useRef, useState } from "react";
import type { OmiConnection } from "./OmiConnection";

export type UseOmiAudioStreamResult = {
  isStreaming: boolean;
  error: Error | null;
  start: () => Promise<void>;
  stop: () => void;
};

/** React hook for controlling an Omi audio stream. It always stops on unmount. */
export function useOmiAudioStream(
  connection: OmiConnection | null,
  onAudio: (payload: Uint8Array) => void,
  includePacketHeader = false,
): UseOmiAudioStreamResult {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const stopRef = useRef<(() => void) | null>(null);

  const stop = useCallback(() => {
    stopRef.current?.();
    stopRef.current = null;
    connection?.stopAudioStream();
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
  return { isStreaming, error, start, stop };
}
