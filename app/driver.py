import logging
import time
from functools import lru_cache, partialmethod
from itertools import chain
from spidev import SpiDev
from typing import List

logger = logging.getLogger(__name__)


class ST7920:
    X_PIXELS = 128
    Y_PIXELS = 64

    PREAMBLE = 0b11111000

    def __init__(self, bus=0, device=0, clock=500000):
        self.spi = SpiDev()
        self.spi.open(bus, device)
        self.config_interface(self.spi, clock)

    @staticmethod
    def config_interface(spi_dev: SpiDev, clock: int) -> None:
        spi_dev.cshigh = True  # use inverted CS
        spi_dev.mode = 0b01
        spi_dev.max_speed_hz = clock  # set SPI clock

    def display_turn_on(self):
        for command in [0x30, 0x30, 0x0C, 0x34, 0x34, 0x36]:
            self.send_commands([command])
            time.sleep(0.010)

    def send_to_device(self, data):
        return self.spi.xfer2(data)

    @lru_cache(4)
    def get_first_byte(self, rs: bool, rw: bool):
        return [self.PREAMBLE | ((rw & 1) << 2) | ((rs & 1) << 1)]

    @staticmethod
    def split_command(command):
        logger.warning('Split command <%#x>, to <%#x> & <%#x>', command, command & 0xF0, (command & 0x0F) << 4)
        return command & 0xF0, (command & 0x0F) << 4

    def send(self, rs: bool, rw: bool, data: List[bytes]):
        commands = chain(self.get_first_byte(rs, rw), data)
        prepared_commands = chain.from_iterable(map(self.split_command, commands))
        return self.send_to_device(prepared_commands)

    send_commands = partialmethod(send, rs=False, rw=True)
    send_data = partialmethod(send, rs=True, rw=False)
