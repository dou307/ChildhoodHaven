import { textToSpeech } from '@kit.CoreSpeechKit';

export type SpeechPlaybackState = 'idle' | 'speaking';

export class SpeechPlaybackService {
  private engine?: textToSpeech.TextToSpeechEngine;
  private activeRequestId: string = '';
  private onState?: (state: SpeechPlaybackState) => void;
  private onError?: (message: string) => void;

  async speak(
    text: string,
    onState: (state: SpeechPlaybackState) => void,
    onError: (message: string) => void
  ): Promise<void> {
    const normalized = text.trim();
    if (normalized.length === 0) {
      return;
    }

    this.stop();
    this.onState = onState;
    this.onError = onError;

    try {
      await this.ensureEngine();
      const requestId = `tts-${Date.now()}`;
      const params: textToSpeech.SpeakParams = {
        requestId: requestId,
        extraParams: {
          'queueMode': 0,
          'speed': 1,
          'volume': 2,
          'pitch': 1,
          'languageContext': 'zh-CN',
          'audioType': 'pcm',
          'soundChannel': 3,
          'playType': 1
        }
      };
      this.activeRequestId = requestId;
      this.engine?.speak(normalized, params);
      this.onState?.('speaking');
    } catch (error) {
      this.activeRequestId = '';
      this.onState?.('idle');
      this.onError?.(this.errorMessage(error, '无法开始朗读'));
    }
  }

  stop(): void {
    if (this.activeRequestId.length === 0) {
      return;
    }
    this.activeRequestId = '';
    try {
      this.engine?.stop();
    } catch (error) {
      this.onError?.(this.errorMessage(error, '停止朗读失败'));
    }
    this.onState?.('idle');
  }

  shutdown(): void {
    this.stop();
    try {
      this.engine?.shutdown();
    } catch (_error) {
    }
    this.engine = undefined;
  }

  private async ensureEngine(): Promise<void> {
    if (this.engine) {
      return;
    }

    const params: textToSpeech.CreateEngineParams = {
      language: 'zh-CN',
      person: 0,
      online: 1,
      extraParams: {
        'style': 'interaction-broadcast',
        'locate': 'CN',
        'name': 'ChildhoodHavenTts'
      }
    };
    try {
      this.engine = await textToSpeech.createEngine(params);
    } catch (error) {
      throw new Error(this.errorMessage(error, '朗读引擎初始化失败'));
    }

    const listener: textToSpeech.SpeakListener = {
      onStart: (requestId: string, _response: textToSpeech.StartResponse): void => {
        if (requestId === this.activeRequestId) {
          this.onState?.('speaking');
        }
      },
      onComplete: (requestId: string, response: textToSpeech.CompleteResponse): void => {
        if (requestId === this.activeRequestId && response.type === 1) {
          this.activeRequestId = '';
          this.onState?.('idle');
        }
      },
      onStop: (requestId: string, _response: textToSpeech.StopResponse): void => {
        if (requestId === this.activeRequestId) {
          this.activeRequestId = '';
          this.onState?.('idle');
        }
      },
      onError: (requestId: string, errorCode: number, errorMessage: string): void => {
        if (requestId === this.activeRequestId) {
          this.activeRequestId = '';
          this.onState?.('idle');
          this.onError?.(`朗读失败（${errorCode}）：${errorMessage}`);
        }
      }
    };
    this.engine.setListener(listener);
  }

  private errorMessage(error: Object, fallback: string): string {
    return error instanceof Error ? `${fallback}：${error.message}` : fallback;
  }
}
