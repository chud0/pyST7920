import time

import spidev


class ST7920:
    X_PIXELS = 128
    Y_PIXELS = 64

    PREAMBLE = 0b11111000

    def __init__(self, bus=0, device=0, clock=None, rotation=0):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.cshigh = True  # use inverted CS
        self.spi.mode = 0b01
        self.spi.max_speed_hz = clock  # set SPI clock

        self.buff = None  # buffer to display image

        self._send_cmd(0x30)  # basic instruction set
        time.sleep(0.010)
        self._send_cmd(0x30)  # repeated
        time.sleep(0.010)
        self._send_cmd(0x0C)  # display on
        time.sleep(0.010)

        self._send_cmd(0x34)  # extended instruction set
        time.sleep(0.010)
        self._send_cmd(0x34)  # repeated
        time.sleep(0.010)
        self._send_cmd(0x36)  # enable graphics display

        self.rot = None
        self.set_rotation(rotation)  # set rotation

        self.clear()
        self.redraw()

    def set_rotation(self, rot):
        if rot == 0 or rot == 2:
            self.width = self.X_PIXELS
            self.height = self.Y_PIXELS
        elif rot == 1 or rot == 3:
            self.width = self.Y_PIXELS
            self.height = self.X_PIXELS
        self.rot = rot

    def _send(self, rs, rw, data):
        if isinstance(data, int):  # if a single arg, convert to a list
            data = [data]

        b1 = self.PREAMBLE | ((rw & 0x01) << 2) | ((rs & 0x01) << 1)
        payloads = [b1]
        for cmd in data:
            payloads.append(cmd & 0xF0)
            payloads.append((cmd & 0x0F) << 4)
        return self.spi.xfer2(payloads)

    def _send_cmd(self, cmds):
        self._send(rs=0, rw=0, data=cmds)

    def _send_data(self, data):
        self._send(rs=1, rw=0, data=data)

    def clear(self):
        width_bytes = self.X_PIXELS // 8
        self.fbuff = [[0] * width_bytes for _ in range(self.Y_PIXELS)]

    def line(self, x1, y1, x2, y2, set=True):
        diffX = abs(x2 - x1)
        diffY = abs(y2 - y1)
        shiftX = 1 if (x1 < x2) else -1
        shiftY = 1 if (y1 < y2) else -1
        err = diffX - diffY
        drawn = False
        while not drawn:
            self.plot(x1, y1, set)
            if x1 == x2 and y1 == y2:
                drawn = True
                continue
            err2 = 2 * err
            if err2 > -diffY:
                err -= diffY
                x1 += shiftX
            if err2 < diffX:
                err += diffX
                y1 += shiftY

    def fill_rect(self, x1, y1, x2, y2, set=True):
        for y in range(y1, y2 + 1):
            self.line(x1, y, x2, y, set)

    def rect(self, x1, y1, x2, y2, set=True):
        self.line(x1, y1, x2, y1, set)
        self.line(x2, y1, x2, y2, set)
        self.line(x2, y2, x1, y2, set)
        self.line(x1, y2, x1, y1, set)

    def plot(self, x, y, set):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        if set:
            if self.rot == 0:
                self.fbuff[y][x // 8] |= 1 << (7 - (x % 8))
            elif self.rot == 1:
                self.fbuff[x][15 - (y // 8)] |= 1 << (y % 8)
            elif self.rot == 2:
                self.fbuff[63 - y][15 - (x // 8)] |= 1 << (x % 8)
            elif self.rot == 3:
                self.fbuff[63 - x][y // 8] |= 1 << (7 - (y % 8))
        else:
            if self.rot == 0:
                self.fbuff[y][x // 8] &= ~(1 << (7 - (x % 8)))
            elif self.rot == 1:
                self.fbuff[x][15 - (y // 8)] &= ~(1 << (y % 8))
            elif self.rot == 2:
                self.fbuff[63 - y][15 - (x // 8)] &= ~(1 << (x % 8))
            elif self.rot == 3:
                self.fbuff[63 - x][y // 8] &= ~(1 << (7 - (y % 8)))

    def redraw(self, dx1=0, dy1=0, dx2=127, dy2=63):
        for i in range(dy1, dy2 + 1):
            self._send_cmd([0x80 + i % 32, 0x80 + ((dx1 // 16) + (8 if i >= 32 else 0))])  # set address
            self._send_data(self.fbuff[i][dx1 // 16:(dx2 // 8) + 1])
