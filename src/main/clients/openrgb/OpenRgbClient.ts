import { ChildProcess, spawn } from 'child_process';
import { existsSync, readFileSync, readdirSync } from 'fs';
import net, { AddressInfo } from 'net';
import os from 'os';
import path from 'path';

import { LoggerMain } from '@tser-framework/main';

import { AuraBrightness } from '@commons/models/Aura';

import Device from '@main/clients/openrgb/client/classes/Device';
import { RGBColor } from '@main/clients/openrgb/client/classes/RGBColor';
import Client from '@main/clients/openrgb/client/client';
import { breathing } from '@main/clients/openrgb/effects/Breathing';
import { danceFloor } from '@main/clients/openrgb/effects/DanceFloor';
import { rain } from '@main/clients/openrgb/effects/Rain';
import { spectrumCycle } from '@main/clients/openrgb/effects/SpectrumCycle';
import { starryNight } from '@main/clients/openrgb/effects/StarryNight';
import { staticEffect } from '@main/clients/openrgb/effects/Static';
import { temperature } from '@main/clients/openrgb/effects/Temperature';
import { UsbIdentifier } from '@main/models/OpenRgb';
import { Constants } from '@main/utils/Constants';

import openRgbAppImage from '@resources/OpenRGB.AppImage?asset&asarUnpack';

class OpenRgbClient {
  private logger = LoggerMain.for('OpenRgbClient');
  private initialized = false;
  private availableModesInst = [
    staticEffect,
    breathing,
    spectrumCycle,
    starryNight,
    temperature,
    danceFloor,
    rain
  ];
  public availableModes: Array<string> = [];
  public availableDevices: Array<Device> = [];
  public compatibleDevices: Array<UsbIdentifier> | undefined = undefined;
  private openRgbProc: ChildProcess | undefined = undefined;
  public port: number = 6472;
  private client: Client | undefined = undefined;

  public async initialize(): Promise<void> {
    await new Promise<void>((resolve, reject) => {
      (async (): Promise<void> => {
        if (!this.initialized) {
          try {
            this.logger.info('Initializing client');
            LoggerMain.addTab();
            await this.startOpenRgbProccess();
            await this.loadSupportedDevices();
            await this.connectClient();
            LoggerMain.removeTab();
            resolve();
          } catch (err) {
            reject(err);
          }
        }
      })();
    });

    this.availableModes = this.availableModesInst.map((mode) => mode.name);
  }

  private loadSupportedDevices(): void {
    this.compatibleDevices = undefined;
    const mountDir = readdirSync(os.tmpdir(), { withFileTypes: true }).find((entry) =>
      entry.name.startsWith('.mount_' + path.basename(openRgbAppImage).substring(0, 6))
    );
    if (mountDir) {
      const uDevPath = path.join(
        mountDir.path,
        mountDir.name,
        'usr',
        'lib',
        'udev',
        'rules.d',
        '60-openrgb.rules'
      );
      if (existsSync(uDevPath)) {
        const content = readFileSync(uDevPath).toString();
        const lines = content.split('\n');

        const regex =
          /SUBSYSTEMS==".*?", ATTRS\{idVendor\}=="([\da-fA-F]+)", ATTRS\{idProduct\}=="([\da-fA-F]+)"/;

        const results = lines
          .map((line) => regex.exec(line)) // Buscar coincidencias
          .filter((match) => match !== null) // Filtrar solo las líneas que coincidan
          .map(
            (match): UsbIdentifier => ({
              idVendor: match[1],
              idProduct: match[2]
            })
          );
        this.compatibleDevices = results;
      }
    }
  }

  public async stop(): Promise<void> {
    this.logger.info('Stopping client');
    LoggerMain.addTab();
    for (let i = 0; i < this.availableModesInst.length; i++) {
      await this.availableModesInst[i].stop();
    }
    this.availableDevices.forEach((dev) =>
      dev.updateLeds(Array(dev.leds.length).fill(RGBColor.fromHex('#000000')))
    );
    await new Promise<void>((resolve) => setTimeout(resolve, 50));
    await this.disconnectClient();
    await this.stopOpenRgbServer();
    this.initialized = false;
    LoggerMain.removeTab();
  }

