MSG_START =               0xFE
LINE_DELIM =              0x0A

MSG_TYPE_CONNECTED =      0x01
MSG_TYPE_DISCONNECTED =   0x02
MSG_TYPE_ERROR =          0x03
MSG_TYPE_DEVICE_POLL =    0x04
MSG_TYPE_DEVICE_STRING =  0x05
MSG_TYPE_DEVICE_INFO =    0x06
MSG_TYPE_HID_INFO =       0x07
MSG_TYPE_STARTUP =        0x08

DEVICE_TYPE_KYBRD =       0x06
DEVICE_TYPE_MOUSE =       0x02

CODE_CTRL_L =             0xE0
CODE_SHIFT_L =            0xE1
CODE_ALT_L =              0xE2
CODE_GUI_L =              0xE3
CODE_CTRL_R =             0xE4
CODE_SHIFT_R =            0xE5
CODE_ALT_R =              0xE6
CODE_GUI_R =              0xE7

# modifier keys are compressed into a single byte, these are the bit indices (from LSB)
MOD_BIT_FLAG_MAP = {
    0: CODE_CTRL_L,
    1: CODE_SHIFT_L,
    2: CODE_ALT_L, 
    3: CODE_GUI_L,
    4: CODE_CTRL_R,
    5: CODE_SHIFT_R,
    # right side GUI button (Windows/CMD) doesn't seem to work with CH559 fw?
    7: CODE_ALT_R
}

class Ch559:
    def __init__(self, uart):
        self._cached_keys = []
        self._uart = uart
        self._incomplete_data = None
    
    def poll(self):
        # conveniently, the ch559 spits out packets delimited with newline chars
        # BUT the newline value (0x0a) may also be part of the data packet being sent
        # so we use uart.readline for conevience, but we still wait for the full expected packet length
        data = self._uart.readline()
        if data is not None:
            if data[0] == MSG_START:
                self._incomplete_data = None
            elif self._incomplete_data is not None:
                data = self._incomplete_data + data
            msg_data_len = data[1]
            if len(data) == msg_data_len + 12:
                return self.parse(data)
            else: 
                self._incomplete_data = data

    def parse(self, packet):
        msg_len = packet[1]
        msg_type = packet[3]
        if msg_type != MSG_TYPE_DEVICE_POLL:
            return
        device_type = packet[4]
        if device_type == DEVICE_TYPE_KYBRD:
            return self.on_keyboard_event(packet)
        elif device_type == DEVICE_TYPE_MOUSE:
            # consumer control (medial controls etc.) are encoded as mouse messages, but they have a shorter length
            if msg_len == 3:
                return self.on_consumer_control_key_event(packet)
            else:
                # TODO Mouse sh*t
                pass

    # consumer control events don't seem to accurately report key releases, so we just ignore them.
    def on_consumer_control_key_event(self, packet):
        if packet[11] != 3:
            return
        raw_btn = packet[12]
        if raw_btn == 0:
            return
        return {
            # for some reason, certain keys come with the 7th highest bit randomly set
            # no idea what the 64/128 offset is for - I just observed that these values were lower than CircuitPython's Keycodes
            "consumer_ctrl_clicked": (0b10111111 & raw_btn) + 64 if raw_btn >= 0x80 else (0b10111111 & raw_btn) + 128
        }
        
    def on_keyboard_event(self, packet):
        modifier_flags = packet[11]
        modifer_keys_pressed = []
        for i in range(8):
            has_mod_for_index = (modifier_flags & (1 << i)) > 0
            if has_mod_for_index:
                mod_code = MOD_BIT_FLAG_MAP.get(i)
                if mod_code is not None:
                    modifer_keys_pressed.append(mod_code)
        # for some reason, certain keys come with the 7th highest bit randomly set
        # no idea what the 64 offset is for - I just observed that these values were 64 higher than CircuitPython's Keycodes
        keys_pressed = [(0b10111111 & i) - 64 if i >= 0x80 else (0b00111111 & i) for i in packet[13:18] if i > 0] + modifer_keys_pressed
        output = {
            "keys_removed": [x for x in self._cached_keys if x not in keys_pressed],
            "keys_added": [x for x in keys_pressed if x not in self._cached_keys]
        }
        self._cached_keys = keys_pressed
        return output
