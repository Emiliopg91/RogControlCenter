import systeminformation from 'systeminformation';

import Client from '../../client/client';
import Device, { RGBColor } from '../../client/device';
import { AbstractEffect } from '../AbstractEffect';

export class Temperature extends AbstractEffect {
  private static maxTemp = 90;
  private static minTemp = 40;
  private static steps = Temperature.maxTemp - Temperature.minTemp;
  private static increment = Math.floor(255 / Temperature.steps);
  private colorsByTemp: Record<number, RGBColor> = {};

  public getName(): string {
    return 'Temperature';
  }

  protected async applyEffect(client: Client, devices: Array<Device>): Promise<void> {
    this.updateColorsByTemp();

    let prevColor = await this.getNewColor();
    while (this.isRunning) {
      const newColor = await this.getNewColor();

      for (let offset = 0; offset < 20 && this.isRunning; offset++) {
        let color = newColor;
        if (offset < 19) {
          color = {
            red: prevColor.red + (offset * (newColor.red - prevColor.red)) / 20,
            green: prevColor.green + (offset * (newColor.green - prevColor.green)) / 20,
            blue: prevColor.blue + (offset * (newColor.blue - prevColor.blue)) / 20
          };
        }
        devices.forEach((dev, i) => {
          client.updateLeds(i, Array(dev.leds.length).fill(color));
        });

        if (this.isRunning) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
      }

      prevColor = newColor;
    }
    this.hasFinished = true;
  }

  private async getNewColor(): Promise<RGBColor> {
    const cpuTemp = (await systeminformation.cpuTemperature()).main;
    if (cpuTemp >= Temperature.maxTemp) {
      return { red: 255 * this.brightness, green: 0, blue: 0 };
    } else if (cpuTemp < Temperature.minTemp) {
      return { red: 0, green: 255 * this.brightness, blue: 0 };
    } else {
      return this.colorsByTemp[cpuTemp];
    }
  }

  private updateColorsByTemp(): void {
    this.colorsByTemp = {};
    for (let i = 0; i <= Temperature.steps; i++) {
      const color = {
        red: i * Temperature.increment * this.brightness,
        green: (255 - i * Temperature.increment) * this.brightness,
        blue: 0
      };
      this.colorsByTemp[Temperature.minTemp + i] = color;
    }
  }
}
