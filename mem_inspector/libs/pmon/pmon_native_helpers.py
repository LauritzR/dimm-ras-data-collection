import asyncio
import os
import socket
from datetime import datetime
from functools import lru_cache
from typing import Dict, List

from libs.data_processors import AbsDataProcessor
from libs.hwmon.hwmon import HWMON
from libs.native import NativeCallMap
from libs.pmon.pmon import (  # noqa: E402
    PMON,
    Devices,
    Events,
    PMONDevice,
    Registers,
    Size,
)

# from libs.pmon.pmon_driver_emulated import PMONEmulatedDriver
# from libs.pmon.pmon_driver_vsi import PMONVSIDriver  # noqa: E402
from libs.pmon.pmon_driver_linuxkernel import PMONLinuxKernelDriver
from libs.pmon.pmon_utils import count_bw, get_bitfield, measure
from libs.logger import pmon_logger as logger
from libs.metric_values import AbsMetricValues, MetricMetaData, PMONMetricValues
from libs.pmon.pmon_metric_values import (
    METRICS_PMON_CORRERRCNT,
    METRICS_PMON_DIMM_TEMP,
    METRICS_PMON_HWMON_TEMP,
    METRICS_PMON_MEMORY_BW,
    METRICS_PMON_PCICFG,
    METRICS_PMON_PMONCTR,
    METRICS_PMON_SCRUBADDRESS,
    HWMONTempValues,
    PMONBWValues,
    PMONCorrerrcntValues,
    PMONDevicesWithRegisters,
    PMONPCICFGValues,
    PMONPmoncntrValues,
    PMONScrubaddressValues,
    PMONTRMLMaxTempValues,
)
from libs.vme_constants import PCI_INTEL_VENDORID

pmon = PMON(PMONLinuxKernelDriver)
hwmon = HWMON()

@lru_cache
def get_unique_host_id() -> str:
    host_id: str = "/sys/devices/virtual/dmi/id/product_serial"
    if os.path.exists(host_id):
        with open(host_id, "r") as file:
            return file.read().replace("\n", "")
    else:
        return socket.gethostname()


@lru_cache
def scan_and_cache_all_imc() -> List[PMONDevice]:
    return pmon.scan(
        deviceids=[
            Devices.IMC0C0_1LMS,
            Devices.IMC0C1_1LMS,
            Devices.IMC0C2_1LMS,
            Devices.IMC1C0_1LMS,
            Devices.IMC1C1_1LMS,
            Devices.IMC1C2_1LMS,
        ]
    )


@lru_cache
def scan_and_cache_correrr_imc() -> List[PMONDevice]:
    return pmon.scan(deviceids=[Devices.IMC0C0_1LMDP])


""" Python Native Function syntax:

    async def function_name(out: AbsDataProcessor, args: List[str]) -> None:

    out = DataProcessor - object responsible for data parsing
        (buffering, filtering, serialization, compression) and further
        data transfer over network
    args = List of string that represent the function params

    return value : None
"""


async def read_scrubaddress(out: AbsDataProcessor, args: List[str]) -> None:
    """
    read_scrubaddress - Simple function that demonstrate process of fetching
    scrubaddresslo and scrubaddresshi registers using PMON.
    Registers pair contains part of the address of the last patrol scrub request.
    During memtest, failing address is logged in this register.

    Params:
        args[0] - "node name" i.e "0000:D0:06.1"
    """
    if not len(args):
        logger.error("Missing node param")
        return None
    node = str(args[0])

    await asyncio.sleep(1)

    data = PMONMetricValues(
        meta=MetricMetaData(
            tool=METRICS_PMON_SCRUBADDRESS,
            creation_timestamp=datetime.utcnow(),
            hostname=get_unique_host_id(),
        ),
        metrics=PMONScrubaddressValues(
            node_name=node,
            scrubaddresslo=pmon[node].reg(Registers.scrubaddresslo).get(Size.DWORD),
            scrubaddresshi=pmon[node].reg(Registers.scrubaddresshi).get(Size.DWORD),
        ),
    )
    out.write_metric([data])


