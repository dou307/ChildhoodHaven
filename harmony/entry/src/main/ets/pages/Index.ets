import { ChildModeView } from '../components/ChildModeView';
import { util } from '@kit.ArkTS';
import { GuardianGateMode, GuardianGateView } from '../components/GuardianGateView';
import { GuardianModeView } from '../components/GuardianModeView';
import { ConfirmedMemory, HealthResponse, MemoryCandidate, ParentGuidance, StoryPage,
  ToolTraceItem, TurnRequest, TurnResponse } from '../models/AgentModels';
import { AgentApi } from '../services/AgentApi';
import { GuardianPinService } from '../services/GuardianPinService';
import { SpeechInputService, SpeechInputState } from '../services/SpeechInputService';
import { SpeechPlaybackService, SpeechPlaybackState } from '../services/SpeechPlaybackService';

type AppMode = 'child' | 'guardian_gate' | 'guardian_setup' | 'guardian';

PersistentStorage.persistProp('guardian_pin_hash', '');
PersistentStorage.persistProp('guardian_pin_salt', '');
PersistentStorage.persistProp('child_id', '');
PersistentStorage.persistProp('child_nickname', '小雨');
PersistentStorage.persistProp('child_age', 6);

@Entry
@Component
struct Index {
  @StorageLink('guardian_pin_hash') private guardianPinHash: string = '';
  @StorageLink('guardian_pin_salt') private guardianPinSalt: string = '';
  @StorageLink('child_id') private childId: string = '';
  @StorageLink('child_nickname') private childNickname: string = '小雨';
  @StorageLink('child_age') private childAge: number = 6;
  @State private appMode: AppMode = 'child';
  @State private pinInput: string = '';
  @State private pinConfirmation: string = '';
  @State private pinError: string = '';
  @State private message: string = '';
  @State private loading: boolean = false;
  @State private childReply: string = '今天发生了什么？我会认真听你说。';
  @State private action: string = '';
  @State private provider: string = '';
  @State private serviceState: string = 'checking';
  @State private serviceSummary: string = '正在连接陪伴服务';
  @State private riskLevel: string = 'none';
  @State private riskReason: string = '';
  @State private traceItems: ToolTraceItem[] = [];
  @State private showTrace: boolean = false;
  @State private errorMessage: string = '';
  @State private storyTitle: string = '';
  @State private storyPages: StoryPage[] = [];
  @State private parentObservation: string = '';
  @State private parentResponse: string = '';
  @State private parentQuestion: string = '';
  @State private parentNextAction: string = '';
  @State private parentDisclaimer: string = '';
  @State private speechState: SpeechInputState = 'idle';
  @State private speechError: string = '';
  @State private playbackState: SpeechPlaybackState = 'idle';
  @State private speakingPageNumber: number = 0;
  @State private playbackError: string = '';
  @State private hasMemoryCandidate: boolean = false;
  @State private memoryCandidateSummary: string = '';
  @State private memoryCandidateReason: string = '';
  @State private memorySaving: boolean = false;
  @State private memoryMessage: string = '';
  @State private memoryError: string = '';
  @State private memoriesLoading: boolean = false;
  @State private confirmedMemories: ConfirmedMemory[] = [];
  @State private pendingDeleteMemoryId: string = '';
  private latestMemoryCandidate?: MemoryCandidate;
  private conversationId: string = `mobile-${Date.now()}`;
  private pendingTurnId: string = '';
  private pendingTurnMessage: string = '';
  private readonly speechInput: SpeechInputService = new SpeechInputService();
  private readonly speechPlayback: SpeechPlaybackService = new SpeechPlaybackService();

  aboutToAppear(): void {
    if (this.childId.length === 0) {
      this.childId = util.generateRandomUUID();
    }
    this.checkService();
  }

  aboutToDisappear(): void {
    this.speechInput.shutdown().catch(() => {});
    this.speechPlayback.shutdown();
    this.appMode = 'child';
    this.clearPinInput();
  }

  private openGuardianMode(): void {
    this.speechPlayback.stop();
    this.clearPinInput();
    this.appMode = this.guardianPinHash.length === 0 ? 'guardian_setup' : 'guardian_gate';
  }

