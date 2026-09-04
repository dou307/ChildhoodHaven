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
  @Prop serviceState: string = 'checking';
  @State private currentPageIndex: number = 0;
  onToggleSpeech: () => void = (): void => {};
  onSubmit: () => void = (): void => {};
  onTogglePagePlayback: (page: StoryPage) => void = (_page: StoryPage): void => {};
  onOpenGuardian: () => void = (): void => {};
  onStartNewConversation: () => void = (): void => {};
  onRetryService: () => void = (): void => {};

  private chooseFeeling(feeling: string): void {
    if (this.loading || this.speechState !== 'idle') return;
    this.message = `我今天觉得${feeling}，因为`;
  }

  private startAgain(): void {
    this.currentPageIndex = 0;
    this.onStartNewConversation();
  }

  private stopReadingIfNeeded(): void {
    if (this.playbackState === 'speaking' && this.storyPages.length > this.currentPageIndex &&
      this.speakingPageNumber === this.storyPages[this.currentPageIndex].page_number) {
      this.onTogglePagePlayback(this.storyPages[this.currentPageIndex]);
    }
  }

  @Builder
  buildTopBar(light: boolean) {
    Row({ space: 8 }) {
      Column({ space: 2 }) {
        Text('童心译站')
          .fontSize(26)
          .fontWeight(FontWeight.Bold)
          .fontColor(light ? '#FFF8E8' : '#4A3228')
        Text('让每一种心情被认真听见')
          .fontSize(12)
          .fontColor(light ? '#FFF1CE' : '#795C4E')
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)

      Button('重新开始')
        .height(36)
        .fontSize(13)
        .fontColor(light ? '#FFF8E8' : '#5D4037')
        .backgroundColor(light ? '#6D4C41CC' : '#FFF8E8E8')
        .onClick(() => this.startAgain())
      Button('家长')
        .height(36)
        .fontSize(13)
        .fontColor(light ? '#FFF8E8' : '#5D4037')
        .backgroundColor(light ? '#6D4C41CC' : '#FFF8E8E8')
        .onClick(() => this.onOpenGuardian())
    }
    .width('100%')
    .padding({ left: 20, right: 20, top: 18, bottom: 10 })
  }

  @Builder
  buildServiceNotice() {
    if (this.serviceState === 'offline') {
      Row({ space: 8 }) {
        Text('陪伴服务暂时没有连接')
          .layoutWeight(1)
          .fontSize(13)
          .fontColor('#7A3028')
        Button('重试')
          .height(32)
          .fontSize(13)
          .fontColor('#7A3028')
          .backgroundColor('#FFFFFF')
          .onClick(() => this.onRetryService())
      }
      .width('92%')
      .padding({ left: 14, right: 10, top: 8, bottom: 8 })
      .backgroundColor('#FFF0ECCC')
      .borderRadius(8)
    }
  }

  @Builder
  buildFeelingChoices() {
    Column({ space: 9 }) {
      Text('现在的心情更像哪一种？')
        .fontSize(14)
        .fontColor('#6D4C41')
      Row({ space: 7 }) {
        Button('开心')
          .fontSize(13)
          .fontColor('#6D4C41')
          .backgroundColor('#FFF4BF')
          .onClick(() => this.chooseFeeling('开心'))
        Button('难过')
          .fontSize(13)
          .fontColor('#4E5F80')
          .backgroundColor('#E8EEFF')
          .onClick(() => this.chooseFeeling('难过'))
        Button('生气')
          .fontSize(13)
          .fontColor('#8A4134')
          .backgroundColor('#FFE4D9')
          .onClick(() => this.chooseFeeling('生气'))
        Button('害怕')
          .fontSize(13)
          .fontColor('#5F4E78')
          .backgroundColor('#EEE7F8')
          .onClick(() => this.chooseFeeling('害怕'))
      }
      Row({ space: 7 }) {
        Button('孤单')
          .fontSize(13)
          .fontColor('#536066')
          .backgroundColor('#E8F0F1')
          .onClick(() => this.chooseFeeling('孤单'))
        Button('委屈')
          .fontSize(13)
          .fontColor('#775166')
          .backgroundColor('#F8E7EF')
          .onClick(() => this.chooseFeeling('委屈'))
        Button('紧张')
          .fontSize(13)
          .fontColor('#6B5A3D')
          .backgroundColor('#F4ECD9')
          .onClick(() => this.chooseFeeling('紧张'))
      }
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  buildListeningScene() {
    Stack({ alignContent: Alignment.Top }) {
      Image($r('app.media.child_home_background'))
        .width('100%')
        .height('100%')
        .objectFit(ImageFit.Cover)

      Scroll() {
        Column({ space: 14 }) {
          this.buildTopBar(false)
          this.buildServiceNotice()

          Column({ space: 10 }) {
            Text(this.childReply)
              .width('100%')
              .fontSize(19)
              .fontWeight(FontWeight.Medium)
              .fontColor('#4A3228')
              .lineHeight(28)
            Text('你可以慢慢说，我会先听懂，再和你一起把它变成故事。')
              .width('100%')
              .fontSize(13)
              .fontColor('#84695B')
          }
          .width('88%')
          .padding(18)
          .backgroundColor('#FFFDF5E8')
          .border({ width: 1, color: '#F2D9A7' })
          .borderRadius(8)

          this.buildFeelingChoices()

          Column({ space: 10 }) {
            Image($r('app.media.child_microphone'))
              .width(this.speechState === 'listening' ? 150 : 136)
              .height(this.speechState === 'listening' ? 150 : 136)
              .objectFit(ImageFit.Contain)
              .opacity(this.loading ? 0.55 : 1)
              .onClick(() => {
                if (!this.loading && this.speechState !== 'processing') this.onToggleSpeech();
              })
            Text(this.speechState === 'listening' ? '我正在认真听，讲完再点一次' :
              (this.speechState === 'processing' ? '正在听懂你说的话…' : '点一下，讲讲今天发生的事'))
              .fontSize(14)
              .fontWeight(FontWeight.Medium)
              .fontColor('#5D4037')
          }

          Column({ space: 10 }) {
            TextArea({ placeholder: '也可以在这里写下来…', text: this.message })
              .width('100%')
              .height(94)
              .fontSize(16)
              .fontColor('#4A3228')
              .backgroundColor('#FFFDF5F2')
              .border({ width: 1, color: '#E9CFA5' })
              .borderRadius(8)
              .onChange((value: string) => {
                this.message = value;
              })

            Button(this.loading ? '正在把心情变成故事…' : '告诉小星星')
              .width('100%')
              .height(50)
              .fontSize(17)
              .fontWeight(FontWeight.Medium)
              .backgroundColor('#C9613B')
              .enabled(!this.loading && this.speechState === 'idle' && this.message.trim().length > 0)
              .onClick(() => this.onSubmit())
          }
          .width('88%')

          if (this.speechError.length > 0) {
            Text(this.speechError)
              .width('88%')
              .fontSize(13)
              .fontColor('#8C2F27')
              .backgroundColor('#FFF2F0E8')
              .padding(10)
              .borderRadius(8)
          }

          if (this.errorMessage.length > 0) {
            Text(this.errorMessage)
              .width('88%')
              .fontSize(13)
              .fontColor('#8C2F27')
              .backgroundColor('#FFF2F0E8')
              .padding(10)
              .borderRadius(8)
          }

          if (this.riskLevel === 'urgent') {
            Column({ space: 6 }) {
              Text('现在先去找身边信任的大人')
                .width('100%')
                .fontSize(17)
                .fontWeight(FontWeight.Bold)
                .fontColor('#8C2F27')
              Text(this.riskReason)
                .width('100%')
                .fontSize(14)
                .fontColor('#6F332D')
            }
            .width('88%')
            .padding(16)
            .backgroundColor('#FFF2F0F2')
            .border({ width: 1, color: '#E4A49D' })
            .borderRadius(8)
          }
        }
        .width('100%')
        .padding({ bottom: 30 })
      }
      .width('100%')
      .height('100%')
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  buildReadingScene() {
    Stack({ alignContent: Alignment.Top }) {
      Image($r('app.media.story_reading_background'))
        .width('100%')
        .height('100%')
        .objectFit(ImageFit.Cover)

      Scroll() {
        Column({ space: 16 }) {
          this.buildTopBar(true)

          Column({ space: 12 }) {
            Image($r('app.media.story_book'))
              .width(72)
              .height(72)
              .objectFit(ImageFit.Contain)
            Text(this.storyTitle)
              .width('100%')
              .textAlign(TextAlign.Center)
              .fontSize(24)
              .fontWeight(FontWeight.Bold)
              .fontColor('#5A3828')

            Text(this.storyPages[this.currentPageIndex].text)
              .width('100%')
              .textAlign(TextAlign.Center)
              .fontSize(20)
              .lineHeight(32)
              .fontColor('#47362E')
              .padding({ left: 8, right: 8, top: 10, bottom: 10 })

            Text(`第 ${this.currentPageIndex + 1} 页，共 ${this.storyPages.length} 页`)
              .fontSize(13)
              .fontColor('#8A7061')

            Button(this.playbackState === 'speaking' &&
              this.speakingPageNumber === this.storyPages[this.currentPageIndex].page_number ?
              '停止朗读' : '朗读这一页')
              .width(150)
              .height(46)
              .fontSize(16)
              .fontColor('#5A3828')
              .backgroundColor('#F7DFA8')
              .onClick(() => this.onTogglePagePlayback(this.storyPages[this.currentPageIndex]))

            Row({ space: 12 }) {
              Button('上一页')
                .layoutWeight(1)
                .height(46)
                .fontSize(15)
                .fontColor('#5D4037')
                .backgroundColor('#F3E8D2')
                .enabled(this.currentPageIndex > 0)
                .onClick(() => {
                  if (this.currentPageIndex > 0) {
                    this.stopReadingIfNeeded();
                    this.currentPageIndex -= 1;
                  }
                })
              Button(this.currentPageIndex >= this.storyPages.length - 1 ? '读完了' : '下一页')
                .layoutWeight(1)
                .height(46)
                .fontSize(15)
                .backgroundColor('#C9613B')
                .onClick(() => {
                  if (this.currentPageIndex < this.storyPages.length - 1) {
                    this.stopReadingIfNeeded();
                    this.currentPageIndex += 1;
                  } else {
                    this.startAgain();
                  }
                })
            }
            .width('100%')

            if (this.playbackError.length > 0) {
              Text(this.playbackError)
                .width('100%')
                .fontSize(13)
                .fontColor('#8C2F27')
            }
          }
          .width('88%')
          .padding({ left: 20, right: 20, top: 22, bottom: 20 })
          .backgroundColor('#FFFDF5F2')
          .border({ width: 2, color: '#E7C98D' })
          .borderRadius(8)

          Text('故事之外，家长模式里还有陪伴建议和需要确认的成长记录。')
            .width('84%')
            .textAlign(TextAlign.Center)
            .fontSize(13)
            .fontColor('#FFF4DE')
            .backgroundColor('#5D4037CC')
            .padding(10)
            .borderRadius(8)
        }
        .width('100%')
        .padding({ bottom: 28 })
      }
      .width('100%')
      .height('100%')
    }
    .width('100%')
    .height('100%')
  }

  build() {
    if (this.storyPages.length > 0) {
      this.buildReadingScene()
    } else {
      this.buildListeningScene()
    }
  }
}
