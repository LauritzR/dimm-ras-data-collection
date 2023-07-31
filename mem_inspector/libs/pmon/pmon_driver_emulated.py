import os
import re
from typing import Any, Dict, Final, List, Optional, Tuple, Union

from libs.pmon.pmon import CPUInfo, PMONDevice, PMONDriver, Registers, Size
from libs.logger import pmon_logger as logger
from libs.vme_constants import (
    PCI_AMD_VENDORID,
    PCI_INTEL_VENDORID,
    PCI_UNKNOWN_VENDORID,
    PROCESSOR_AMD_NAME,
    PROCESSOR_INTEL_NAME,
)


class PMONEmulatedDriver(PMONDriver):
    """
    Class: PMONEmulatedDriver(based on PMONDriver)
    Description: This is a replacement for old legacy lspci/setpci strategy based of output of lspci -D -xxx
    """

    FILE_CPUINFO: Final[str] = "/proc/cpuinfo"
    LABEL_VENDORID: Final[str] = "vendor_id"
    LABEL_MODEL: Final[str] = "model"
    LABEL_CPU_FAMILY: Final[str] = "cpu family"

    name: Final[str] = "Emulated"

    dump_file: str = ""
    dump_data: Dict[str, Any] = {}
    cpuinfo_file: str = FILE_CPUINFO

    def get(
        self, node: Tuple[str, str, str, str], addr: Registers, size: Size = Size.DWORD
    ) -> int:
        """
        Method: get(node, addr, size)
        Description: Function read [size] data from [addr] of [node]
        """
        if PMONEmulatedDriver.dump_file:
            if not PMONEmulatedDriver.dump_data:
                PMONEmulatedDriver.readdump()
            path = str("%s:%s:%s.%s" % node)
            value: int = int.from_bytes(
                PMONEmulatedDriver.dump_data[path][
                    addr.value : addr.value + size.value
                ],
                "little",
            )
            logger.debug(
                f"[GET] pmon[{path}].reg({hex(addr.value)}).get({size.value}) = {value}"
            )
            return value
        else:
            unit: str
            if size.value == 1:
                unit = "b"
            elif size.value == 2:
                unit = "w"
            else:
                unit = "l"
            cmd: str = "setpci -s %s %s.%s" % (
                str("%s:%s:%s.%s" % node),
                hex(addr.value),
                unit,
            )
            logger.debug("[GET] %s" % cmd)
            stream = os.popen(cmd)
            output: str = stream.read()
            stream.close()
            if size.value == 6:
                cmd = "setpci -s %s %s.%s" % (
                    str("%s:%s:%s.%s" % node),
                    hex(addr.value + 4),
                    "w",
                )
                logger.debug("[GET] %s" % cmd)
                stream = os.popen(cmd)
                hi: str = stream.read()
                stream.close()
                lo: str = output
                sum = (int(hi, 16) << 32) + int(lo, 16)
                return sum
            else:
                return int(output, 16)

    def set(self, node: Tuple[str, str, str, str], addr: Registers, value: int) -> None:
        """
        Method: set(node, addr, value)
        Description: Function writes [value] to [addr] of [node]
        """
        if PMONEmulatedDriver.dump_file:
            if not PMONEmulatedDriver.dump_data:
                PMONEmulatedDriver.readdump()
            path = str("%s:%s:%s.%s" % node)
            size = 4
            PMONEmulatedDriver.dump_data[path][addr.value : addr.value + 4] = (
                value
            ).to_bytes(size, byteorder="little")
            logger.debug(f"[SET] pmon[{path}].reg({hex(addr.value)}).set({value})")

        else:
            cmd: str = "setpci -s %s %s.%s=%s" % (
                str("%s:%s:%s.%s" % node),
                hex(addr.value),
                "l",
                hex(value),
            )
            logger.debug("[SET] %s" % cmd)
            stream = os.popen(cmd)
            stream.close()

        return None

    @staticmethod
    def readdump() -> None:
        if not os.path.isfile(PMONEmulatedDriver.dump_file):
            logger.error(f"File {PMONEmulatedDriver.dump_file} desn't exist")
            return None
        file = open(PMONEmulatedDriver.dump_file, "rb")
        PMONEmulatedDriver.dump_data = {}
        dataload = bytearray()
        devname = ""
        for line in file:
            words = line.split()
            if not len(words):
                continue
            if len(words[0]) == 12:
                if devname:
                    PMONEmulatedDriver.dump_data[devname] = dataload
                devname = words[0].decode("utf-8")
                dataload = bytearray()
                continue
            for word in words[1:]:
                byte = int(word, 16)
                dataload.append(byte)
        file.close()
        PMONEmulatedDriver.dump_data[devname] = dataload
        logger.debug(
            f"[READDUMP] {PMONEmulatedDriver.dump_file=} has {len(PMONEmulatedDriver.dump_data.keys())} records"
        )
        return None

    @staticmethod
    def read_msr(cpu: int, addr: int) -> Optional[int]:
        """
        Static method: read_msr(cpu, addr)
        Description: Read data from an MSR [addr] from a given logical [cpu].
        """
        return None

    @staticmethod
    def write_msr(cpu: int, addr: int, value: int) -> Optional[int]:
        """
        Static method: write_msr(cpu, addr, value)
        Description: Write [value] data to an MSR [addr] on given logical [cpu].
        """
        return None

    @staticmethod
    def scan(
        vendorids: Union[int, List[int]] = [], deviceids: Union[int, List[int]] = []
    ) -> List[PMONDevice]:
        """
        Static method: scan(vendorids, deviceids)
        Description: Scan all pci devices and filter vendorIDs and deviceIDs devices
        """
        deviceids = [deviceids] if isinstance(deviceids, int) else deviceids
        vendorids = [vendorids] if isinstance(vendorids, int) else vendorids
        devid: str = ".. .."
        venid: str = ".. .."
        if vendorids:
            list: List[str] = []
            for data in vendorids:  # type: int
                lo: int = data & 0xFF
                hi: int = data >> 8 & 0xFF
                list.append("{0:02X} {1:02X}".format(lo, hi))
            venid = "(" + "|".join(list) + ")"
        if deviceids:
            list = []
            for data in deviceids:
                lo = data & 0xFF
                hi = data >> 8 & 0xFF
                list.append("{0:02X} {1:02X}".format(lo, hi))
            devid = "(" + "|".join(list) + ")"

        filter: str = 'egrep -i "^00: %s %s" -B 1' % (venid, devid)
        cmd: str = (
            "cat %s" % (PMONEmulatedDriver.dump_file)
            if PMONEmulatedDriver.dump_file
            else "lspci -xxxx -D"
        )

        cmd = f"{cmd} | {filter}"
        logger.debug("[SCAN] %s" % cmd)

        stream = os.popen(cmd)
        output = stream.read()
        stream.close()

        devlist: List[PMONDevice] = []
        pmon_device: PMONDevice
        for dev in re.split("\n", output):  # type: str
            word: Tuple[str, ...] = tuple(re.split(r"\ ", dev))
            # The first word of parsed line is a node name
            node: str = word[0]

            if len(node) == 12:
                sbdf: Tuple[str, str, str, str] = tuple(re.split(r":|\.", node))  # type: ignore
                pmon_device = PMONDevice(
                    path=node,
                    seg=int(sbdf[0], 16),
                    bus=int(sbdf[1], 16),
                    dev=int(sbdf[2], 16),
                    func=int(sbdf[3], 16),
                )
            elif node == "00:":
                pmon_device.vid = (int(word[2], 16) << 8) + int(word[1], 16)
                pmon_device.did = (int(word[4], 16) << 8) + int(word[3], 16)
                devlist.append(pmon_device)
        return devlist

    @staticmethod
    def get_cpuinfo() -> CPUInfo:
        """
        Static method: getCPUInfo()
        Description: Get CPU specific information:
            vendorID, model, family
        """
        cpuinfo = CPUInfo()
        if not os.path.isfile(PMONEmulatedDriver.cpuinfo_file):
            logger.error(f"File {PMONEmulatedDriver.cpuinfo_file} desn't exist")
            return cpuinfo
        with open(PMONEmulatedDriver.cpuinfo_file, "r") as file:
            for count, line in enumerate(file):
                if count > 20:
                    break
                word: Tuple[str, ...] = tuple(re.split(r"\t: ", line.strip()))
                # split each line into word list, split word into key and value
                key: str = word[0]
                value: Union[str, int] = word[1]
                if key == PMONEmulatedDriver.LABEL_VENDORID:
                    if value == PROCESSOR_INTEL_NAME:
                        cpuinfo.vendorid = PCI_INTEL_VENDORID
                    elif value == PROCESSOR_AMD_NAME:
                        cpuinfo.vendorid = PCI_AMD_VENDORID
                    else:
                        cpuinfo.vendorid = PCI_UNKNOWN_VENDORID
                if key == PMONEmulatedDriver.LABEL_MODEL + "\t":
                    cpuinfo.model = int(value)
                if key == PMONEmulatedDriver.LABEL_CPU_FAMILY:
                    cpuinfo.family = int(value)
        return cpuinfo
