"""
HWMON kernelspace reader was based on unified sysfs interface
https://www.kernel.org/doc/Documentation/hwmon/sysfs-interface
"""
import os
from dataclasses import dataclass
from typing import List

from libs.logger import pmon_logger as logger


@dataclass
class HWMONTempDevice:
    socket: int
    sensor: int
    input: float
    max: float
    crit: float
    label: str


class HWMON:

    PCI_DEVS: str = "/sys/class/hwmon"
    PCI_PATH: str = PCI_DEVS + "/hwmon%d/temp%d_%s"

    def get_temperatures(self) -> List[HWMONTempDevice]:
        """
        Method: get_temperatures()
        Description: Return all Sockets
        """
        devlist: List[HWMONTempDevice] = []
        if not os.path.isdir(HWMON.PCI_DEVS):
            logger.error(
                f"Problem with using Linux kernel, system directory {HWMON.PCI_DEVS} desn't exist."
            )
            return devlist
        for socket_path in sorted(os.listdir(HWMON.PCI_DEVS)):
            socket = int(socket_path[len("hwmon") :])
            for sensor in range(1, 64):
                if not os.path.isfile(HWMON.PCI_PATH % (socket, sensor, "input")):
                    continue

                with open(HWMON.PCI_PATH % (socket, sensor, "input"), "r") as f:
                    input = int(f.readline()) / 1000
                with open(HWMON.PCI_PATH % (socket, sensor, "max"), "r") as f:
                    max = int(f.readline()) / 1000
                with open(HWMON.PCI_PATH % (socket, sensor, "crit"), "r") as f:
                    crit = int(f.readline()) / 1000
                with open(HWMON.PCI_PATH % (socket, sensor, "label"), "r") as f:
                    label = str(f.readline().strip())

                logger.debug(
                    "[GET] socket_path : %s , socket: %d, sensor: %d, input: %d, max: %d, crit: %d, label: '%s'"
                    % (
                        HWMON.PCI_PATH % (socket, sensor, "*"),
                        socket,
                        sensor,
                        input,
                        max,
                        crit,
                        label,
                    )
                )
                devlist.append(
                    HWMONTempDevice(
                        socket=socket,
                        sensor=sensor,
                        input=input,
                        max=max,
                        crit=crit,
                        label=label,
                    )
                )
        return devlist
