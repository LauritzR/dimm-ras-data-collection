"""
Uncore Performance Monitoring Class
Set of tools for PCICFG and MSR manipulation
- support ESXi VSI
"""
import re
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, List, Optional, Tuple, Type, Union

PMON_PATH: Final[str] = "path"
PMON_SEG: Final[str] = "seg"
PMON_BUS: Final[str] = "bus"
PMON_DEV: Final[str] = "dev"
PMON_FUNC: Final[str] = "func"


@dataclass
class PMONDevice:
    path: str = ""
    seg: int = 0
    bus: int = 0
    dev: int = 0
    func: int = 0
    did: int = 0
    vid: int = 0


@dataclass
class CPUInfo:
    vendorid: int = 0x0
    model: int = 0x0
    family: int = 0x0


@dataclass
class PCIProp:
    val: Final[int] = 0
    bus: Final[int] = 0
    dev: Final[int] = 0
    func: Final[int] = 0
    desc: Final[str] = ""


class DeviceDescriptions:
    """
    Class: DeviceDescriptions
    Description: Implement Device description units
    """

    IMC0C0_1LMS: Final[PCIProp] = PCIProp(0x2042, 2, 10, 2, "IMC0C0")
    IMC0C1_1LMS: Final[PCIProp] = PCIProp(0x2046, 2, 10, 6, "IMC0C1")
    IMC0C2_1LMS: Final[PCIProp] = PCIProp(0x204A, 2, 11, 2, "IMC0C2")
    IMC1C0_1LMS: Final[PCIProp] = PCIProp(0x2042, 2, 12, 2, "IMC1C0")
    IMC1C1_1LMS: Final[PCIProp] = PCIProp(0x2046, 2, 12, 6, "IMC1C1")
    IMC1C2_1LMS: Final[PCIProp] = PCIProp(0x204A, 2, 13, 2, "IMC1C2")


class Devices:
    """
    Class: Devices
    Description: Implement Device units
    """

    SKX_UBOX_DID: Final[int] = 0x2014
    IMC0C0_MAIN_DECS: Final[int] = 0x2040
    IMC1C0_MAIN_DECS: Final[int] = 0x2040
    IMC0C0_1LMS: Final[int] = 0x2042
    IMC0C1_1LMS: Final[int] = 0x2046
    IMC0C2_1LMS: Final[int] = 0x204A
    IMC1C0_1LMS: Final[int] = 0x2042
    IMC1C1_1LMS: Final[int] = 0x2046
    IMC1C2_1LMS: Final[int] = 0x204A
    IMC0C0_1LMDP: Final[int] = 0x2043
    IMC0C1_1LMDP: Final[int] = 0x2047
    IMC0C2_1LMDP: Final[int] = 0x204B
    IMC1C0_1LMDP: Final[int] = 0x2043
    IMC1C1_1LMDP: Final[int] = 0x2047
    IMC1C2_1LMDP: Final[int] = 0x204B


class Size(Enum):
    """
    Enum Class: Size
    Description: Implement external data size format for get/set operations
    """

    BYTE = 1
    WORD = 2
    DWORD = 4
    COUNTER = 6


class Registers(Enum):
    """
    Enum Class: Registers
    Description: Implement Registers adresses i.e Controlers / Counters
    """

    vendorid = 0x0
    memtrmltemprep = 0x60
    pmoncntr_0 = 0xA0
    pmoncntr_1 = 0xA8
    pmoncntr_2 = 0xB0
    pmoncntr_3 = 0xB8
    pmoncntr_4 = 0xC0
    pmoncntrcfg_0 = 0xD8
    pmoncntrcfg_1 = 0xDC
    pmoncntrcfg_2 = 0xE0
    pmoncntrcfg_3 = 0xE4
    pmoncntrcfg_4 = 0xE8
    correrrcnt_0 = 0x104
    correrrcnt_1 = 0x108
    correrrcnt_2 = 0x10C
    correrrcnt_3 = 0x110
    correrrthrshld_0 = 0x11C
    correrrthrshld_1 = 0x120
    correrrthrshld_2 = 0x124
    correrrthrshld_3 = 0x128
    correrrorstatus = 0x134
    scrubaddresslo = 0x90C
    scrubaddresshi = 0x910
    scrubctl = 0x914
    smisparectl = 0x924
    scrubaddress2lo = 0x950
    scrubaddress2hi = 0x954
    scrubmask = 0x96C
    ubox_lnid_offset = 0xC0
    ubox_gid_offset = 0xD4


