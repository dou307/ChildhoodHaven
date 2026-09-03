import { audio } from '@kit.AudioKit';
import { speechRecognizer } from '@kit.CoreSpeechKit';

export type SpeechInputState = 'idle' | 'listening' | 'processing';

const AUDIO_CHUNK_SIZE: number = 1280;

export class SpeechInputService {
  private engine?: speechRecognizer.SpeechRecognitionEngine;
  private capturer?: audio.AudioCapturer;
  private onText?: (text: string, isFinal: boolean) => void;
  private onState?: (state: SpeechInputState) => void;
  private onError?: (message: string) => void;
  private sessionId: string = '';
  private pendingAudio: Uint8Array = new Uint8Array(0);
  private readDataCallback?: (data: ArrayBuffer) => void;
  private state: SpeechInputState = 'idle';

  async start(
    onText: (text: string, isFinal: boolean) => void,
    onState: (state: SpeechInputState) => void,
    onError: (message: string) => void
  ): Promise<void> {
    if (this.state !== 'idle') {
      return;
    }

    this.onText = onText;
    this.onState = onState;
    this.onError = onError;
    this.sessionId = `asr-${Date.now()}`;
    this.pendingAudio = new Uint8Array(0);

    try {
      await this.ensureEngine();
      await this.createCapturer();
      this.startRecognizer();
      await this.capturer?.start();
      this.setState('listening');
    } catch (error) {
      await this.releaseCapturer();
      this.safeCancel();
      this.setState('idle');
      this.onError?.(this.errorMessage(error, '无法启动语音识别'));
    }
  }

  async finish(): Promise<void> {
    if (this.state !== 'listening') {
      return;
    }

    this.setState('processing');
    try {
      await this.releaseCapturer();
      this.engine?.finish(this.sessionId);
    } catch (error) {
      this.setState('idle');
      this.onError?.(this.errorMessage(error, '无法结束语音识别'));
    }
  }

  async cancel(): Promise<void> {
    if (this.state === 'idle') {
      return;
    }
    await this.releaseCapturer();
    this.safeCancel();
    this.setState('idle');
  }

  async shutdown(): Promise<void> {
    await this.cancel();
    this.engine?.shutdown();
    this.engine = undefined;
  }

  private async ensureEngine(): Promise<void> {
    if (this.engine) {
      return;
    }

    const createParams: speechRecognizer.CreateEngineParams = {
      language: 'zh-CN',
      online: 1,
      extraParams: {
        'locate': 'CN',
        'recognizerMode': 'short'
      }
    };
    try {
      this.engine = await speechRecognizer.createEngine(createParams);
    } catch (error) {
      throw new Error(this.errorMessage(error, '语音识别引擎初始化失败'));
    }
    this.engine.setListener({
      onStart: (_sessionId: string, _eventMessage: string): void => {
      },
      onEvent: (_sessionId: string, _eventCode: number, _eventMessage: string): void => {
      },
      onResult: (_sessionId: string, result: speechRecognizer.SpeechRecognitionResult): void => {
        const text = result.result.trim();
        if (text.length > 0) {
          this.onText?.(text, result.isFinal);
        }
      },
      onComplete: (_sessionId: string, _eventMessage: string): void => {
        this.releaseCapturer().finally(() => this.setState('idle'));
      },
      onError: (_sessionId: string, errorCode: number, errorMessage: string): void => {
        this.releaseCapturer().finally(() => {
          this.setState('idle');
          this.onError?.(`语音识别失败（${errorCode}）：${errorMessage}`);
        });
      }
    });
  }

  private async createCapturer(): Promise<void> {
    const options: audio.AudioCapturerOptions = {
      streamInfo: {
        samplingRate: audio.AudioSamplingRate.SAMPLE_RATE_16000,
        channels: audio.AudioChannel.CHANNEL_1,
        sampleFormat: audio.AudioSampleFormat.SAMPLE_FORMAT_S16LE,
        encodingType: audio.AudioEncodingType.ENCODING_TYPE_RAW
      },
      capturerInfo: {
        source: audio.SourceType.SOURCE_TYPE_VOICE_RECOGNITION,
        capturerFlags: 0
      }
    };
    this.capturer = await audio.createAudioCapturer(options);
    this.readDataCallback = (data: ArrayBuffer): void => this.writeAudio(data);
    try {
      this.capturer.on('readData', this.readDataCallback);
    } catch (error) {
      throw new Error(this.errorMessage(error, '无法读取麦克风音频'));
    }
  }

  private startRecognizer(): void {
    const audioInfo: speechRecognizer.AudioInfo = {
      audioType: 'pcm',
      sampleRate: 16000,
      soundChannel: 1,
      sampleBit: 16
    };
    const params: speechRecognizer.StartParams = {
      sessionId: this.sessionId,
      audioInfo: audioInfo,
      extraParams: {
        'recognitionMode': 0,
        'vadBegin': 2000,
        'vadEnd': 3000,
        'maxAudioDuration': 20000
      }
    };
    try {
      this.engine?.startListening(params);
    } catch (error) {
      throw new Error(this.errorMessage(error, '语音识别启动失败'));
    }
  }

  private writeAudio(buffer: ArrayBuffer): void {
    const incoming = new Uint8Array(buffer);
    const combined = new Uint8Array(this.pendingAudio.length + incoming.length);
    combined.set(this.pendingAudio, 0);
    combined.set(incoming, this.pendingAudio.length);

    let offset = 0;
    while (offset + AUDIO_CHUNK_SIZE <= combined.length) {
      try {
        this.engine?.writeAudio(
          this.sessionId,
          combined.slice(offset, offset + AUDIO_CHUNK_SIZE)
        );
      } catch (error) {
        this.onError?.(this.errorMessage(error, '语音数据写入失败'));
        return;
      }
      offset += AUDIO_CHUNK_SIZE;
    }
    this.pendingAudio = combined.slice(offset);
  }

  private async releaseCapturer(): Promise<void> {
    const current = this.capturer;
    if (!current) {
      return;
    }
    this.capturer = undefined;
    if (this.readDataCallback) {
      try {
        current.off('readData', this.readDataCallback);
      } catch (_error) {
      }
    }
    this.readDataCallback = undefined;
    try {
      await current.stop();
    } catch (_error) {
    }
    await current.release();
  }

  private setState(state: SpeechInputState): void {
    this.state = state;
    this.onState?.(state);
  }

  private safeCancel(): void {
    try {
      this.engine?.cancel(this.sessionId);
    } catch (_error) {
    }
  }

  private errorMessage(error: Object, fallback: string): string {
    return error instanceof Error ? `${fallback}：${error.message}` : fallback;
  }
}
