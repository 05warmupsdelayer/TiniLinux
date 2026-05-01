#!/usr/bin/env python3

import evdev
import asyncio
import subprocess

def find_device_by_name(name):
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if device.name == name:
            return device
    raise Exception(f"Input device with name '{name}' not found")

joypadInput = find_device_by_name("H700 Gamepad")
volumeInput = find_device_by_name("gpio-keys-volume")
lidInput = find_device_by_name("gpio-keys-lid")

brightness_path = "/sys/devices/platform/backlight/backlight/backlight/brightness"
max_brightness = int(open("/sys/devices/platform/backlight/backlight/backlight/max_brightness").read())

class Joypad:
    l1 = 310
    r1 = 311
    l2 = 312
    r2 = 313

    up = 544
    down = 545
    left = 546
    right = 547

    x = 307
    y = 308
    a = 305
    b = 304

    fn = 316
    select = 314
    start = 315


def runcmd(cmd):
    print(f">>> {cmd}")
    subprocess.run(cmd, shell=True)


def brightness(direction):
    with open(brightness_path, "r") as f:
        cur = int(f.read().strip())

    adj = int(max_brightness * 0.05)  # 5%
    cur = max(1, min(cur + adj * direction, max_brightness))

    with open(brightness_path, "w") as f:
        f.write(str(cur))


def volume(direction):
    result = subprocess.run(
        "amixer get -c 0 DAC | awk -F'[][]' '/Left:/ { print $2 }' | sed 's/%//'",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode == 0 and result.stdout.strip().isdigit():
        cur = int(result.stdout.strip())
        cur = max(0, min(cur + 10 * direction, 100))
        subprocess.run(f"amixer set -c 0 DAC {cur}%", shell=True)


last_lid_state = None


async def handle_event(device):

    global last_lid_state

    async for event in device.async_read_loop():

        # ---------------- GAMEPAD ----------------
        if device.name == "H700 Gamepad":
            keys = joypadInput.active_keys()

            if Joypad.fn in keys:

                if Joypad.select in keys:
                    if event.code == Joypad.start and event.value == 1:
                        runcmd("systemctl restart launcher")

                if event.code == Joypad.start and event.value == 1:
                    runcmd("killall retroarch pico8_64 commander simple-terminal fbdoom fbgif-linux-aarch64 || true")

                if event.code == Joypad.up and event.value == 1:
                    brightness(1)

                if event.code == Joypad.down and event.value == 1:
                    brightness(-1)

        # ---------------- VOLUME ----------------
        elif device.name == "gpio-keys-volume":
            if event.code == 115 and event.value == 1:
                volume(1)
            if event.code == 114 and event.value == 1:
                volume(-1)


        # ---------------- LID SWITCH ----------------
        elif device.name == "gpio-keys-lid":
            if event.type == evdev.ecodes.EV_SW and event.code == evdev.ecodes.SW_LID:

                if event.value != last_lid_state:
                    last_lid_state = event.value

                    if event.value == 1:
                        print("LID CLOSED → suspend")
                        runcmd("systemctl suspend")
                    else:
                        print("LID OPENED")


def run():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(handle_event(joypadInput))
    loop.create_task(handle_event(volumeInput))
    loop.create_task(handle_event(lidInput))

    loop.run_forever()


if __name__ == "__main__":
    run()
