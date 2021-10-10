import time
import board
import busio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.consumer_control import ConsumerControl
from ch559 import Ch559

# NOTE - make sure these pins are up-to-date for your setup!
uart = busio.UART(board.D6, board.D7, baudrate=400000)

time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems

# we're just going to forward on keyboard events - a clean passthrough
keyboard = Keyboard(usb_hid.devices)
consumer_ctrl = ConsumerControl(usb_hid.devices)

ch559 = Ch559(uart)

while True:
    event = ch559.poll()
    if event is not None:
        new_keys = event.get("keys_added")
        if new_keys is not None:
            for k in new_keys:
                keyboard.press(k)
        old_keys = event.get("keys_removed")
        if old_keys is not None:
            for rk in old_keys:
                keyboard.release(rk)
        cc = event.get("consumer_ctrl_clicked")
        if cc is not None:
            consumer_ctrl.send(cc)