  private returnToChildMode(): void {
    this.appMode = 'child';
    this.clearPinInput();
  }

  private clearPinInput(): void {
    this.pinInput = '';
    this.pinConfirmation = '';
    this.pinError = '';
  }

  private unlockGuardianMode(): void {
    if (!GuardianPinService.verify(this.pinInput, this.guardianPinSalt, this.guardianPinHash)) {
      this.pinError = 'PIN 不正确，请重试。';
      this.pinInput = '';
      return;
    }
    this.appMode = 'guardian';
    this.clearPinInput();
    this.loadMemories();
  }

  private saveGuardianPin(): void {
    if (!GuardianPinService.isValid(this.pinInput)) {
      this.pinError = '请输入 4–6 位数字 PIN。';
      return;
    }
    if (this.pinInput !== this.pinConfirmation) {
      this.pinError = '两次输入不一致。';
      return;
    }
    const salt = GuardianPinService.createSalt();
    const pinHash = GuardianPinService.hash(this.pinInput, salt);
    if (pinHash.length === 0) {
      this.pinError = 'PIN 保存失败，请重试。';
      return;
    }
    this.guardianPinSalt = salt;
    this.guardianPinHash = pinHash;
    this.appMode = 'guardian';
    this.clearPinInput();
    this.loadMemories();
  }

  private changeGuardianPin(): void {
    this.clearPinInput();
    this.appMode = 'guardian_setup';
  }

  private async checkService(): Promise<void> {
    this.serviceState = 'checking';
    this.serviceSummary = '正在连接陪伴服务';
    try {
      const health: HealthResponse = await AgentApi.health();
      this.serviceState = 'online';
      this.serviceSummary = `${health.model_provider} · ${health.persistence}`;
    } catch (_error) {
      this.serviceState = 'offline';
      this.serviceSummary = '服务未连接';
    }
  }

  private async togglePagePlayback(page: StoryPage): Promise<void> {
    this.playbackError = '';
    if (this.playbackState === 'speaking' && this.speakingPageNumber === page.page_number) {
      this.speechPlayback.stop();
      return;
    }
    this.speakingPageNumber = page.page_number;
    await this.speechPlayback.speak(page.text,
      (state: SpeechPlaybackState): void => {
        this.playbackState = state;
        if (state === 'idle') this.speakingPageNumber = 0;
      },
      (message: string): void => { this.playbackError = message; });
  }

  private async toggleSpeech(): Promise<void> {
    this.speechError = '';
    if (this.speechState === 'listening') {
      await this.speechInput.finish();
      return;
    }
    if (this.speechState === 'processing' || this.loading) return;
    await this.speechInput.start(
      (text: string, _isFinal: boolean): void => { this.message = text; },
      (state: SpeechInputState): void => { this.speechState = state; },
      (message: string): void => { this.speechError = message; });
  }

  private async submit(): Promise<void> {
    const normalized = this.message.trim();
    if (normalized.length === 0 || this.loading) return;
    this.loading = true;
    this.errorMessage = '';
    this.speechPlayback.stop();
    const payload: TurnRequest = {
      message: normalized,
      child: {
        child_id: this.childId,
        nickname: this.childNickname.trim().length > 0 ? this.childNickname.trim() : '小朋友',
        age: this.childAge
      },
      turn_id: this.turnIdFor(normalized)
    };
    try {
      this.applyResult(await AgentApi.createTurn(this.conversationId, payload));
      this.pendingTurnId = '';
      this.pendingTurnMessage = '';
    } catch (error) {
      const reason = error instanceof Error ? error.message : '未知错误';
      this.errorMessage = `暂时没有连接到陪伴服务：${reason}`;
    } finally {
      this.loading = false;
    }
  }

  private turnIdFor(message: string): string {
    if (this.pendingTurnId.length === 0 || this.pendingTurnMessage !== message) {
      this.pendingTurnId = util.generateRandomUUID();
      this.pendingTurnMessage = message;
    }
    return this.pendingTurnId;
  }

