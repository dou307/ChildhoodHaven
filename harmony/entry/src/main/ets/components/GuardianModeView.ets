import { ConfirmedMemory, ToolTraceItem } from '../models/AgentModels';

@Component
export struct GuardianModeView {
  @Link childNickname: string;
  @Link childAge: number;
  @Prop riskLevel: string = 'none';
  @Prop riskReason: string = '';
  @Prop parentObservation: string = '';
  @Prop parentResponse: string = '';
  @Prop parentQuestion: string = '';
  @Prop parentNextAction: string = '';
  @Prop parentDisclaimer: string = '';
  @Prop hasMemoryCandidate: boolean = false;
  @Prop memoryCandidateSummary: string = '';
  @Prop memoryCandidateReason: string = '';
  @Prop memorySaving: boolean = false;
  @Prop memoriesLoading: boolean = false;
  @Prop confirmedMemories: ConfirmedMemory[] = [];
  @Prop pendingDeleteMemoryId: string = '';
  @Prop memoryMessage: string = '';
  @Prop memoryError: string = '';
  @Prop provider: string = '';
  @Prop action: string = '';
  @Prop traceItems: ToolTraceItem[] = [];
  @Link showTrace: boolean;
  onChangePin: () => void = (): void => {};
  onConfirmMemory: () => void = (): void => {};
  onDiscardMemory: () => void = (): void => {};
  onLoadMemories: () => void = (): void => {};
  onDeleteMemory: (memoryId: string) => void = (_memoryId: string): void => {};

  private categoryLabel(category: string): string {
    if (category === 'social_event') {
      return '社交事件';
    }
    if (category === 'emotional_pattern') {
      return '情绪模式';
    }
    if (category === 'preference') {
      return '兴趣偏好';
    }
    if (category === 'routine') {
      return '生活习惯';
    }
    return category;
  }