@dataclass
class EventItem:
    umask: Final[str] = ""
    ev_sel: Final[int] = 0


class Events(Enum):
    """
    Enum Class: Events
    Description: Implement external Events map with mask and ev_sel values
    """

    CAS_COUNT_RD = EventItem("00000011", 0x04)
    CAS_COUNT_WR = EventItem("00001100", 0x04)
    ECC_CORRECTABLE_ERRORS = EventItem("00000000", 0x09)
    RD_CAS_RANK0 = EventItem("00010000", 0xB0)
    RD_CAS_RANK1 = EventItem("00010000", 0xB1)
    RD_CAS_RANK2 = EventItem("00010000", 0xB2)
    RD_CAS_RANK3 = EventItem("00010000", 0xB3)
    RD_CAS_RANK4 = EventItem("00010000", 0xB4)
    RD_CAS_RANK5 = EventItem("00010000", 0xB5)
    RD_CAS_RANK6 = EventItem("00010000", 0xB6)
    RD_CAS_RANK7 = EventItem("00010000", 0xB7)
    WR_CAS_RANK0 = EventItem("00010000", 0xB8)
    WR_CAS_RANK1 = EventItem("00010000", 0xB9)
    WR_CAS_RANK2 = EventItem("00010000", 0xBA)
    WR_CAS_RANK3 = EventItem("00010000", 0xBB)
    WR_CAS_RANK4 = EventItem("00010000", 0xBC)
    WR_CAS_RANK5 = EventItem("00010000", 0xBD)
    WR_CAS_RANK6 = EventItem("00010000", 0xBE)
    WR_CAS_RANK7 = EventItem("00010000", 0xBF)


class PMONDriver(ABC):
    """
    Class: PMONDriver
    Description: This is a base class of PMON function strategies
    """

    name: Optional[str] = None

    def get(
        self, node: Tuple[str, str, str, str], addr: Registers, size: Size = Size.DWORD
    ) -> Optional[int]:
        return 0

    def set(self, node: Tuple[str, str, str, str], addr: Registers, value: int) -> None:
        return None

    @staticmethod
    def read_msr(cpu: int, addr: int) -> Optional[int]:
        return None

    @staticmethod
    def write_msr(cpu: int, addr: int, value: int) -> Optional[int]:
        return None

    @staticmethod
    def scan(
        vendorids: Union[int, List[int]] = [], deviceids: Union[int, List[int]] = []
    ) -> List[PMONDevice]:
        return []

    @staticmethod
    def get_cpuinfo() -> CPUInfo:
        return CPUInfo()


