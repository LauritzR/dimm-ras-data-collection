from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Final, List

METRICS_PMON_MEMORY_BW: Final[str] = "pmon.read_bw"
METRICS_PMON_SCRUBADDRESS: Final[str] = "pmon.read_scrubaddress"
METRICS_PMON_PMONCTR: Final[str] = "pmon.read_pmonctr"
METRICS_PMON_CORRERRCNT: Final[str] = "pmon.read_correrrcnt"
METRICS_PMON_DIMM_TEMP: Final[str] = "pmon.read_dimm_temp"
METRICS_PMON_PCICFG: Final[str] = "offline_addinfo.read_pcicfg"
METRICS_PMON_HWMON_TEMP: Final[str] = "hwmon.read_temp"

PMON_MEM_BW_RD: Final[str] = "mem_bw_rd"
PMON_MEM_BW_WR: Final[str] = "mem_bw_wr"
PMON_MEM_BW_TOTAL: Final[str] = "mem_bw_total"

HWMON_TEMP_SOCKET: Final[str] = "socket"
HWMON_TEMP_SENSOR: Final[str] = "sensor"
HWMON_TEMP_INPUT: Final[str] = "input"
HWMON_TEMP_MAX: Final[str] = "max"
HWMON_TEMP_CRIT: Final[str] = "crit"
HWMON_TEMP_LABEL: Final[str] = "label"

PMON_NODE_NAME: Final[str] = "node_name"
PMON_NODE_BUS: Final[str] = "bus"
PMON_NODE_DEV: Final[str] = "dev"
PMON_NODE_FUNC: Final[str] = "func"
PMON_SCRUBADDRESSLO: Final[str] = "scrubaddresslo"
PMON_SCRUBADDRESSHI: Final[str] = "scrubaddresshi"
PMON_EVENT_NAME: Final[str] = "event_name"
PMON_COUNTER: Final[str] = "counter"
PMON_PERIOD: Final[str] = "period"

PMON_CORRERRCNT_0: Final[str] = "correrrcnt_0"
PMON_CORRERRCNT_1: Final[str] = "correrrcnt_1"
PMON_CORRERRCNT_2: Final[str] = "correrrcnt_2"
PMON_CORRERRCNT_3: Final[str] = "correrrcnt_3"
PMON_CORRERRTHRSHLD_0: Final[str] = "correrrthrshld_0"
PMON_CORRERRTHRSHLD_1: Final[str] = "correrrthrshld_1"
PMON_CORRERRTHRSHLD_2: Final[str] = "correrrthrshld_2"
PMON_CORRERRTHRSHLD_3: Final[str] = "correrrthrshld_3"
PMON_CORRERRORSTATUS: Final[str] = "correrrorstatus"

PMON_TEMP_CHANNEL_0: Final[str] = "channel0_max_temp"
PMON_TEMP_CHANNEL_1: Final[str] = "channel1_max_temp"
PMON_TEMP_CHANNEL_2: Final[str] = "channel2_max_temp"
PMON_TEMP_CHANNEL_3: Final[str] = "channel3_max_temp"


class ABSPMONValues(ABC):
    pass

@dataclass
class PMONBWValues(ABSPMONValues):
    node_name: str
    mem_bw_rd: float
    mem_bw_wr: float
    mem_bw_total: float
    period: float


@dataclass
class PMONScrubaddressValues(ABSPMONValues):
    node_name: str
    scrubaddresslo: float
    scrubaddresshi: float


@dataclass
class PMONPmoncntrValues(ABSPMONValues):
    node_name: str
    event_name: str
    counter: float
    period: float


@dataclass
class PMONDevicesWithRegisters:
    path: str
    seg: int
    bus: int
    dev: int
    func: int
    regs: Dict[str, int]


@dataclass
class PMONPCICFGValues(ABSPMONValues):
    devices: List[PMONDevicesWithRegisters]


@dataclass
class HWMONTempValues(ABSPMONValues):
    input: float
    max: float
    crit: float
    socket: int
    sensor: int
    socket_sensor: int
    label: str


@dataclass
class PMONCorrerrcntValues(ABSPMONValues):
    node_name: str
    correrrcnt_0: int
    correrrcnt_1: int
    correrrcnt_2: int
    correrrcnt_3: int
    correrrthrshld_0: int
    correrrthrshld_1: int
    correrrthrshld_2: int
    correrrthrshld_3: int
    correrrorstatus: int

@dataclass
class PMONTRMLMaxTempValues(ABSPMONValues):
    node_name: str
    channel0_max_temp: int
    channel1_max_temp: int
    channel2_max_temp: int
    channel3_max_temp: int