  public async restart(): Promise<void> {
    await this.stop();
    await this.initialize();
    LoggerMain.removeTab();
  }

  private async startOpenRgbProccess(): Promise<void> {
    return new Promise<void>((resolve) => {
      (async (): Promise<void> => {
        this.logger.info('Initializing OpenRGB');
        LoggerMain.addTab();

        this.port = await new Promise((resolve) => {
          const server = net.createServer();
          server.listen(0, () => {
            const port = (server.address() as AddressInfo)!.port;
            server.close(() => resolve(port));
          });
        });
        this.logger.info('Launching OpenRGB server using port ' + this.port);
        this.openRgbProc = spawn(openRgbAppImage, [
          '--server-host',
          String(Constants.localhost),
          '--server-port',
          String(this.port)
        ]);
        this.openRgbProc.stdout!.on('data', (data) => {
          this.logger.debug(data.toString());
        });

        this.openRgbProc.stderr!.on('data', (data) => {
          this.logger.error(data.toString());
        });

        this.openRgbProc.on('close', (code) => {
          if (code) {
            this.logger.info(`Finished with code ${code}`);
          } else {
            this.logger.info(`Process killed`);
          }
          this.openRgbProc = undefined;
        });

        this.openRgbProc.on('error', (error) => {
          this.logger.error(error.message);
        });

        while (
          !(await new Promise((resolve) => {
            const socket = new net.Socket();
            socket.setTimeout(50);
            socket
              .once('connect', () => {
                socket.destroy();
                resolve(true);
              })
              .once('error', () => {
                resolve(false);
              })
              .once('timeout', () => {
                socket.destroy();
                resolve(false);
              })
              .connect({ host: Constants.localhost, port: this.port });
          }))
        ) {
          /**/
        }
        this.logger.info('OpenRGB server online');
        resolve();
      })();
    });
  }

  private async stopOpenRgbServer(): Promise<void> {
    this.logger.info('Stopping OpenRGB');
    await new Promise<void>((resolve) => {
      this.openRgbProc?.on('exit', () => {
        resolve();
      });
      this.openRgbProc?.kill('SIGKILL');
    });
  }

  private async disconnectClient(): Promise<void> {
    this.logger.info('Disconnecting client');
    this.client?.disconnect();
    this.client = undefined;
  }

  private async connectClient(): Promise<void> {
    this.availableDevices = [];
    this.client = new Client('RogControlCenter', this.port, Constants.localhost);
    this.logger.info('Connecting to OpenRGB server on port ' + this.port);
    await this.client.connect();

    this.logger.info('Getting available devices');
    const count = await this.client!.getControllerCount();
    const promises: Array<Promise<Device>> = [];
    for (let i = 0; i < count; i++) {
      promises.push(this.client!.getControllerData(i));
    }

    const allDevs = await Promise.all(promises);
    allDevs.forEach((dev) => {
      const direct = dev.modes.filter((m) => m.name == 'Direct');
      if (direct && direct.length > 0) {
        this.availableDevices.push(dev);
      }
    });
  }

  public async applyEffect(
    effect: string,
    brightness: AuraBrightness,
    color?: string
  ): Promise<void> {
    const inst = this.availableModesInst.filter((i) => i.name == effect);
    if (inst && inst.length > 0) {
      for (let i = 0; i < this.availableModesInst.length; i++) {
        await this.availableModesInst[i].stop();
      }
      await inst[0].start(this.availableDevices, brightness, RGBColor.fromHex(color || '#000000'));
    }
  }

  public allowsColor(mode: string): boolean {
    return this.availableModesInst.find((inst) => inst.name == mode)!.supportsColor;
  }
}

export const openRgbClient = new OpenRgbClient();
