import { StoryPage } from '../models/AgentModels';
import { SpeechInputState } from '../services/SpeechInputService';
import { SpeechPlaybackState } from '../services/SpeechPlaybackService';

@Component
export struct ChildModeView {
  @Link message: string;
  @Prop childReply: string = '';
  @Prop loading: boolean = false;
  @Prop speechState: SpeechInputState = 'idle';
  @Prop speechError: string = '';
  @Prop errorMessage: string = '';
  @Prop riskLevel: string = 'none';
  @Prop riskReason: string = '';
  @Prop storyTitle: string = '';
  @Prop storyPages: StoryPage[] = [];
  @Prop playbackState: SpeechPlaybackState = 'idle';
  @Prop speakingPageNumber: number = 0;
  @Prop playbackError: string = '';
  onToggleSpeech: () => void = (): void => {};
  onSubmit: () => void = (): void => {};
  onTogglePagePlayback: (page: StoryPage) => void = (_page: StoryPage): void => {};

  build() {
    Column({ space: 20 }) {
      Column({ space: 12 }) {
        Text(this.childReply)
          .fontSize(20)
          .fontColor('#24302B')
          .lineHeight(30)
          .width('100%')

        TextArea({ placeholder: '可以说说今天让你开心或难过的事情', text: this.message })
          .height(132)
          .fontSize(17)
          .backgroundColor('#FFFFFF')
          .border({ width: 1, color: '#CAD5CF' })
          .borderRadius(8)
          .onChange((value: string) => {
            this.message = value;
          })

        Row({ space: 10 }) {
          Button(this.speechState === 'listening' ? '结束讲述' : '语音讲述')
            .layoutWeight(1)
            .height(48)
            .fontSize(16)
            .fontColor('#285943')
            .backgroundColor('#EAF3EE')
            .enabled(!this.loading && this.speechState !== 'processing')
            .onClick(() => this.onToggleSpeech())

          if (this.speechState !== 'idle') {
            Text(this.speechState === 'listening' ? '正在听你说…' : '正在识别…')
              .fontSize(14)
              .fontColor('#A6522A')
          }
        }
        .width('100%')

        if (this.speechError.length > 0) {
          Text(this.speechError)
            .width('100%')
            .fontSize(13)
            .fontColor('#A13D32')
        }

        Button(this.loading ? '正在认真想一想…' : '发送')
          .width('100%')
          .height(52)
          .fontSize(17)
          .backgroundColor('#285943')
          .enabled(!this.loading && this.speechState === 'idle')
          .onClick(() => this.onSubmit())
      }
      .width('100%')

      if (this.errorMessage.length > 0) {
        Text(this.errorMessage)
          .width('100%')
          .fontSize(14)
          .fontColor('#A13D32')
          .backgroundColor('#FFF2F0')
          .padding(12)
          .borderRadius(6)
      }

      if (this.riskLevel === 'urgent') {
        Column({ space: 8 }) {
          Text('需要立即请家长介入')
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

      if (this.storyPages.length > 0) {
        Column({ space: 14 }) {
          Text(this.storyTitle)
            .width('100%')
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor('#24302B')
          ForEach(this.storyPages, (page: StoryPage) => {
            Row() {
              Text(`${page.page_number}`)
                .width(34)
                .height(34)
                .textAlign(TextAlign.Center)
                .fontColor('#FFFFFF')
                .backgroundColor('#D97745')
                .borderRadius(17)
              Text(page.text)
                .layoutWeight(1)
                .fontSize(17)
                .lineHeight(27)
                .fontColor('#33413A')
                .margin({ left: 12 })
              Button(this.playbackState === 'speaking' && this.speakingPageNumber === page.page_number ?
                '停止' : '朗读')
                .width(68)
                .height(36)
                .fontSize(14)
                .fontColor('#285943')
                .backgroundColor('#EAF3EE')
                .margin({ left: 8 })
                .onClick(() => this.onTogglePagePlayback(page))
            }
            .width('100%')
            .alignItems(VerticalAlign.Top)
            .padding(14)
            .backgroundColor('#FFFFFF')
            .borderRadius(8)
          }, (page: StoryPage) => `${page.page_number}`)
          if (this.playbackError.length > 0) {
            Text(this.playbackError)
              .width('100%')
              .fontSize(13)
              .fontColor('#A13D32')
          }
        }
        .width('100%')
      }
    }
    .width('100%')
  }
}
