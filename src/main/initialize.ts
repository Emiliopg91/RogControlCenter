import { ConfigurationHelper, TranslatorMain, TrayBuilder } from '@tser-framework/main';
import { Menu, app } from 'electron/main';

import icon45 from '../../resources/icons/icon-45x45.png?asset';
import translations from '../../resources/translations.i18n.json';
import { AuraClient } from './dbus/AuraClient';
import { FanCurvesClient } from './dbus/FanCurvesClient';
import { PlatformClient } from './dbus/PlatformClient';
import { PowerClient } from './dbus/PowerClient';
import { ApplicationService } from './services/Application';
import { AuraService } from './services/Aura';
import { PlatformService } from './services/Platform';
import { generateTrayMenuDef, setTrayMenuRefreshFn } from './setup';
import { HttpServer } from './utils/HttpServer';
import { Settings } from './utils/Settings';

export async function initializeBeforeReady(): Promise<void> {
  ConfigurationHelper.initialize();
  TranslatorMain.initialize(translations);
}

// eslint-disable-next-line @typescript-eslint/no-empty-function
export async function initializeWhenReady(): Promise<void> {
  await Settings.initialize();
  await AuraClient.getInstance();
  await FanCurvesClient.getInstance();
  await PlatformClient.getInstance();
  await PowerClient.getInstance();
  await PlatformService.initialize();
  await AuraService.initialize();
  await ApplicationService.initialize();
  await HttpServer.initialize();

  const trayBuilder: TrayBuilder | undefined = TrayBuilder.builder(icon45)
    .withToolTip(app.name)
    .withMenu(await generateTrayMenuDef());
  const tray = trayBuilder.build();
  setTrayMenuRefreshFn((newMenu: Array<Electron.MenuItemConstructorOptions>) => {
    const contextMenu = Menu.buildFromTemplate(newMenu);
    tray.setContextMenu(contextMenu);
  });
}