  private startNewConversation(): void {
    this.speechPlayback.stop();
    this.conversationId = `mobile-${Date.now()}`;
    this.message = '';
    this.pendingTurnId = '';
    this.pendingTurnMessage = '';
    this.childReply = '今天发生了什么？我会认真听你说。';
    this.action = '';
    this.provider = '';
    this.errorMessage = '';
    this.storyTitle = '';
    this.storyPages = [];
    this.parentObservation = '';
    this.parentResponse = '';
    this.parentQuestion = '';
    this.parentNextAction = '';
    this.parentDisclaimer = '';
    this.riskLevel = 'none';
    this.riskReason = '';
    this.traceItems = [];
    this.showTrace = false;
    this.hasMemoryCandidate = false;
    this.latestMemoryCandidate = undefined;
    this.memoryMessage = '';
    this.memoryError = '';
  }

  private async confirmMemory(): Promise<void> {
    const candidate = this.latestMemoryCandidate;
    if (!candidate || this.memorySaving) return;
    this.memorySaving = true;
    this.memoryError = '';
    this.memoryMessage = '';
    try {
      await AgentApi.confirmMemory(this.childId, candidate);
      this.hasMemoryCandidate = false;
      this.latestMemoryCandidate = undefined;
      this.memoryMessage = '已由家长确认并保存。';
      await this.loadMemories();
    } catch (error) {
      this.memoryError = `保存失败：${error instanceof Error ? error.message : '未知错误'}`;
    } finally {
      this.memorySaving = false;
    }
  }

  private discardMemoryCandidate(): void {
    this.hasMemoryCandidate = false;
    this.latestMemoryCandidate = undefined;
    this.memoryMessage = '本次候选已忽略，不会保存。';
    this.memoryError = '';
  }

  private async loadMemories(): Promise<void> {
    if (this.memoriesLoading) return;
    this.memoriesLoading = true;
    this.memoryError = '';
    try {
      this.confirmedMemories = await AgentApi.listMemories(this.childId);
    } catch (error) {
      this.memoryError = `读取失败：${error instanceof Error ? error.message : '未知错误'}`;
    } finally {
      this.memoriesLoading = false;
    }
  }

  private async deleteMemory(memoryId: string): Promise<void> {
    if (this.pendingDeleteMemoryId !== memoryId) {
      this.pendingDeleteMemoryId = memoryId;
      this.memoryMessage = '再次点击“确认删除”后才会删除。';
      return;
    }
    this.memoryError = '';
    try {
      await AgentApi.deleteMemory(this.childId, memoryId);
      this.confirmedMemories = this.confirmedMemories.filter(
        (memory: ConfirmedMemory): boolean => memory.memory_id !== memoryId);
      this.pendingDeleteMemoryId = '';
      this.memoryMessage = '已删除这条长期记忆。';
    } catch (error) {
      this.memoryError = `删除失败：${error instanceof Error ? error.message : '未知错误'}`;
    }
  }

  private applyResult(result: TurnResponse): void {
    this.childReply = result.child_message;
    this.action = result.action;
    this.provider = result.model_provider;
    this.riskLevel = result.safety.risk_level;
    this.riskReason = result.safety.reason;
    this.traceItems = result.tool_trace;
    this.storyTitle = result.story?.title ?? '';
    this.storyPages = result.story?.pages ?? [];
    const guidance: ParentGuidance | undefined = result.parent_guidance;
    this.parentObservation = guidance?.observation ?? '';
    this.parentResponse = guidance?.suggested_response ?? '';
    this.parentQuestion = guidance?.shared_reading_question ?? '';
    this.parentNextAction = guidance?.next_action ?? '';
    this.parentDisclaimer = guidance?.disclaimer ?? '';
    const candidate: MemoryCandidate | undefined = result.memory_candidate;
    this.latestMemoryCandidate = candidate;
    this.hasMemoryCandidate = candidate !== undefined;
    this.memoryCandidateSummary = candidate?.summary ?? '';
    this.memoryCandidateReason = candidate?.reason ?? '';
    this.memoryMessage = '';
    this.memoryError = '';
  }

