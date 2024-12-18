import { Mutex } from 'async-mutex';

import Device from '@main/clients/openrgb/client/classes/Device';
import { RGBColor } from '@main/clients/openrgb/client/classes/RGBColor';
import { AbstractEffect } from '@main/clients/openrgb/effects/base/AbstractEffect';

class StarryNight extends AbstractEffect {
  private mutex: Mutex = new Mutex();

  public constructor() {
    super('Starry Night', false);
  }

  private getRandom(): RGBColor {
    return RGBColor.fromHSV(Math.floor(Math.random() * 360), 1, this.brightness);
  }

  private maxSteps = 30;

  protected async applyEffect(devices: Array<Device>): Promise<void> {
    const promises: Array<Promise<void>> = [];
    for (let i = 0; i < devices.length; i++) {
      promises.push(
        new Promise<void>((resolve) => {
          (async (): Promise<void> => {
            const leds: Array<RGBColor> = Array(devices[i].leds.length).fill(
              RGBColor.fromHex('#000000')
            );
            const steps: Array<number> = Array(devices[i].leds.length).fill(0);
            for (let iter = 0; this.isRunning; iter = (iter + 1) % this.maxSteps) {
              const newColors = Array(devices[i].leds.length);

              for (let j = 0; j < leds.length; j++) {
                steps[j] = Math.max(0, steps[j] - 1);
                newColors[j] = leds[j].getDimmed(steps[j] / this.maxSteps);
              }

              const canTurnOn = steps.filter((i) => i > 0).length / steps.length < 0.1;
              if (iter == 0 || canTurnOn) {
                let ledOn = -1;
                do {
                  ledOn = Math.floor(Math.random() * leds.length);
                } while (steps[ledOn] > 0);
                steps[ledOn] = 15 + Math.floor(Math.random() * 15);
                newColors[ledOn] = leds[ledOn] = this.getRandom().getDimmed(
                  steps[ledOn] / this.maxSteps
                );
              }

              this.setLeds(devices[i], newColors);
              await new Promise<void>((resolve) => {
                setTimeout(resolve, Math.random() * 150);
              });
            }
            resolve();
          })();
        })
      );
    }

    await Promise.all(promises);
    this.hasFinished = true;
  }

  private setLeds(dev: Device, colors: Array<RGBColor>): void {
    this.mutex.runExclusive(() => {
      dev.updateLeds(colors);
    });
  }
}

export const starryNight = new StarryNight();
