import Device from '@main/clients/openrgb/client/classes/Device';
import { RGBColor } from '@main/clients/openrgb/client/classes/RGBColor';
import Client from '@main/clients/openrgb/client/client';
import { AbstractEffect } from '@main/clients/openrgb/effects/base/AbstractEffect';

class SpectrumCycle extends AbstractEffect {
  public getName(): string {
    return 'Spectrum Cycle';
  }

  protected async applyEffect(client: Client, devices: Array<Device>): Promise<void> {
    for (let offset = 0; this.isRunning; offset = (offset + 1) % 360) {
      devices.forEach((element, i) => {
        client.updateLeds(
          i,
          Array(element.leds.length).fill(RGBColor.fromHSV(offset, 1, this.brightness))
        );
      });
      await new Promise<void>((resolve) => setTimeout(resolve, 20));
    }
    this.hasFinished = true;
  }
}

export const spectrumCycle = new SpectrumCycle();
