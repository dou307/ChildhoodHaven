import { util } from '@kit.ArkTS';
import { cryptoFramework } from '@kit.CryptoArchitectureKit';

export class GuardianPinService {
  static isValid(pin: string): boolean {
    return /^\d{4,6}$/.test(pin);
  }

  static createSalt(): string {
    return util.generateRandomUUID();
  }

  static hash(pin: string, salt: string): string {
    try {
      const digest = cryptoFramework.createMd('SHA256');
      const encoder = new util.TextEncoder();
      digest.updateSync({ data: encoder.encodeInto(`${salt}:${pin}`) });
      const result = digest.digestSync().data;
      let hex = '';
      for (let index = 0; index < result.length; index += 1) {
        hex += result[index].toString(16).padStart(2, '0');
      }
      return hex;
    } catch (_error) {
      return '';
    }
  }

  static verify(pin: string, salt: string, expectedHash: string): boolean {
    if (!GuardianPinService.isValid(pin) || salt.length === 0 || expectedHash.length === 0) {
      return false;
    }
    return GuardianPinService.hash(pin, salt) === expectedHash;
  }
}
