import { randomBytes, createHmac, timingSafeEqual } from "node:crypto";

const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

export function base32Encode(buffer: Buffer): string {
  let bits = 0;
  let value = 0;
  let output = "";

  for (let i = 0; i < buffer.length; i++) {
    value = (value << 8) | buffer[i]!;
    bits += 8;
    while (bits >= 5) {
      output += BASE32_ALPHABET.charAt((value >>> (bits - 5)) & 31);
      bits -= 5;
    }
  }
  if (bits > 0) {
    output += BASE32_ALPHABET.charAt((value << (5 - bits)) & 31);
  }
  while (output.length % 8 !== 0) {
    output += "=";
  }
  return output;
}

export function base32Decode(input: string): Buffer {
  const cleanedInput = input.toUpperCase().replace(/=/g, "");
  const length = cleanedInput.length;
  let bits = 0;
  let value = 0;
  let index = 0;
  const output = Buffer.alloc(((length * 5) / 8) | 0);

  for (let i = 0; i < length; i++) {
    const val = BASE32_ALPHABET.indexOf(cleanedInput.charAt(i));
    if (val === -1) throw new Error("Invalid base32 character");
    value = (value << 5) | val;
    bits += 5;
    if (bits >= 8) {
      output[index++] = (value >>> (bits - 8)) & 255;
      bits -= 8;
    }
  }
  return output;
}

export function generateSecret(): string {
  return base32Encode(randomBytes(20)).replace(/=/g, "");
}

export function generateUri(email: string, secret: string): string {
  const issuer = encodeURIComponent("KAgent");
  const account = encodeURIComponent(email);
  return `otpauth://totp/${issuer}:${account}?secret=${secret}&issuer=${issuer}`;
}

export function generateCode(secretBuffer: Buffer, timeStep: number): string {
  const timeBuffer = Buffer.alloc(8);
  timeBuffer.writeBigUInt64BE(BigInt(timeStep), 0);

  const hmac = createHmac("sha1", secretBuffer).update(timeBuffer).digest();

  const offset = hmac[hmac.length - 1]! & 0xf;
  const codeInt =
    ((hmac[offset]! & 0x7f) << 24) |
    ((hmac[offset + 1]! & 0xff) << 16) |
    ((hmac[offset + 2]! & 0xff) << 8) |
    (hmac[offset + 3]! & 0xff);

  const code = (codeInt % 1000000).toString().padStart(6, "0");
  return code;
}

export function verifyCodeWithStep(secret: string, code: string, window = 1, currentStepOverride?: number): { valid: boolean; step: number } {
  if (!/^\d{6}$/.test(code)) return { valid: false, step: 0 };

  let secretBuffer: Buffer;
  try {
    secretBuffer = base32Decode(secret);
  } catch {
    return { valid: false, step: 0 };
  }

  const currentStep = currentStepOverride ?? Math.floor(Date.now() / 30000);
  const targetCode = Buffer.from(code);

  for (let i = -window; i <= window; i++) {
    const step = currentStep + i;
    const generated = Buffer.from(generateCode(secretBuffer, step));
    if (generated.length === targetCode.length && timingSafeEqual(generated, targetCode)) {
      return { valid: true, step };
    }
  }
  return { valid: false, step: 0 };
}
