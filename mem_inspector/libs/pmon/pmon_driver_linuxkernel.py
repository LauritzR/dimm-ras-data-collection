import os
import re
from typing import List, Optional, Tuple, Union

from libs.pmon.pmon import CPUInfo, PMONDevice, PMONDriver, Registers, Size
from libs.logger import pmon_logger as logger
from libs.vme_constants import (
    PCI_AMD_VENDORID,
    PCI_INTEL_VENDORID,
    PCI_UNKNOWN_VENDORID,
    PROCESSOR_AMD_NAME,
    PROCESSOR_INTEL_NAME,
)


class PMONLinuxKernelDriver(PMONDriver):
    """
    Class: PMONLinuxKernelDriver(based on PMONDriver)
    Description: This is a /sys/devices/pci0000:* based driver using linux kernel space access
    """

    MSR_PATH: str = "/dev/cpu/%d/msr"
    PCI_DEVS: str = "/sys/bus/pci/devices"
    PCI_PATH: str = PCI_DEVS + "/%04x:%02x:%02x.%01x/%s"
    FILE_CPUINFO: str = "/proc/cpuinfo"
    LABEL_VENDORID: str = "vendor_id"
    LABEL_MODEL: str = "model"
    LABEL_CPU_FAMILY: str = "cpu family"

    name: str = "LinuxKernel"

    cpuinfo_file: str = FILE_CPUINFO

    @staticmethod
    def _build_pci_path(node: Tuple[str, str, str, str], file: str) -> str:
        seg: int = int(node[0], 16)
        bus: int = int(node[1], 16)
        dev: int = int(node[2], 16)
        func: int = int(node[3], 16)
        logger.debug(
            "[_build_pci_path] "
            + PMONLinuxKernelDriver.PCI_PATH % (seg, bus, dev, func, file)
        )
        return PMONLinuxKernelDriver.PCI_PATH % (seg, bus, dev, func, file)

    def get(
        self, node: Tuple[str, str, str, str], addr: Registers, size: Size = Size.DWORD
    ) -> int:
        """
        Method: get(node, addr, size)
        Description: Function read [size] data from [addr] of [node]
        """
        if not os.path.isdir(PMONLinuxKernelDriver.PCI_DEVS) or not os.path.isfile(
            PMONLinuxKernelDriver._build_pci_path(node, "config")
        ):
            logger.error(
                f"Problem with using Linux kernel, system directory {PMONLinuxKernelDriver.PCI_DEVS} desn't exist."
            )
            return -1

        configspace = os.open(
            PMONLinuxKernelDriver._build_pci_path(node, "config"), os.O_RDONLY
        )
        os.lseek(configspace, addr.value, os.SEEK_SET)

        value: int
        if size.value == int(Size.COUNTER.value):
            low: int = int.from_bytes(os.read(configspace, 4), "little")
            high: int = int.from_bytes(os.read(configspace, 2), "little")
            value = (high << 32) + low
        else:
            value = int.from_bytes(os.read(configspace, size.value), "little")

        os.close(configspace)
        return value

    def set(self, node: Tuple[str, str, str, str], addr: Registers, value: int) -> None:
        """
        Method: set(node, addr, value)
        Description: Function writes [value] to [addr] of [node]
        """
        if not os.path.isdir(PMONLinuxKernelDriver.PCI_DEVS) or not os.path.isfile(
            PMONLinuxKernelDriver._build_pci_path(node, "config")
        ):
            logger.error(
                f"Problem with using Linux kernel, system directory {PMONLinuxKernelDriver.PCI_DEVS} desn't exist."
            )
            return None

        configspace = os.open(
            PMONLinuxKernelDriver._build_pci_path(node, "config"), os.O_WRONLY
        )
        os.lseek(configspace, addr.value, os.SEEK_SET)
        os.write(configspace, (value).to_bytes(4, byteorder="little"))
        os.close(configspace)
        return None

    @staticmethod
    def read_msr(cpu: int, addr: int) -> Optional[int]:
        """
        Static method: read_msr(cpu, addr)
        Description: Read data from an MSR [addr] from a given logical [cpu].
        """
        if not os.path.exists(PMONLinuxKernelDriver.MSR_PATH % cpu):
            print(
                f"Problem with using Linux kernel, system file {PMONLinuxKernelDriver.MSR_PATH % cpu} desn't exist."
            )
            return -1
        msr = os.open(PMONLinuxKernelDriver.MSR_PATH % cpu, os.O_RDONLY)
        os.lseek(msr, addr, os.SEEK_SET)

        value = int.from_bytes(os.read(msr, 8), "little")
        os.close(msr)
        return value

    @staticmethod
    def write_msr(cpu: int, addr: int, value: int) -> Optional[int]:
        """
        Static method: write_msr(cpu, addr, value)
        Description: Write [value] data to an MSR [addr] on given logical [cpu].
        """
        if not os.path.exists(PMONLinuxKernelDriver.MSR_PATH % cpu):
            logger.error(
                f"Problem with using Linux kernel, system file {PMONLinuxKernelDriver.MSR_PATH % cpu} desn't exist."
            )
            return -1
        msr = os.open(PMONLinuxKernelDriver.MSR_PATH % cpu, os.O_WRONLY)
        os.lseek(msr, addr, os.SEEK_SET)
        os.write(msr, (value).to_bytes(8, byteorder="little"))
        os.close(msr)
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

        devlist: List[PMONDevice] = []
        pci_deviceid: int
        pci_vendorid: int
        if not os.path.isdir(PMONLinuxKernelDriver.PCI_DEVS):
            logger.error(
                f"Problem with using Linux kernel, system directory {PMONLinuxKernelDriver.PCI_DEVS} desn't exist."
            )
            return devlist

        for path in sorted(os.listdir(PMONLinuxKernelDriver.PCI_DEVS)):
            sbdf: Tuple[str, str, str, str] = tuple(re.split(r":|\.", path))  # type: ignore
            with open(PMONLinuxKernelDriver._build_pci_path(sbdf, "device"), "r") as f:
                pci_deviceid = int(f.read(), 16)
            with open(PMONLinuxKernelDriver._build_pci_path(sbdf, "vendor"), "r") as f:
                pci_vendorid = int(f.read(), 16)

            add_deviceid: bool = True
            add_vendorid: bool = True
            if vendorids:
                add_vendorid = pci_vendorid in vendorids
            if deviceids:
                add_deviceid = pci_deviceid in deviceids

            logger.debug(
                "[SCAN] vendorid: %s/%s, deviceid: %d/%s"
                % (pci_vendorid, str(add_vendorid), pci_deviceid, str(add_deviceid))
            )
            if add_deviceid and add_vendorid:
                devlist.append(
                    PMONDevice(
                        path=path,
                        seg=int(sbdf[0], 16),
                        bus=int(sbdf[1], 16),
                        dev=int(sbdf[2], 16),
                        func=int(sbdf[3], 16),
                        did=pci_deviceid,
                        vid=pci_vendorid,
                    )
                )
        return devlist

    @staticmethod
    def get_cpuinfo() -> CPUInfo:
        """
        Static method: getCPUInfo()
        Description: Get CPU specific information:
            vendorID, model, family
        """
        cpuinfo = CPUInfo()
        if not os.path.isfile(PMONLinuxKernelDriver.cpuinfo_file):
            logger.error(f"File {PMONLinuxKernelDriver.cpuinfo_file} desn't exist")
            return cpuinfo
        with open(PMONLinuxKernelDriver.cpuinfo_file, "r") as file:
            for count, line in enumerate(file):
                if count > 20:
                    break
                word: Tuple[str, ...] = tuple(re.split(r"\t: ", line.strip()))
                # split each line into word list, split word into key and value
                key: str = word[0]
                value: Union[str, int] = word[1]
                if key == PMONLinuxKernelDriver.LABEL_VENDORID:
                    if value == PROCESSOR_INTEL_NAME:
                        cpuinfo.vendorid = PCI_INTEL_VENDORID
                    elif value == PROCESSOR_AMD_NAME:
                        cpuinfo.vendorid = PCI_AMD_VENDORID
                    else:
                        cpuinfo.vendorid = PCI_UNKNOWN_VENDORID
                if key == PMONLinuxKernelDriver.LABEL_MODEL + "\t":
                    cpuinfo.model = int(value)
                if key == PMONLinuxKernelDriver.LABEL_CPU_FAMILY:
                    cpuinfo.family = int(value)
        return cpuinfo
