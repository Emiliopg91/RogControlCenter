/* eslint-disable no-case-declarations */
import { LoggerMain } from '@tser-framework/main';

import { PlatformService } from './services/Platform';

export async function applicationLogic(): Promise<void> {
  const logger = LoggerMain.for('main/applicationLogic.ts');

  logger.system('Running application logic');
  LoggerMain.addTab();
  PlatformService.restoreThrottleThermalPolicy();
}
