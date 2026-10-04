import { useContext } from "react";
import { OmiContext } from "./OmiProvider";
export function useOmi() {
  const omi = useContext(OmiContext);
  if (!omi) {
    throw new Error("useOmi must be used inside <OmiProvider>.");
  }
  return omi;
}
//# sourceMappingURL=useOmi.js.map