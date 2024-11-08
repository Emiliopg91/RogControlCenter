import {
  DefaulLevel,
  LoggerRequest,
  RestClientRequest,
  RestClientResponse
} from '@tser-framework/commons';
import { TranslatorRenderer } from '@tser-framework/renderer';
import { ipcRenderer } from 'electron';

import { author, name } from '../../package.json';
import translations from '../../resources/translations.i18n.json';
import { AuraBrightness, AuraLedMode } from '../commons/src/models/Aura';
import { ThrottleThermalPolicy } from '../commons/src/models/Platform';

const localTranslations = TranslatorRenderer.buildTranslations(translations);

//DO NOT TOUCH!!!
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const defaultExposed = {
  api: {
    log(data: LoggerRequest): void {
      ipcRenderer.send('log', data);
    },
    rest<T>(request: RestClientRequest<T>): Promise<RestClientResponse<T>> {
      return ipcRenderer.invoke('rest', request);
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    cfg(): Record<string, any> {
      return ipcRenderer.invoke('cfg');
    }
  },
  env: {
    LOG_LEVEL: process.env.LOG_LEVEL || DefaulLevel
  }
};

export const exposed = {
  api: {
    ...defaultExposed.api,
    async getChargeThresold(): Promise<number> {
      return ipcRenderer.invoke('getChargeThreshold');
    },
    setChargeThresold(thresold: number): void {
      ipcRenderer.invoke('setChargeThreshold', thresold);
    },
    refreshChargeThreshold(callback: (threshold: number) => void): void {
      ipcRenderer.on('refreshChargeThreshold', (_, threshold: number) => {
        callback(threshold);
      });
    },
    async getBrightness(): Promise<AuraBrightness> {
      return ipcRenderer.invoke('getBrightness');
    },
    setBrightness(brightness: AuraBrightness): Promise<void> {
      return ipcRenderer.invoke('setBrightness', brightness);
    },
    refreshBrightness(callback: (brightness: AuraBrightness) => void): void {
      ipcRenderer.on('refreshBrightness', (_, brightness: AuraBrightness) => {
        callback(brightness);
      });
    },
    async getLedMode(): Promise<AuraLedMode> {
      return ipcRenderer.invoke('getLedMode');
    },
    setLedMode(mode: AuraLedMode): Promise<AuraBrightness> {
      return ipcRenderer.invoke('setLedMode', mode);
    },
    refreshLedMode(callback: (mode: AuraLedMode) => void): void {
      ipcRenderer.on('refreshLedMode', (_, mode: AuraLedMode) => {
        callback(mode);
      });
    },
    async getThrottleThermalPolicy(): Promise<ThrottleThermalPolicy> {
      return ipcRenderer.invoke('getThrottleThermalPolicy');
    },
    setThrottleThermalPolicy(policy: ThrottleThermalPolicy): Promise<void> {
      return ipcRenderer.invoke('setThrottleThermalPolicy', policy);
    },
    refreshThrottleThermalPolicy(callback: (policy: ThrottleThermalPolicy) => void): void {
      ipcRenderer.on('refreshThrottleThermalPolicy', (_, policy: ThrottleThermalPolicy) => {
        callback(policy);
      });
    },
    allowsAutoStart(): Promise<boolean> {
      return ipcRenderer.invoke('allowsAutoStart');
    },
    checkAutoStart(): Promise<boolean> {
      return ipcRenderer.invoke('checkAutostart');
    },
    setAutoStart(enabled: boolean): Promise<void> {
      return ipcRenderer.invoke('setAutoStart', enabled);
    }
  },
  app: {
    name: name,
    email: author.email
  },
  env: {
    ...defaultExposed.env
  },
  translations: localTranslations
};

export type ExposedDefinition = typeof exposed;
