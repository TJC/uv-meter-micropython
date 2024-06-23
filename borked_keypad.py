from machine import Pin


class BorkedKeypad:
    def __init__(self):
        self.last_keypress = None
        # Defining the GPIO connected to keypad rows and columns (ordering important)
        self.row_list = [16, 11, 12, 14]
        self.col_list = [15, 17, 13]

        for x in range(0, 4):
            self.row_list[x] = Pin(self.row_list[x], Pin.OUT)
            self.row_list[x].value(0)

        for x in range(0, 3):
            self.col_list[x] = Pin(self.col_list[x], Pin.IN, Pin.PULL_DOWN)

        # Define the symbol associated with each key
        self.key_list = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"],
        ]

    # The connection for column 1 is broken, so let's try and use * (col 3)
    # in combination with keys from column 2 to emulate it?
    def keypad(self):
        keys = []
        for r in range(0, 4):
            self.row_list[r].value(1)
            for c in range(0, 3):
                if self.col_list[c].value() == 1:
                    key = self.key_list[r][c]
                    keys.append(key)
                    # print(f"Found {key}")
            self.row_list[r].value(0)
        if len(keys) > 1 and keys[1] == "#":
            if keys[0] == "2":
                keys = ["1"]
            elif keys[0] == "5":
                keys = ["4"]
            elif keys[0] == "8":
                keys = ["7"]
        if len(keys) == 0:
            return None
        else:
            return keys[0]

    # This method makes sure only the "key down" event is sent,
    # rather than continually repeating the key.
    def keypresses_only(self):
        key = self.keypad()
        if key == self.last_keypress:
            return None
        self.last_keypress = key
        return key


# Usage
# k = BorkedKeypad()
# while True:
#     key = k.keypresses_only()
#     if key != None:
#         print(key)
#     utime.sleep(0.3)
