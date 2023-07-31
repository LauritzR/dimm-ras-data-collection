from typing import Any, Dict, List, Optional, Tuple, Union

from libs.pmon.pmon import (
    PMON_BUS,
    PMON_DEV,
    PMON_FUNC,
    PMON_SEG,
    CPUInfo,
    PMONDevice,
    PMONDriver,
    Registers,
    Size,
)
from libs.logger import pmon_logger as logger
from libs.vme_constants import (
    DEVICEID,
    PCI_AMD_VENDORID,
    PCI_INTEL_VENDORID,
    PCI_UNKNOWN_VENDORID,
    PROCESSOR_AMD_NAME,
    PROCESSOR_INTEL_NAME,
    VENDORID,
)

try:
    import vmware.vsi as vsi  # type: ignore
except ImportError:
    # To overcome problems with importing PMONSIDriver in UnitTests
    # try / except block has been provided.
    # This will be replaced with:
    # Stub vmware.vsi within PMONVSIDriver to exclude try/except block
    logger.error(
        "Unable to import vmware library, some of PMON functionality might not work.\n"
        "Try to load another PMON driver."
    )


class PMONVSIDriver(PMONDriver):
    """
    Class: PMONVSIDriver (based on PMONNullDriver)
    Description: This is a VSI strategy implementation of PMON
    """

    PCI_PATH: str = "/hardware/pci/seg/0x%s/bus/0x%s/slot/0x%s/func/0x%s/pciConfigReg/size/%d/addr/0x%x"
    MSR_PATH: str = "/hardware/msr/pcpu/%u/addr/0x%x"
    PCI_DEVS: str = "/hardware/pci/devices/"
    PCI_FUNC: str = "/hardware/pci/seg/%s/bus/%s/slot/%s/func/%s/"
    PCI_HEADER: str = "pciConfigHeader"
    CPU_INFO: str = "/hardware/cpu/cpuList/0"

    LABEL_FAMILY: str = "family"
    LABEL_MODEL: str = "model"
    LABEL_NAME: str = "name"

    name: str = "VSI"

    def _build_pci_path(
        self, seg: str, bus: str, slot: str, func: str, size: int, addr: int
    ) -> str:
        logger.debug(
            "[_build_pci_path] " + self.PCI_PATH % (seg, bus, slot, func, size, addr)
        )
        return self.PCI_PATH % (seg, bus, slot, func, size, addr)

    def get(
        self, node: Tuple[str, str, str, str], addr: Registers, size: Size = Size.DWORD
    ) -> Optional[int]:
        """
        Method: get(node, addr, size)
        Description: Function read [size] data from [addr] of [node]
        """
        logger.debug(
            "[GET] Driver: {0}, Device : {1}, Address : 0x{2:0X}, Size : {3}bits".format(
                self.name, node, addr.value, size.value * 8
            )
        )
        try:
            if size.value == int(Size.COUNTER.value):
                path: str = self._build_pci_path(
                    seg=node[0],
                    bus=node[1],
                    slot=node[2],
                    func=node[3],
                    size=4,
                    addr=addr.value,
                )
                low: int = int(vsi.get(path))
                path = self._build_pci_path(
                    seg=node[0],
                    bus=node[1],
                    slot=node[2],
                    func=node[3],
                    size=2,
                    addr=addr.value + 4,
                )
                high: int = int(vsi.get(path))
                value: int = (high << 32) + low
            else:
                path = self._build_pci_path(
                    seg=node[0],
                    bus=node[1],
                    slot=node[2],
                    func=node[3],
                    size=size.value,
                    addr=addr.value,
                )
                value = int(vsi.get(path))
        except Exception as err:
            logger.error(
                f"[GET] Unexpected vsi.get error : {err=}, {err.args=}, {size=} {node=}, {addr=}"
            )
            return None
        return value

    def set(self, node: Tuple[str, str, str, str], addr: Registers, value: int) -> None:
        """
        Method: set(node, addr, value)
        Description: Function writes [value] to [addr] of [node]
        """
        logger.debug(
            "[SET] Driver: {0}, Device : {1}, Address : 0x{2:0X}, Value : 0x{3:0X}".format(
                self.name, node, addr.value, value
            )
        )
        try:
            path: str = self._build_pci_path(
                seg=node[0],
                bus=node[1],
                slot=node[2],
                func=node[3],
                size=4,
                addr=addr.value,
            )
            vsi.set(path, value)
        except Exception as err:
            logger.error(
                f"[SET] Unexpected vsi.set error : {err=}, {err.args=}, {node=}, {addr=}, {value=}"
            )
        return None

    @staticmethod
    def read_msr(cpu: int, addr: int) -> Optional[int]:
        """
        Static method: read_msr(cpu, addr)
        Description: Read data from an MSR [addr] from a given logical [cpu].
        """
        try:
            value: int = vsi.get(PMONVSIDriver.MSR_PATH % (cpu, addr))
        except Exception as err:
            logger.error(
                f"[READ_MSR] Unexpected vsi.get error : {err=}, {err.args=}, {cpu=}, {addr=}"
            )
            return None
        return value

    @staticmethod
    def write_msr(cpu: int, addr: int, value: int) -> Optional[int]:
        """
        Static method: write_msr(cpu, addr, value)
        Description: Write [value] data to an MSR [addr] on given logical [cpu].
        """
        try:
            vsi.set(PMONVSIDriver.MSR_PATH % (cpu, addr), value)
        except Exception as err:
            logger.error(
                f"[WRITE_MSR] Unexpected vsi.set error : {err=}, {err.args=}, {cpu=}, {addr=}, {value=}"
            )
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
        for dev in vsi.list(PMONVSIDriver.PCI_DEVS):  # type: str
            try:
                info: Dict[str, Any] = vsi.get(
                    "%s%s/info" % (PMONVSIDriver.PCI_DEVS, dev)
                )
                pci: Dict[str, int] = vsi.get(
                    (PMONVSIDriver.PCI_FUNC + PMONVSIDriver.PCI_HEADER)
                    % (info[PMON_SEG], info[PMON_BUS], info[PMON_DEV], info[PMON_FUNC])
                )
            except Exception as err:
                logger.error(
                    f"[SCAN] Unexpected vsi.get error : {err=}, {err.args=}, {dev=}"
                )
                return []

            pci_deviceid: int = int(pci[DEVICEID])
            pci_vendorid: int = int(pci[VENDORID])
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
                        path="{0:04X}:{1:02X}:{2:02X}.{3:0X}".format(
                            info[PMON_SEG],
                            info[PMON_BUS],
                            info[PMON_DEV],
                            info[PMON_FUNC],
                        ),
                        seg=int(info[PMON_SEG]),
                        bus=int(info[PMON_BUS]),
                        dev=int(info[PMON_DEV]),
                        func=int(info[PMON_FUNC]),
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
        try:
            read_data = vsi.get(PMONVSIDriver.CPU_INFO)
            cpuinfo = CPUInfo()
            if read_data[PMONVSIDriver.LABEL_NAME] == PROCESSOR_INTEL_NAME:
                cpuinfo.vendorid = PCI_INTEL_VENDORID
            elif read_data[PMONVSIDriver.LABEL_NAME] == PROCESSOR_AMD_NAME:
                cpuinfo.vendorid = PCI_AMD_VENDORID
            else:
                cpuinfo.vendorid = PCI_UNKNOWN_VENDORID
            cpuinfo.model = int(read_data[PMONVSIDriver.LABEL_MODEL])
            cpuinfo.family = int(read_data[PMONVSIDriver.LABEL_FAMILY])

            logger.debug(
                f"[GET_CPUINFO] VendorID: {hex(cpuinfo.vendorid)} Model: {hex(cpuinfo.model)} Family: {hex(cpuinfo.family)}"
            )

        except Exception as err:
            logger.error(
                f"[GET_CPUINFO] Unexpected vsi.get error : {err=}, {err.args=}"
            )
            return CPUInfo()

        return cpuinfo
