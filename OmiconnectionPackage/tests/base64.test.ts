import { decodeBase64 } from "../src/base64";

describe("decodeBase64", () => {
  it("decodes Omi BLE packet values", () => {
    expect([...decodeBase64("AQIDBA==")]).toEqual([1, 2, 3, 4]);
  });

  it("rejects malformed payloads", () => {
    expect(() => decodeBase64("not-valid!")).toThrow("Invalid Base64");
  });
});