async def read_pmoncntr(out: AbsDataProcessor, args: List[str]) -> None:
    """
    read_pmoncntr - Return IMC controller read operation traffic
        over time period.

    Params:
        args[0] - "node name" i.e "0000:D0:06.1"
        args[1] - sleep inteval (in seconds) i.e "5"
    """
    if len(args) < 2:
        logger.error("Missing params, usage: read_pmoncntr node time")
        return None

    node = str(args[0])
    sleep_time = int(args[1])
    pmon[node].reg(Registers.pmoncntrcfg_0).set_event(Events.CAS_COUNT_RD)
    await asyncio.sleep(sleep_time)
    pmon[node].reg(Registers.pmoncntrcfg_0).set_event(Events.CAS_COUNT_RD, False, False)

    data = PMONMetricValues(
        meta=MetricMetaData(
            tool=METRICS_PMON_PMONCTR,
            creation_timestamp=datetime.utcnow(),
            hostname=get_unique_host_id(),
        ),
        metrics=PMONPmoncntrValues(
            node_name=node,
            event_name="CAS_COUNT_RD",
            counter=pmon[node].reg(Registers.pmoncntr_0).get(Size.COUNTER),
            period=sleep_time,
        ),
    )
    pmon[node].reg(Registers.pmoncntrcfg_0).set_event(Events.CAS_COUNT_RD, False, True)
    out.write_metric([data])


async def read_bw(out: AbsDataProcessor, args: List[str]) -> None:
    """
    read_bw - Return all IMC controllers total bandwidth
        over time period.

    Params:
        args[0] - sleep inteval (in seconds) i.e "5"
    """
    if len(args) < 1:
        logger.error("Missing params, usage: read_bw time")
        return None
    period = int(args[0])

    cached_scan_devs = scan_and_cache_all_imc()
    result = await asyncio.gather(
        *(
            measure(
                pmon,
                dev.path,
                Registers.pmoncntrcfg_0,
                Registers.pmoncntr_0,
                Events.CAS_COUNT_RD,
                period,
            )
            for dev in cached_scan_devs
        ),
        *(
            measure(
                pmon,
                dev.path,
                Registers.pmoncntrcfg_1,
                Registers.pmoncntr_1,
                Events.CAS_COUNT_WR,
                period,
            )
            for dev in cached_scan_devs
        ),
    )
    data: List[AbsMetricValues] = []
    for dev in cached_scan_devs:
        index_read = cached_scan_devs.index(dev)
        index_write = len(cached_scan_devs) + cached_scan_devs.index(dev)
        (mem_bw_rd, mem_bw_wr, mem_bw_total) = count_bw(
            result[index_read], result[index_write]
        )
        v = PMONMetricValues(
            meta=MetricMetaData(
                tool=METRICS_PMON_MEMORY_BW,
                creation_timestamp=datetime.utcnow(),
                hostname=get_unique_host_id(),
            ),
            metrics=PMONBWValues(
                node_name=dev.path,
                mem_bw_rd=mem_bw_rd,
                mem_bw_wr=mem_bw_wr,
                mem_bw_total=mem_bw_total,
                period=period,
            ),
        )
        data.append(v)
    out.write_metric(data)


async def read_pcicfg(out: AbsDataProcessor, args: List[str]) -> None:
    """
    read_pcicfg - Return dump from PCICFG space memory

    Params:
        args[0] - all_devs: "0" only limted number of devices
                            "1" all Intel devices
        args[1] - all_regs: "0" limited number of registers
                            "1" whole 4kb memor of device PCICFG space
    """
    if len(args) < 2:
        logger.error(
            'Missing params, usage: read_pcicfg all_devs all_regs\n\ti.e read_pcicfg "0" "0"'
        )
        return None

    if int(args[0]):
        deviceids = []
    else:
        deviceids = [
            getattr(skylake_registers.Devices, dev)
            for dev in dir(skylake_registers.Devices)
            if not dev.startswith("__")
        ]

    if int(args[1]):
        all_registers = pcicfg_registers.Registers
    else:
        all_registers = skylake_registers.Registers  # type: ignore

    registers = [
        getattr(all_registers, reg)
        for reg in dir(all_registers)
        if not reg.startswith("__")
    ]

    pmon_devices: List[PMONDevicesWithRegisters] = []
    for dev in pmon.scan(deviceids=deviceids, vendorids=PCI_INTEL_VENDORID):
        registers_values: Dict[str, int] = {}
        for reg in registers:
            reg_value = pmon[dev.path].reg(reg).get()
            reg_name = str(reg)[len("Registers.") :]
            reg_name = reg_name if reg_name.startswith("pmon_") else "pmon_" + reg_name
            registers_values[reg_name] = reg_value

        pmon_devices.append(
            PMONDevicesWithRegisters(
                path=dev.path,
                seg=dev.seg,
                bus=dev.bus,
                dev=dev.dev,
                func=dev.func,
                regs=registers_values,
            )
        )

    data = PMONMetricValues(
        meta=MetricMetaData(
            tool=METRICS_PMON_PCICFG,
            creation_timestamp=datetime.utcnow(),
            hostname=get_unique_host_id(),
        ),
        metrics=PMONPCICFGValues(devices=pmon_devices),
    )
    out.write_metric([data])


