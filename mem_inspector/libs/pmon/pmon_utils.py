import asyncio
from typing import Final, List, Tuple

from libs.pmon.pmon import (  # noqa: E402
    PMON,
    Devices,
    Events,
    PMONDevice,
    Registers,
    Size,
)
from libs.logger import pmon_logger as logger
from libs.vme_constants import PCI_INTEL_VENDORID


def get_bitmask(hibit: int, lobit: int) -> int:
    maskhi: int = 1 << (hibit + 1)
    masklo: int = 1 << lobit
    return maskhi - masklo


def get_bitfield(data: int, startbit: int, endbit: int) -> int:
    value: int = data >> startbit
    mask: int = (1 << (endbit - startbit + 1)) - 1
    result = value & mask
    logger.debug(
        "[BITFIELD] {0:032b}[{1}:{2}] = {3:0b} x {4:0b} = {5:0b}".format(
            data, startbit, endbit, value, mask, result
        )
    )
    return result


def get_bitvalue(nr: int) -> int:
    return 1 << nr


async def measure(
    pmon: PMON,
    node: str,
    unit_ctrl: Registers,
    unit_ctr: Registers,
    event: Events,
    time: int,
) -> int:
    # Function set_event is : setting counter, enabling, reseting init value
    pmon[node].reg(unit_ctrl).set_event(event)
    await asyncio.sleep(time)
    value: int = pmon[node].reg(unit_ctr).get(Size.COUNTER)
    return value


def humanbytes(data: int) -> str:
    """Return the given bytes as a human friendly KB, MB, GB, or TB string."""
    b = float(data)
    kb = float(1024)
    mb = float(kb**2)  # 1,048,576
    gb = float(kb**3)  # 1,073,741,824
    tb = float(kb**4)  # 1,099,511,627,776

    if b < kb:
        return "{0} {1}".format(int(b), "Byte/s" if 0 == b > 1 else "Bytes/s")
    elif kb <= b < mb:
        return "{0:.2f} KB/s".format(b / kb)
    elif mb <= b < gb:
        return "{0:.2f} MB/s".format(b / mb)
    elif gb <= b < tb:
        return "{0:.2f} GB/s".format(b / gb)
    return "{0:.2f} TB/s".format(b / tb)


def count_bw(cas_count_rd: int, cas_count_wr: int) -> Tuple[int, int, int]:
    mem_bw_rd: int = cas_count_rd * 64
    mem_bw_wr: int = cas_count_wr * 64
    mem_bw_total: int = mem_bw_rd + mem_bw_wr
    return (mem_bw_rd, mem_bw_wr, mem_bw_total)


class BitArray(object):
    def __init__(self, length: int):
        self.values = bytearray(b"\x00" * (length // 8 + (1 if length % 8 else 0)))
        self.length = length

    def __setitem__(self, index: int, value: int) -> None:
        value = int(bool(value)) << (7 - index % 8)
        mask = 0xFF ^ (7 - index % 8)
        self.values[index // 8] &= mask
        self.values[index // 8] |= value

    def __getitem__(self, index: int) -> int:
        mask = 1 << (7 - index % 8)
        return bool(self.values[index // 8] & mask)

    def __len__(self) -> int:
        return self.length

    def __repr__(self) -> str:
        return "<{}>".format(", ".join("{:d}".format(value) for value in self))  # type: ignore


class Dev2SocketID:
    LAST_BUSID: Final[int] = 256
    SOCKETS_MASK: Final[int] = 0x00000007
    socket_ranges: List[int] = []
    socket_nodeid: List[int] = []
    socket_devs: List[PMONDevice] = []

    @staticmethod
    def scan_socketids(pmon: PMON) -> None:
        Dev2SocketID.socket_devs = pmon.scan(
            deviceids=Devices.SKX_UBOX_DID, vendorids=PCI_INTEL_VENDORID
        )
        for dev in Dev2SocketID.socket_devs:
            # first get node id for the local socket (socket number 0-7)
            nodeid: int = (
                pmon[dev.path].reg(Registers.ubox_lnid_offset).get(Size.DWORD)
                & Dev2SocketID.SOCKETS_MASK
            )
            # Every 3bits of the Node ID mapping register maps to a specific node
            # Read the Node ID Mapping Register and find the node that matches
            # the gid read from the Node ID configuration register (above).
            # e.g. Bits 2:0 map to node 0, bits 5:3 maps to package 1, etc.
            mapping: int = pmon[dev.path].reg(Registers.ubox_gid_offset).get(Size.DWORD)
            for bits in range(0, 8):
                if nodeid == (mapping >> (3 * bits)) & Dev2SocketID.SOCKETS_MASK:
                    Dev2SocketID.socket_nodeid.append(bits)
                    Dev2SocketID.socket_ranges.append(dev.bus)
                    break
        # add the last bus number to the socketID range
        Dev2SocketID.socket_ranges.append(Dev2SocketID.LAST_BUSID)

    @staticmethod
    def get(pmon: PMON, dev: PMONDevice) -> int:
        # Lets optimize this function a bit.
        if not Dev2SocketID.socket_devs:
            Dev2SocketID.scan_socketids(pmon)
        # Find the socketID within two socket_ranges values
        for idx, range in enumerate(Dev2SocketID.socket_ranges):
            if (
                Dev2SocketID.socket_ranges[idx] <= dev.bus
                and dev.bus < Dev2SocketID.socket_ranges[idx + 1]
            ):
                return Dev2SocketID.socket_nodeid[idx]
        return -1
