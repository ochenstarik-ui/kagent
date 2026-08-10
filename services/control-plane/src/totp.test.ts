import { describe, it, expect } from "vitest";
import { generateCode, verifyCodeWithStep, base32Decode, base32Encode } from "./totp.js";

describe("TOTP (RFC 6238)", () => {
  const secretAscii = "12345678901234567890";
  const secretBuffer = Buffer.from(secretAscii, "ascii");
  const secretBase32 = base32Encode(secretBuffer).replace(/=/g, ""); // GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ

  // Test vectors from RFC 6238 Appendix B (SHA1)
  const vectors = [
    { time: 59, step: 1, code: "287082" },
    { time: 1111111109, step: 37037036, code: "081804" },
    { time: 1111111111, step: 37037037, code: "050471" },
    { time: 1234567890, step: 41152263, code: "005924" },
    { time: 2000000000, step: 66666666, code: "279037" },
    { time: 20000000000, step: 666666666, code: "353130" },
  ];

  it("should generate correct codes for RFC 6238 test vectors", () => {
    for (const vector of vectors) {
      const generated = generateCode(secretBuffer, vector.step);
      expect(generated).toBe(vector.code);
    }
  });

  it("should verify code exactly on step", () => {
    const res = verifyCodeWithStep(secretBase32, "081804", 1, 37037036);
    expect(res.valid).toBe(true);
    expect(res.step).toBe(37037036);
  });

  it("should verify code within window (+1 step)", () => {
    const res = verifyCodeWithStep(secretBase32, "081804", 1, 37037035);
    expect(res.valid).toBe(true);
    expect(res.step).toBe(37037036);
  });

  it("should verify code within window (-1 step)", () => {
    const res = verifyCodeWithStep(secretBase32, "081804", 1, 37037037);
    expect(res.valid).toBe(true);
    expect(res.step).toBe(37037036);
  });

  it("should reject code outside window", () => {
    const res = verifyCodeWithStep(secretBase32, "081804", 1, 37037034);
    expect(res.valid).toBe(false);
  });

  it("should reject invalid format code", () => {
    expect(verifyCodeWithStep(secretBase32, "abc123", 1).valid).toBe(false);
    expect(verifyCodeWithStep(secretBase32, "12345", 1).valid).toBe(false);
    expect(verifyCodeWithStep(secretBase32, "1234567", 1).valid).toBe(false);
  });

  it("should return false on invalid secret", () => {
    expect(verifyCodeWithStep("invalid-base32!", "123456", 1).valid).toBe(false);
  });
});