async def read_hwmon_temp(out: AbsDataProcessor, args: List[str]) -> None:
    """
    read_hwmon_temp - Return all HWMON sensors temperature meausrements
    Params: none
    """
    data: List[AbsMetricValues] = []
    for temp in hwmon.get_temperatures():
        v = PMONMetricValues(
            meta=MetricMetaData(
                tool=METRICS_PMON_HWMON_TEMP,
                creation_timestamp=datetime.utcnow(),
                hostname=get_unique_host_id(),
            ),
            metrics=HWMONTempValues(
                socket=temp.socket,
                sensor=temp.sensor,
                socket_sensor=temp.socket * 1024 + temp.sensor,
                input=temp.input,
                max=temp.max,
                crit=temp.crit,
                label=temp.label,
            ),
        )
        data.append(v)
    out.write_metric(data)


async def read_correrrcnt(out: AbsDataProcessor, args: List[str]) -> None:
    """
    read_correrrcnt - Return Corrected Error counters, threshould and status
    Params:
        args - did numbers for deviceid filtering during scan
    """
    deviceids: List[int] = []
    for arg in args:
        deviceids.append(int(arg, base=16))

    data: List[AbsMetricValues] = []
    for dev in pmon.scan(deviceids=deviceids, vendorids=PCI_INTEL_VENDORID):
        # for dev in scan_and_cache_correrr_imc():
        data.append(
            PMONMetricValues(
                meta=MetricMetaData(
                    tool=METRICS_PMON_CORRERRCNT,
                    creation_timestamp=datetime.utcnow(),
                    hostname=get_unique_host_id(),
                ),
                metrics=PMONCorrerrcntValues(
                    node_name=dev.path,
                    correrrcnt_0=pmon[dev.path].reg(Registers.correrrcnt_0).get(),
                    correrrcnt_1=pmon[dev.path].reg(Registers.correrrcnt_1).get(),
                    correrrcnt_2=pmon[dev.path].reg(Registers.correrrcnt_2).get(),
                    correrrcnt_3=pmon[dev.path].reg(Registers.correrrcnt_3).get(),
                    correrrthrshld_0=pmon[dev.path]
                    .reg(Registers.correrrthrshld_0)
                    .get(),
                    correrrthrshld_1=pmon[dev.path]
                    .reg(Registers.correrrthrshld_1)
                    .get(),
                    correrrthrshld_2=pmon[dev.path]
                    .reg(Registers.correrrthrshld_2)
                    .get(),
                    correrrthrshld_3=pmon[dev.path]
                    .reg(Registers.correrrthrshld_3)
                    .get(),
                    correrrorstatus=pmon[dev.path].reg(Registers.correrrorstatus).get(),
                ),
            )
        )
    out.write_metric(data)


async def read_dimm_temp(out: AbsDataProcessor, args: List[str]) -> None:
    """
    read_dimm_temp - Return the thermal status of the memory
    Params:
        args - did numbers for deviceid filtering during scan
    """
    deviceids: List[int] = []
    for arg in args:
        deviceids.append(int(arg, base=16))

    data: List[AbsMetricValues] = []
    for dev in pmon.scan(deviceids=deviceids, vendorids=PCI_INTEL_VENDORID):
        temp = pmon[dev.path].reg(Registers.memtrmltemprep).get()
        channel0_max_temp = get_bitfield(temp, 0, 7)
        channel1_max_temp = get_bitfield(temp, 8, 15)
        channel2_max_temp = get_bitfield(temp, 16, 23)
        channel3_max_temp = get_bitfield(temp, 24, 31)
        data.append(
            PMONMetricValues(
                meta=MetricMetaData(
                    tool=METRICS_PMON_DIMM_TEMP,
                    creation_timestamp=datetime.utcnow(),
                    hostname=get_unique_host_id(),
                ),
                metrics=PMONTRMLMaxTempValues(
                    node_name=dev.path,
                    channel0_max_temp=channel0_max_temp,
                    channel1_max_temp=channel1_max_temp,
                    channel2_max_temp=channel2_max_temp,
                    channel3_max_temp=channel3_max_temp,
                ),
            )
        )
    out.write_metric(data)


def pmu_utils_init() -> None:
    """pmu_utils_init() - function register NativeCallMap call functions"""
    NativeCallMap.register("scrubaddress", read_scrubaddress)  # type: ignore
    NativeCallMap.register("pmoncntr", read_pmoncntr)  # type: ignore
    NativeCallMap.register("read_bw", read_bw)  # type: ignore
    NativeCallMap.register("pcicfg_dump", read_pcicfg)  # type: ignore
    NativeCallMap.register("read_hwmon_temp", read_hwmon_temp)  # type: ignore
    NativeCallMap.register("read_correrrcnt", read_correrrcnt)  # type: ignore
    NativeCallMap.register("read_dimm_temp", read_dimm_temp)  # type: ignore
