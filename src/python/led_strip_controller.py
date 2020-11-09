#!/usr/bin/env python3

import argparse
from datetime import datetime
from multiprocessing import RLock
from numbers import Real
from time import sleep
from typing import Tuple, Container, Literal

import psutil
from serial import Serial

_ALL_METRICS = ('cpu', 'memory', 'disk')


class LEDStripController:
    def __init__(self, serial_port) -> None:
        self._conn = Serial(port=serial_port, baudrate=115200)
        self._lock = RLock()
        self._rgb = None
        self.set_rgb(0, 0, 0)

    def __enter__(self) -> 'LEDStripController':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def get_rgb(self) -> Tuple[int, int, int]:
        return self._rgb

    def set_rgb(self, red: Real, green: Real, blue: Real) -> None:
        """
        Sets the brightness of the LEDs.
        :param red: [0, 255] Red LED brightness.
        :param green: [0, 255] Green LED brightness.
        :param blue: [0, 255] Blue LED brightness.
        """

        old_rgb = self._rgb
        self._rgb = red, green, blue = _limit(red), _limit(green), _limit(blue)
        if self._rgb == old_rgb:
            return

        data = f'{red},{green},{blue}.'.encode(encoding='ascii')
        with self._lock, self._conn:
            self._conn.reset_input_buffer()
            self._conn.write(data)
            self._conn.flush()
            self._conn.read()

    def fade_rgb(self, red: Real, green: Real, blue: Real, time_s: Real, step_time_s: Real = 0.2):
        steps = max(1, int(time_s / step_time_s))
        sleep_time = time_s / steps

        r, g, b = self.get_rgb()
        dr, dg, db = (red - r) / steps, (green - g) / steps, (blue - b) / steps
        for _ in range(steps):
            sleep(sleep_time)

            r += dr
            g += dg
            b += db

            self.set_rgb(r, g, b)


def _limit(value: Real) -> int:
    value = round(value)
    return min(max(0, value), 255)


def _get_cpu_percent() -> float:
    usage = psutil.cpu_percent()
    print(f'    CPU usage: {round(usage):3}%', end='')
    return usage


def _get_disk_percent() -> float:
    usage = max(psutil.disk_usage(disk.mountpoint).percent for disk in psutil.disk_partitions())
    print(f'    Disk usage: {round(usage):3}%', end='')
    return usage


def _get_memory_percent() -> float:
    usage = psutil.virtual_memory().percent
    print(f'    Memory usage: {round(usage):3}%', end='')
    return usage


def show_rainbow(leds: LEDStripController, time_s: Real = 30, step_time_s: Real = 0.2):
    leds.set_rgb(255, 1, 1)
    while True:
        leds.fade_rgb(1, 255, 1, time_s, step_time_s=step_time_s)
        leds.fade_rgb(1, 1, 255, time_s, step_time_s=step_time_s)
        leds.fade_rgb(255, 1, 1, time_s, step_time_s=step_time_s)


def show_system_load(
        leds: LEDStripController,
        no_load_rgb=(0, 0, 255),
        full_load_rgb=(255, 0, 0),
        metrics: Container[Literal['cpu', 'disk', 'memory']] = _ALL_METRICS,
        update_interval_s: float = 10
):
    metric_funcs = []
    if 'cpu' in metrics:
        metric_funcs.append(_get_cpu_percent)
    if 'disk' in metrics:
        metric_funcs.append(_get_disk_percent)
    if 'memory' in metrics:
        metric_funcs.append(_get_memory_percent)
    if not metric_funcs:
        raise ValueError('No valid metrics given.')

    while True:
        print(f'{datetime.now()}:', end='')
        max_usage = max(func() for func in metric_funcs)
        print()

        value = max_usage * 255 / 100
        leds.fade_rgb(value, 0, 255 - value, update_interval_s)


def manual_control(leds: LEDStripController) -> None:
    ...


def main():
    parser = argparse.ArgumentParser(description='Control an RGB LED strip.')
    parser.add_argument(
        'serial_port',
        metavar='serial-port',
        help='path to the serial port that the controller is connected to, e.g. "/dev/ttyACM0"'
    )

    subparsers = parser.add_subparsers(help='how to control the LED strip', required=True)

    # Manual mode
    manual_parser = subparsers.add_parser('manual', help='control the LED strip manually')
    manual_parser.set_defaults(func=manual_control)
    # ...

    # Rainbow mode
    rainbow_parser = subparsers.add_parser('rainbow', help='show a repeating rainbow sequence')
    rainbow_parser.set_defaults(func=show_rainbow)

    # System load mode
    sysload_parser = subparsers.add_parser('sysload', help='automatically change the color based on system load')
    sysload_parser.set_defaults(func=show_system_load)
    sysload_parser.add_argument(
        '--no-load-color',
        metavar='R,G,B',
        type=lambda arg: arg.split(','),
        default=(0, 0, 255),
        help='Color of the strip when there is no load on the system. '
             'Should be given as a comma-separated list of RGB values. '
             'Defaults to "0,0,255" (blue).'
    )
    sysload_parser.add_argument(
        '--full-load-color',
        metavar='R,G,B',
        type=lambda arg: arg.split(','),
        default=(255, 0, 0),
        help='Color of the strip when the system is under full load. '
             'Should be given as a comma-separated list of RGB values. '
             'Defaults to "255,0,0" (red).'
    )
    sysload_parser.add_argument(
        '--metrics', '-m',
        type=lambda arg: arg.split(','),
        default=_ALL_METRICS,
        help=f'Which metrics to monitor when determining the system load. '
             f'The metric with the highest load will determine the color. '
             f'Defaults to all metrics, i.e. "{",".join(_ALL_METRICS)}".'
    )
    sysload_parser.add_argument(
        '--update-interval', '-u',
        metavar='seconds',
        type=float,
        default=10,
        help='How many seconds to wait between checking the system load. Defaults to 10 seconds.'
    )

    args = parser.parse_args()

    with LEDStripController(args.serial_port) as leds:
        try:
            if args.func is show_system_load:
                show_system_load(
                    leds,
                    no_load_rgb=args.no_load_color,
                    full_load_rgb=args.full_load_color,
                    metrics=args.metrics,
                    update_interval_s=args.update_interval
                )
            elif args.func is show_rainbow:
                show_rainbow(leds)
            elif args.func is manual_control:
                manual_control(leds)
            else:
                raise RuntimeError(f'Unexpected args.func: {args.func}')
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