class PMON:
    """
    Class: PMON
    Description: PMON class is producing factories objects based on supported PCI device functions
    within given driver strategy.
    """

    driver: Type[PMONDriver] = PMONDriver

    def __init__(self, driver: Type[PMONDriver]) -> None:
        self.driver = driver

    def __getitem__(self, search: str) -> Any:
        """
        Method: index [] methd
        Desription: The magic method __getitem__ is used for accessing node methods on given address
        """

        class Unit:
            """
            Class: PMON
            Description: PMON class is producing factories objects based on supported PCI device functions
            within given driver strategy.
            """

            parent: PMON
            node: Tuple[str, str, str, str]

            def __init__(self, parent: PMON, node: Tuple[str, str, str, str]) -> None:
                self.parent = parent
                self.node = node

            def reg(self, register: Registers) -> Any:
                """
                Method: PMON[addr].reg( register )
                Description: Functions retuns an Register class for set/get operations
                """

                class Register(self.parent.driver):  # type: ignore
                    parent: Unit
                    register: Registers

                    def __init__(self, parent: Unit, register: Registers) -> None:
                        self.parent = parent
                        self.register = register

                    def info(
                        self,
                    ) -> Tuple[Optional[str], Tuple[str, str, str, str], Registers]:
                        """
                        Method: PMON[addr].reg(register).info()
                        Description: Prints debug info
                        """
                        print(
                            "Driver: %s, Device : %s, Register : %s"
                            % (super().name, self.parent.node, self.register)
                        )
                        return (super().name, self.parent.node, self.register)

                    def set_event(
                        self,
                        event: Events,
                        enable: bool = True,
                        reset: bool = True,
                    ) -> Optional[int]:
                        """
                        Method: PMON[addr].reg(register).set_event(Events.Type)
                        Description: Set CTRL registry and set event i.e counters

                        According to Table 1-6. Baseline *_PMON_CTLx Register – Field Definitions
                        [bits]        [field]
                        63:32         rsv             Only relevant to unit’s that use 64b control registers
                        31:24         thresh
                          23          invert
                          22          en
                          21          rsv
                          20          ov_en
                          19          rsv
                          18          edge_det
                          17          rst
                          16          rsv
                        15:8          umask
                         7:0          ev_sel

                        ev_sel = 0x04         According to 2.3.5 iMC Box Events Ordered By Code
                        umask  = 0x0F
                        rsv    = 0
                        en     = 1            "Local Counter Enable" set to 1
                        rst    = 1            "When set to 1, the corresponding counter will be cleared to 0"
                        """
                        thresh: str = "00000000"
                        invert: str = "0"
                        en: str = "1" if enable else "0"
                        rsv: str = "0"
                        ov_en: str = "0"
                        edge_det: str = "0"
                        rst: str = "1" if reset else "0"

                        pmu_str: str = (
                            thresh
                            + invert
                            + en
                            + rsv
                            + ov_en
                            + rsv
                            + edge_det
                            + rst
                            + rsv
                            + str(event.value.umask)
                            + str("{0:0>8b}".format(event.value.ev_sel))
                        )
                        pmu_data: int = int(pmu_str, 2)
                        self.set(pmu_data)
                        return None

                    def get(self, size: Size = Size.DWORD) -> int:
                        """
                        Method: PMON[addr].reg(register).get(size)
                        Description: Returns value from given register on node addr.
                        """
                        return super().get(self.parent.node, self.register, size)  # type: ignore

                    def set(self, value: int) -> None:
                        """
                        Method: PMON[addr].reg(register).set(value)
                        Description: Set value of given register on node addr.
                        """
                        super().set(self.parent.node, self.register, value)
                        return None

                return Register(self, register)

        return Unit(self, tuple(re.split(r":|\.", search)))  # type: ignore

    def read_msr(self, cpu: int, addr: int) -> Optional[int]:
        """
        Method: read_msr(cpu, addr)
        Description: Read data from an MSR [addr] from a given logical [cpu].
        """
        return self.driver.read_msr(cpu, addr)

    def write_msr(self, cpu: int, addr: int, value: int) -> Optional[int]:
        """
        static Method: write_msr(cpu, addr, value)
        Description: Write [value] data to an MSR [addr] on given logical [cpu].
        """
        return self.driver.write_msr(cpu, addr, value)

    def scan(
        self,
        vendorids: Union[int, List[int]] = [],
        deviceids: Union[int, List[int]] = [],
    ) -> List[PMONDevice]:
        """
        static Method: scan(vendorids, deviceids)
        Description: Scan all pci config space devices and filter them
        by vendorIDs and deviceIDs
        """
        return self.driver.scan(vendorids, deviceids)

    def get_cpuinfo(self) -> CPUInfo:
        """
        Method: getCPUInfo()
        Description: Get CPU specific information:
        vendorID, model, family
        """
        return self.driver.get_cpuinfo()
