from libs.hwmon.hwmon import HWMON
from libs.pmon.pmon import PMON, Devices, Registers, PMONDevice
from libs.pmon.pmon_driver_emulated import PMONEmulatedDriver
from libs.pmon.pmon_driver_linuxkernel import PMONLinuxKernelDriver
from libs.vme_constants import PCI_INTEL_VENDORID
from libs.logger import pmon_logger as logger
from functools import lru_cache
from typing import Dict, List
import time
import sys
import os

logger.setLevel(100)

if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
    pmon = PMON(PMONEmulatedDriver)
    dump_file_name = sys.argv[1]
    PMONEmulatedDriver.dump_file = dump_file_name
    PMONEmulatedDriver.dump_data = {}
    PMONEmulatedDriver.readdump()
else:
    pmon = PMON(PMONLinuxKernelDriver)

hwmon = HWMON()

@lru_cache
def scan_and_cache_correrr_imc() -> List[PMONDevice]:
    return pmon.scan(
        vendorids=PCI_INTEL_VENDORID,
        deviceids=[Devices.IMC0C0_1LMDP]
    )

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

def read_correrrcnt():
    for dev in scan_and_cache_correrr_imc:
        print(f"\n\t{dev}")
        correrrorstatus = pmon[dev.path].reg(Registers.correrrorstatus).get()
        correrrorstatus_bin = f"{correrrorstatus:032b}"
        correrrorstatus_bin = f"{correrrorstatus_bin[0:7]} {correrrorstatus_bin[8:10]} {correrrorstatus_bin[11:13]} {correrrorstatus_bin[14:21]} {correrrorstatus_bin[22:31]}"
        print(f"{Registers.correrrorstatus.name} [0x{Registers.correrrorstatus.value:02X}] = {correrrorstatus_bin}")

        for reg in range(0,4):
            correrrcnt = Registers[f"correrrcnt_{reg}"]
            correrrthrshld = Registers[f"correrrthrshld_{reg}"]
            correrrcnt_value = pmon[dev.path].reg(correrrcnt).get()
            correrrthrshld_value = pmon[dev.path].reg(correrrthrshld).get()

            correrrcnt_bin = f"{correrrcnt_value:032b}"
            correrrcnt_bin = f"{correrrcnt_bin[0:14]} {correrrcnt_bin[15]} {correrrcnt_bin[16:30]} {correrrcnt_bin[31]}"
            correrrthrshld_bin = f"{correrrthrshld_value:032b}"
            correrrthrshld_bin = f"{correrrthrshld_bin[0:14]} {correrrthrshld_bin[15]} {correrrthrshld_bin[16:30]} {correrrthrshld_bin[31]}"

            print(f"{correrrcnt.name} [0x{correrrcnt.value:02X}] = {correrrcnt_bin}\t"
                f"{correrrthrshld.name} [0x{correrrthrshld.value:02X}] = {correrrthrshld_bin}")


def read_sensors():
    for item in hwmon.get_temperatures():
        print(item)


async def main():
    while True:
        read_sensors()

if __name__ == "__main__":
    asyncio.run(main())
