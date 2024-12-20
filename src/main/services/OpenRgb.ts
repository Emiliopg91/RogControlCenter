import { execSync } from 'child_process';
import { debounce } from 'lodash';

import { LoggerMain } from '@tser-framework/main';

import { AuraBrightness } from '@commons/models/Aura';

import { openRgbClient } from '@main/clients/openrgb/OpenRgbClient';
import { mainWindow } from '@main/index';
import { UsbIdentifier } from '@main/models/OpenRgb';
import { generateTrayMenuDef, refreshTrayMenu } from '@main/setup';
import { settings } from '@main/utils/Settings';

class OpenRgbService {
  private logger = LoggerMain.for('OpenRgbService');
  private mode: string = 'Static';
  private brightness: AuraBrightness = AuraBrightness.OFF;
  private color: string = '#FF0000';
  private initialized = false;
  private connectedUsb: Array<UsbIdentifier> | undefined = undefined;

  private bouncedReload = async (): Promise<void> => {
    const t0 = Date.now();
    this.logger.info('Reloading OpenRGB server');
    LoggerMain.addTab();
    await openRgbClient.restart();
    await this.setMode(this.mode);
    LoggerMain.removeTab();
    this.logger.info(`Reloaded after ${(Date.now() - t0) / 1000} seconds`);
  };
  private debouncedReload = debounce(this.bouncedReload, 500);

  public async initialize(): Promise<void> {
    if (!this.initialized) {
      this.logger.info('Initializing OpenRgbService');
      LoggerMain.addTab();

      this.mode = settings.configMap.openRgb?.state?.mode
        ? settings.configMap.openRgb?.state?.mode
        : this.mode;
      this.brightness = settings.configMap.openRgb?.state?.brightness
        ? (settings.configMap.openRgb?.state?.brightness as AuraBrightness)
        : AuraBrightness.OFF;
      this.color = settings.configMap.openRgb?.state?.color
        ? settings.configMap.openRgb?.state?.color
        : this.color;

      this.logger.info('Restoring state');
      this.setMode(this.mode);
      LoggerMain.removeTab();
      setInterval(() => {
        const currentUsb = execSync('lsusb')
          .toString()
          .trim()
          .split('\n')
          .map((line): UsbIdentifier => {
            const columns = line.trim().split(' ');

            const idVendor = columns[5].split(':')[0];
            const idProduct = columns[5].split(':')[1];
            const name = columns.slice(6).join(' ');

            return { idVendor, idProduct, name };
          })
          .filter((dev) =>
            openRgbClient.compatibleDevices?.find(
              (cd) => cd.idVendor == dev.idVendor && cd.idProduct == dev.idProduct
            )
          );

        if (this.connectedUsb) {
          const added = currentUsb.filter(
            (curr) =>
              !this.connectedUsb?.find(
                (old) => old.idVendor == curr.idVendor && old.idProduct == curr.idProduct
              )
          );
          const removed = this.connectedUsb.filter(
            (old) =>
              !currentUsb?.find(
                (curr) => old.idVendor == curr.idVendor && old.idProduct == curr.idProduct
              )
          );

          if (removed.length > 0) {
            this.logger.info('Removed compatible device(s):');
            LoggerMain.addTab();
            removed.forEach((item) => this.logger.info(item.name));
            LoggerMain.removeTab();
          }

          if (added.length > 0) {
            this.logger.info('Connected compatible device(s):');
            LoggerMain.addTab();
            added.forEach((item) => this.logger.info(item.name));
            LoggerMain.removeTab();

            LoggerMain.addTab();
            this.debouncedReload();
            LoggerMain.removeTab();
          }
        }
        this.connectedUsb = currentUsb;
      }, 200);

      this.initialized = true;
    }
  }

  public async setMode(mode: string): Promise<void> {
    if (openRgbClient.availableModes.includes(mode)) {
      const brightness =
        this.brightness == AuraBrightness.OFF ? AuraBrightness.MEDIUM : this.brightness;
      openRgbClient.applyEffect(mode, brightness, this.color);

      this.mode = mode;
      this.brightness = brightness;
      settings.configMap.openRgb!.state = {
        mode,
        brightness: brightness,
        color: this.color
      };

      refreshTrayMenu(await generateTrayMenuDef());
      mainWindow?.webContents.send('refreshLedMode', mode);
      mainWindow?.webContents.send('refreshBrightness', brightness);
    } else {
      this.logger.info(`Mode ${mode} is not available`);
    }
  }

  public async setBrightness(brightness: AuraBrightness): Promise<void> {
    openRgbClient.applyEffect(this.mode, brightness, this.color);

    this.brightness = brightness;
    settings.configMap.openRgb!.state = {
      mode: this.mode,
      brightness,
      color: this.color
    };
    refreshTrayMenu(await generateTrayMenuDef());
    mainWindow?.webContents.send('refreshBrightness', brightness);
  }

  public async setColor(color: string): Promise<void> {
    openRgbClient.applyEffect(this.mode, this.brightness, color);

    this.color = color;
    settings.configMap.openRgb!.state = {
      mode: this.mode,
      brightness: this.brightness,
      color
    };
    refreshTrayMenu(await generateTrayMenuDef());
  }

  public getAvailableModes(): Array<string> {
    return openRgbClient.availableModes;
  }

  public getBrightness(): AuraBrightness {
    return this.brightness;
  }

  public getMode(): string {
    return this.mode;
  }

  public allowsColor(): boolean {
    return openRgbClient.allowsColor(this.mode);
  }

  public getColor(): string {
    return this.color;
  }

  public getNextMode(): string {
    return openRgbClient.availableModes[
      (openRgbClient.availableModes.indexOf(this.mode) + 1) % openRgbClient.availableModes.length
    ];
  }
}

export const openRgbService = new OpenRgbService();
