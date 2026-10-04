const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/** Decodes Base64 without relying on browser-only `atob` or Node's Buffer. */
export function decodeBase64(value) {
  const clean = value.replace(/\s/g, "").replace(/=+$/, "");
  if (!clean) return new Uint8Array();
  const bytes = [];
  let buffer = 0;
  let bits = 0;
  for (const character of clean) {
    const index = alphabet.indexOf(character);
    if (index < 0) throw new Error("Invalid Base64 value received from BLE device.");
    buffer = buffer << 6 | index;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      bytes.push(buffer >> bits & 0xff);
    }
  }
  return Uint8Array.from(bytes);
}
//# sourceMappingURL=base64.js.map