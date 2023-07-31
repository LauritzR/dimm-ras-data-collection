from libs.pmon.pmon import PMON, Devices, Registers, Size
from libs.pmon.pmon_driver_linuxkernel import PMONLinuxKernelDriver
from libs.vme_constants import PCI_INTEL_VENDORID
from libs.logger import pmon_logger as logger
import sys
import os

logger.setLevel(100)
pmon = PMON(PMONLinuxKernelDriver)

print(pmon.read_msr(0,0x420))
