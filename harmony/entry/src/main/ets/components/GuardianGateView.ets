export type GuardianGateMode = 'guardian_gate' | 'guardian_setup';

@Component
export struct GuardianGateView {
  @Prop mode: GuardianGateMode = 'guardian_gate';
  @Link pinInput: string;
  @Link pinConfirmation: string;
  @Link pinError: string;
  onUnlock: () => void = (): void => {};
  onSave: () => void = (): void => {};

  build() {
    Column({ space: 14 }) {
      Text(this.mode === 'guardian_setup' ? '设置家长 PIN' : '进入家长模式')
        .width('100%')
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
        .fontColor('#24302B')
      Text(this.mode === 'guardian_setup' ?
        '设置 4–6 位数字 PIN，用于保护家长建议和儿童记忆。' :
        '请输入家长 PIN。')
        .width('100%')
        .fontSize(14)
        .fontColor('#68756F')
      TextInput({ placeholder: '输入 PIN', text: this.pinInput })
        .type(InputType.NUMBER_PASSWORD)
        .maxLength(6)
        .height(48)
        .fontSize(18)
        .backgroundColor('#FFFFFF')
        .border({ width: 1, color: '#CAD5CF' })
        .borderRadius(8)
        .onChange((value: string) => {
          this.pinInput = value;
          this.pinError = '';
        })
      if (this.mode === 'guardian_setup') {
        TextInput({ placeholder: '再次输入 PIN', text: this.pinConfirmation })
          .type(InputType.NUMBER_PASSWORD)
          .maxLength(6)
          .height(48)
          .fontSize(18)
          .backgroundColor('#FFFFFF')
          .border({ width: 1, color: '#CAD5CF' })
          .borderRadius(8)
          .onChange((value: string) => {
            this.pinConfirmation = value;
            this.pinError = '';
          })
      }
      if (this.pinError.length > 0) {
        Text(this.pinError)
          .width('100%')
          .fontSize(13)
          .fontColor('#A13D32')
      }
      Button(this.mode === 'guardian_setup' ? '保存并进入' : '进入家长模式')
        .width('100%')
        .height(48)
        .fontSize(16)
        .backgroundColor('#285943')
        .onClick(() => {
          if (this.mode === 'guardian_setup') {
            this.onSave();
          } else {
            this.onUnlock();
          }
        })
    }
    .width('100%')
    .padding(18)
    .backgroundColor('#FFFFFF')
    .borderRadius(8)
  }
}
