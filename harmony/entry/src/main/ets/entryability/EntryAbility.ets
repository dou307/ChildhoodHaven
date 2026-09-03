import { AbilityConstant, abilityAccessCtrl, UIAbility, Want } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { window } from '@kit.ArkUI';

const DOMAIN = 0x1100;

export default class EntryAbility extends UIAbility {
  onCreate(_want: Want, _launchParam: AbilityConstant.LaunchParam): void {
    hilog.info(DOMAIN, 'ChildhoodHaven', 'Ability created');
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    const permissionManager = abilityAccessCtrl.createAtManager();
    permissionManager.requestPermissionsFromUser(this.context, ['ohos.permission.MICROPHONE'])
      .catch((error: Error) => {
        hilog.warn(DOMAIN, 'ChildhoodHaven', 'Microphone permission was not granted: %{public}s', error.message);
      });

    windowStage.loadContent('pages/Index', (error) => {
      if (error.code) {
        hilog.error(DOMAIN, 'ChildhoodHaven', 'Failed to load page: %{public}s', JSON.stringify(error));
      }
    });
  }
}