  build() {
    Scroll() {
      Column({ space: 20 }) {
        Row() {
          Column({ space: 4 }) {
            Text('童心驿站').fontSize(28).fontWeight(FontWeight.Bold).fontColor('#24302B')
            Text(this.appMode === 'child' ? '小星星正在听' : '家长陪伴模式')
              .fontSize(14).fontColor('#5E6C65')
          }.alignItems(HorizontalAlign.Start)
          Blank()
          if (this.appMode === 'child') {
            Button('家长入口').width(88).height(36).fontSize(14).fontColor('#285943')
              .backgroundColor('#EAF3EE').onClick(() => this.openGuardianMode())
            Button('新对话').width(76).height(36).fontSize(14).fontColor('#285943')
              .backgroundColor('#EAF3EE').margin({ left: 8 }).enabled(!this.loading)
              .onClick(() => this.startNewConversation())
          } else {
            Button('返回儿童').width(88).height(36).fontSize(14).fontColor('#285943')
              .backgroundColor('#EAF3EE').onClick(() => this.returnToChildMode())
          }
        }.width('100%')

        Row({ space: 8 }) {
          Text(this.serviceState === 'online' ? '在线' :
            (this.serviceState === 'checking' ? '检查中' : '离线'))
            .fontSize(12).fontColor(this.serviceState === 'online' ? '#285943' : '#8C2F27')
          Text(this.serviceSummary).layoutWeight(1).fontSize(12).fontColor('#68756F')
          if (this.serviceState === 'offline') {
            Button('重试').width(64).height(32).fontSize(13).fontColor('#285943')
              .backgroundColor('#EAF3EE').onClick(() => this.checkService())
          }
        }.width('100%').padding({ left: 10, right: 10, top: 8, bottom: 8 })
          .backgroundColor(this.serviceState === 'online' ? '#EAF3EE' : '#FFF2F0').borderRadius(6)

        if (this.appMode === 'child') {
          ChildModeView({ message: $message, childReply: this.childReply, loading: this.loading,
            speechState: this.speechState, speechError: this.speechError,
            errorMessage: this.errorMessage, riskLevel: this.riskLevel, riskReason: this.riskReason,
            storyTitle: this.storyTitle, storyPages: this.storyPages,
            playbackState: this.playbackState, speakingPageNumber: this.speakingPageNumber,
            playbackError: this.playbackError,
            onToggleSpeech: (): void => { this.toggleSpeech(); },
            onSubmit: (): void => { this.submit(); },
            onTogglePagePlayback: (page: StoryPage): void => { this.togglePagePlayback(page); } })
        } else if (this.appMode === 'guardian') {
          GuardianModeView({ childNickname: $childNickname, childAge: $childAge,
            riskLevel: this.riskLevel, riskReason: this.riskReason,
            parentObservation: this.parentObservation, parentResponse: this.parentResponse,
            parentQuestion: this.parentQuestion, parentNextAction: this.parentNextAction,
            parentDisclaimer: this.parentDisclaimer, hasMemoryCandidate: this.hasMemoryCandidate,
            memoryCandidateSummary: this.memoryCandidateSummary,
            memoryCandidateReason: this.memoryCandidateReason, memorySaving: this.memorySaving,
            memoriesLoading: this.memoriesLoading, confirmedMemories: this.confirmedMemories,
            pendingDeleteMemoryId: this.pendingDeleteMemoryId, memoryMessage: this.memoryMessage,
            memoryError: this.memoryError, provider: this.provider, action: this.action,
            traceItems: this.traceItems, showTrace: $showTrace,
            onChangePin: (): void => { this.changeGuardianPin(); },
            onConfirmMemory: (): void => { this.confirmMemory(); },
            onDiscardMemory: (): void => { this.discardMemoryCandidate(); },
            onLoadMemories: (): void => { this.loadMemories(); },
            onDeleteMemory: (memoryId: string): void => { this.deleteMemory(memoryId); } })
        } else {
          GuardianGateView({ mode: this.appMode as GuardianGateMode, pinInput: $pinInput,
            pinConfirmation: $pinConfirmation, pinError: $pinError,
            onUnlock: (): void => { this.unlockGuardianMode(); },
            onSave: (): void => { this.saveGuardianPin(); } })
        }
      }.width('100%').padding({ left: 20, right: 20, top: 28, bottom: 36 })
    }.width('100%').height('100%').backgroundColor('#F7F7F3')
  }
}