  build() {
    Column({ space: 20 }) {
      Row() {
        Column({ space: 3 }) {
          Text('家长模式')
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor('#24302B')
          Text('建议、记忆与 Agent 运行信息')
            .fontSize(13)
            .fontColor('#68756F')
        }
        .alignItems(HorizontalAlign.Start)
        Blank()
        Button('修改 PIN')
          .width(88)
          .height(36)
          .fontSize(14)
          .fontColor('#285943')
          .backgroundColor('#EAF3EE')
          .onClick(() => this.onChangePin())
      }
      .width('100%')

      Column({ space: 10 }) {
        Text('儿童档案')
          .width('100%')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor('#24302B')
        TextInput({ placeholder: '孩子的称呼', text: this.childNickname })
          .maxLength(20)
          .height(44)
          .fontSize(15)
          .backgroundColor('#FFFFFF')
          .border({ width: 1, color: '#CAD5CF' })
          .borderRadius(8)
          .onChange((value: string) => {
            this.childNickname = value;
          })
        Row({ space: 10 }) {
          Text(`年龄：${this.childAge} 岁`)
            .width(82)
            .fontSize(14)
            .fontColor('#4C5A53')
          Slider({ value: this.childAge, min: 3, max: 12, step: 1 })
            .layoutWeight(1)
            .selectedColor('#285943')
            .onChange((value: number) => {
              this.childAge = Math.round(value);
            })
        }
        .width('100%')
      }
      .width('100%')
      .padding(16)
      .backgroundColor('#FFFFFF')
      .borderRadius(8)

      if (this.riskLevel === 'urgent') {
        Column({ space: 8 }) {
          Text('本轮需要立即介入')
            .width('100%')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#8C2F27')
          Text(this.riskReason)
            .width('100%')
            .fontSize(14)
            .fontColor('#6F332D')
        }
        .width('100%')
        .padding(16)
        .backgroundColor('#FFF2F0')
        .border({ width: 1, color: '#E4A49D' })
        .borderRadius(8)
      }

      if (this.parentObservation.length > 0) {
        Column({ space: 10 }) {
          Text('给家长')
            .width('100%')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#24302B')
          Text('观察')
            .width('100%')
            .fontSize(13)
            .fontWeight(FontWeight.Medium)
            .fontColor('#68756F')
          Text(this.parentObservation)
            .width('100%')
            .fontSize(15)
            .fontColor('#4C5A53')
          Text('建议回应')
            .width('100%')
            .fontSize(13)
            .fontWeight(FontWeight.Medium)
            .fontColor('#68756F')
          Text(this.parentResponse)
            .width('100%')
            .fontSize(15)
            .fontColor('#285943')
          Text('共读问题')
            .width('100%')
            .fontSize(13)
            .fontWeight(FontWeight.Medium)
            .fontColor('#68756F')
          Text(this.parentQuestion)
            .width('100%')
            .fontSize(15)
            .fontColor('#4C5A53')
          Text('下一步')
            .width('100%')
            .fontSize(13)
            .fontWeight(FontWeight.Medium)
            .fontColor('#68756F')
          Text(this.parentNextAction)
            .width('100%')
            .fontSize(15)
            .fontColor('#4C5A53')
          Text(this.parentDisclaimer)
            .width('100%')
            .fontSize(12)
            .fontColor('#68756F')
        }
        .width('100%')
        .padding(16)
        .backgroundColor('#EAF3EE')
        .borderRadius(8)
      }

      if (this.hasMemoryCandidate) {
        Column({ space: 10 }) {
          Text('待家长确认的长期记忆')
            .width('100%')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#24302B')
          Text(this.memoryCandidateSummary)
            .width('100%')
            .fontSize(15)
            .fontColor('#33413A')
          Text(this.memoryCandidateReason)
            .width('100%')
            .fontSize(13)
            .fontColor('#68756F')
          Row({ space: 10 }) {
            Button(this.memorySaving ? '正在保存…' : '家长确认保存')
              .layoutWeight(1)
              .height(44)
              .fontSize(15)
              .backgroundColor('#285943')
              .enabled(!this.memorySaving)
              .onClick(() => this.onConfirmMemory())
            Button('忽略')
              .width(88)
              .height(44)
              .fontSize(15)
              .fontColor('#4C5A53')
              .backgroundColor('#FFFFFF')
              .enabled(!this.memorySaving)
              .onClick(() => this.onDiscardMemory())
          }
          .width('100%')
        }
        .width('100%')
        .padding(16)
        .backgroundColor('#FFF5E9')
        .borderRadius(8)
      }

      Column({ space: 10 }) {
        Row() {
          Text('已确认的长期记忆')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#24302B')
          Blank()
          Button(this.memoriesLoading ? '刷新中…' : '刷新')
            .width(76)
            .height(36)
            .fontSize(14)
            .fontColor('#285943')
            .backgroundColor('#EAF3EE')
            .enabled(!this.memoriesLoading)
            .onClick(() => this.onLoadMemories())
        }
        .width('100%')

        if (this.confirmedMemories.length === 0) {
          Text('尚未读取到家长确认的记忆。')
            .width('100%')
            .fontSize(14)
            .fontColor('#68756F')
        } else {
          ForEach(this.confirmedMemories, (memory: ConfirmedMemory) => {
            Row({ space: 10 }) {
              Column({ space: 4 }) {
                Text(memory.summary)
                  .width('100%')
                  .fontSize(15)
                  .fontColor('#33413A')
                Text(`${this.categoryLabel(memory.category)} · ${memory.created_at.slice(0, 10)}`)
                  .width('100%')
                  .fontSize(12)
                  .fontColor('#68756F')
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)
              Button(this.pendingDeleteMemoryId === memory.memory_id ? '确认删除' : '删除')
                .width(this.pendingDeleteMemoryId === memory.memory_id ? 88 : 64)
                .height(36)
                .fontSize(14)
                .fontColor('#A13D32')
                .backgroundColor('#FFF2F0')
                .onClick(() => this.onDeleteMemory(memory.memory_id))
            }
            .width('100%')
            .padding(12)
            .backgroundColor('#FFFFFF')
            .borderRadius(8)
          }, (memory: ConfirmedMemory) => memory.memory_id)
        }

        if (this.memoryMessage.length > 0) {
          Text(this.memoryMessage)
            .width('100%')
            .fontSize(13)
            .fontColor('#285943')
        }
        if (this.memoryError.length > 0) {
          Text(this.memoryError)
            .width('100%')
            .fontSize(13)
            .fontColor('#A13D32')
        }
      }
      .width('100%')

      if (this.provider.length > 0) {
        Column({ space: 8 }) {
          Row() {
            Text(`Agent 动作：${this.action} · 模型：${this.provider}`)
              .layoutWeight(1)
              .fontSize(12)
              .fontColor('#68756F')
            Button(this.showTrace ? '收起轨迹' : '查看轨迹')
              .width(88)
              .height(34)
              .fontSize(13)
              .fontColor('#285943')
              .backgroundColor('#EAF3EE')
              .onClick(() => {
                this.showTrace = !this.showTrace;
              })
          }
          .width('100%')

          if (this.showTrace) {
            ForEach(this.traceItems, (item: ToolTraceItem) => {
              Row({ space: 10 }) {
                Text(`${item.step}`)
                  .width(28)
                  .height(28)
                  .textAlign(TextAlign.Center)
                  .fontSize(13)
                  .fontColor('#FFFFFF')
                  .backgroundColor('#285943')
                  .borderRadius(14)
                Column({ space: 2 }) {
                  Text(item.node)
                    .width('100%')
                    .fontSize(13)
                    .fontWeight(FontWeight.Medium)
                    .fontColor('#33413A')
                  Text(item.summary)
                    .width('100%')
                    .fontSize(12)
                    .fontColor('#68756F')
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)
              }
              .width('100%')
            }, (item: ToolTraceItem) => `${item.step}-${item.node}`)
          }
        }
        .width('100%')
      }
    }
    .width('100%')
  }
}
