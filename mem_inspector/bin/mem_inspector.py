#!/usr/bin/env python3
import asyncio
from dataclasses import dataclass
from typing import Final, List

from libs.data_processors import AbsDataProcessor
from libs.native import NativeCallMap
from libs.pmon.pmon_native_helpers import pmu_utils_init
from libs.logger import pmon_logger as logger
from libs.metric_values import AbsMetricValues
from libs.pmon.pmon_metric_values import (
    HWMONTempValues,
    PMONBWValues,
    PMONCorrerrcntValues,
    PMONTRMLMaxTempValues,
)


@dataclass
class Command:
    name: str
    cmd: List[str]
    delay: float


class Filter:
    data = {}

    def process(self, data, unique):
        if unique in self.data and self.data[unique] == data:
            logger.debug(f"duplicate {unique} = {data}")
            return False
        else:
            logger.debug(f"non duplicate {unique} = {data}")
            self.data[unique] = data
            return True


class MetricsReader:
    class Out(AbsDataProcessor):
        filter = Filter()

        @staticmethod
        def csv_output(data: AbsMetricValues, order_list: List[str], key: str) -> None:
            q: Final[str] = '"'
            sep: Final[str] = ";"

            csv_line: str = ""
            meta = data.meta
            metrics = data.metrics
            unique: Dict = {}
            unique_key = meta.tool + "_#_" + str(getattr(metrics, key))
            for field in ["creation_timestamp", "tool", "hostname"] + order_list:
                if field in order_list:
                    csv_line += f"{q}{getattr(metrics, field)}{q}{sep}"
                    unique[field] = getattr(metrics, field)
                else:
                    csv_line += f"{q}{getattr(meta, field)}{q}{sep}"

            if MetricsReader.Out.filter.process(unique, unique_key):
                print(csv_line)

        @staticmethod
        def write_metric(metrics_list: List[AbsMetricValues]) -> None:
            for data in metrics_list:
                logger.debug(f"data = {data}")

                if type(data.metrics) == PMONBWValues:
                    MetricsReader.Out.csv_output(
                        data,
                        ["node_name", "mem_bw_rd", "mem_bw_wr", "mem_bw_total"],
                        "node_name",
                    )
                elif type(data.metrics) == HWMONTempValues:
                    MetricsReader.Out.csv_output(
                        data,
                        ["label", "socket_sensor", "input", "crit", "max"],
                        "socket_sensor",
                    )
                elif type(data.metrics) == PMONCorrerrcntValues:
                    MetricsReader.Out.csv_output(
                        data,
                        [
                            "node_name",
                            "correrrcnt_0",
                            "correrrcnt_1",
                            "correrrcnt_2",
                            "correrrcnt_3",
                            "correrrthrshld_0",
                            "correrrthrshld_1",
                            "correrrthrshld_2",
                            "correrrthrshld_3",
                            "correrrorstatus",
                        ],
                        "node_name",
                    )
                elif type(data.metrics) == PMONTRMLMaxTempValues:
                    MetricsReader.Out.csv_output(
                        data,
                        [
                            "node_name",
                            "channel0_max_temp",
                            "channel1_max_temp",
                            "channel2_max_temp",
                            "channel3_max_temp",
                        ],
                        "node_name",
                    )

    async def exec_task(self, cmd: Command) -> None:
        if cmd.delay is not None and cmd.delay != 0:
            await asyncio.sleep(cmd.delay)
        logger.debug(f"EXEC TASK {cmd.name} sleep={cmd.delay}")
        await NativeCallMap.cmd(cmd.name, cmd.cmd, MetricsReader.Out())

    async def run(self, cmds: List[Command]) -> None:
        self.pending_tasks = {
            asyncio.create_task(self.exec_task(cmd), name=cmd.name) for cmd in cmds
        }
        while True:
            done, self.pending_tasks = await asyncio.wait(
                self.pending_tasks, return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                name = task.get_name()
                logger.debug(f"COMPLETED TASK: {name}")
                for cmd in cmds:
                    if cmd.name == name:
                        self.pending_tasks.add(
                            asyncio.create_task(self.exec_task(cmd), name=cmd.name)
                        )


async def main() -> None:
    metrics = MetricsReader()
    cmds = [
        # Command("read_bw", ["read_bw", "1"], 15),
        Command("read_hwmon_temp", ["read_hwmon_temp"], 60),
        Command(
            "read_correrrcnt",
            [
                "read_correrrcnt",
                "0x6fb2",
                "0x6fb3",
                "0x6fb6",
                "0x6fb7",
                "0x6fd2",
                "0x6fd3",
                "0x6fd6",
                "0x6fd7",
            ],
            60,
        ),
        #        Command("read_dimm_temp", ["read_dimm_temp", "0x6fb0", "0x6fd0"], 15),
    ]
    await metrics.run(cmds)


if __name__ == "__main__":
    pmu_utils_init()
    logger.setLevel(100)
    asyncio.run(main())
