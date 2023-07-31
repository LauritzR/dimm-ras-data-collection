import curses
import sys
import subprocess

from datetime import datetime

from libs.pmon.pmon import PMON, Devices, Events, Registers, Size  # noqa: E402
from libs.pmon.pmon_driver_vsi import PMONVSIDriver  # noqa: E402
from libs.pmon.pmon_driver_emulated import PMONEmulatedDriver
from libs.logger import logger

logger.setLevel(100)

old_cas_rd: {}
old_cas_wr: {}

pmon = PMON(PMONEmulatedDriver)
PMONEmulatedDriver.dump_file = "./tests/data/10.173.238.92.dump"
PMONEmulatedDriver.dump_data = {}
PMONEmulatedDriver.readdump()

# pmon = PMON({"driver": PMONVSIDriver})
nodes = []

def humanbytes(data: int) -> str:
    """Return the given bytes as a human friendly KB, MB, GB, or TB string."""
    b = float(data)
    kb = float(1024)
    mb = float(kb ** 2)  # 1,048,576
    gb = float(kb ** 3)  # 1,073,741,824
    tb = float(kb ** 4)  # 1,099,511,627,776

    if b < kb:
        return "{0} {1}                  ".format(int(b), "Byte/s" if 0 == b > 1 else "Bytes/s")
    elif kb <= b < mb:
        return "{0:.2f} KB/s        ".format(b / kb)
    elif mb <= b < gb:
        return "{0:.2f} MB/s        ".format(b / mb)
    elif gb <= b < tb:
        return "{0:.2f} GB/s        ".format(b / gb)
    elif tb <= b:
        return "{0:.2f} TB/s        ".format(b / tb)
    return ""


def init():
    global old_cas_rd, old_cas_wr, nodes
    nodes = []
    devs = pmon.scan(
        deviceids=[
            Devices.IMC0C0_1LMS,
            Devices.IMC0C1_1LMS,
            Devices.IMC0C2_1LMS,
            Devices.IMC1C0_1LMS,
            Devices.IMC1C1_1LMS,
            Devices.IMC1C2_1LMS,
        ]
    )
    for dev in devs:
        nodes.append(dev.path)


def reset_counters():
    global old_cas_rd, old_cas_wr, nodes
    old_cas_rd = {}
    old_cas_wr = {}
    for node in nodes:
        old_cas_rd[node] = 0
        old_cas_wr[node] = 0
        pmon[node].reg(Registers.pmoncntrcfg_2).set_event(Events.CAS_COUNT_RD)
        pmon[node].reg(Registers.pmoncntrcfg_3).set_event(Events.CAS_COUNT_WR)


def draw_menu(stdscr) -> None:  # type: ignore
    global old_cas_rd, old_cas_wr, nodes

    cols=2
    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
    stdscr.nodelay(1)
    k = None
    # Loop where k is the last character pressed

    while k != ord("q"):

        if k == ord("r"):
            reset_counters()
        elif k == ord("1"):
            app = ["/vmfs/volumes/61789a4a-6063db52-998d-248a07b5e986/code/zbigniew/demo2/stressapptest", "-s", "5", "-M", "256", "-m", "4", "-C", "4", "-v", "0"]
            subprocess.Popen(app, stdout=subprocess.PIPE)
        elif k == ord("2"):
            app = ["/vmfs/volumes/61789a4a-6063db52-998d-248a07b5e986/code/zbigniew/demo2/stressapptest", "-s", "5", "-M", "256", "-m", "8", "-C", "8", "-v", "0"]
            subprocess.Popen(app, stdout=subprocess.PIPE)
        elif k == ord("3"):
            app = ["/vmfs/volumes/61789a4a-6063db52-998d-248a07b5e986/code/zbigniew/demo2/stressapptest", "-s", "5", "-M", "128", "-m", "16", "-C", "16", "-v", "0"]
            subprocess.Popen(app, stdout=subprocess.PIPE)
        elif k == ord("4"):
            app = ["/vmfs/volumes/61789a4a-6063db52-998d-248a07b5e986/code/zbigniew/demo2/stressapptest", "-s", "5", "-M", "64", "-m", "24", "-C", "24", "-v", "0"]
            subprocess.Popen(app, stdout=subprocess.PIPE)
        elif k == ord("5"):
            app = ["/vmfs/volumes/61789a4a-6063db52-998d-248a07b5e986/code/zbigniew/demo2/stressapptest", "-s", "5", "-M", "32", "-m", "32", "-C", "32", "-v", "0"]
            subprocess.Popen(app, stdout=subprocess.PIPE)
        elif k == ord(" "):
            app = ["/vmfs/volumes/61789a4a-6063db52-998d-248a07b5e986/code/zbigniew/demo2/stressapptest", "-s", "5", "-M", "256", "-m", "32", "-W", "-v", "0"]
            subprocess.Popen(app, stdout=subprocess.PIPE)

        stdscr.addstr(
            0,
            0,
            "  [ {0} ]".format(datetime.now().strftime("%T")),
            curses.color_pair(1),
        )
        stdscr.addstr(0, 16*cols, "CAS_COUNT.RD", curses.color_pair(3))
        stdscr.addstr(0, 32*cols, "CAS_COUNT.WR", curses.color_pair(3))
        stdscr.addstr(0, 48*cols, "MEM_BW_RD", curses.color_pair(3))
        stdscr.addstr(0, 64*cols, "MEM_BW_WR", curses.color_pair(3))
        stdscr.addstr(0, 80*cols, "MEM_BW_TOTAL", curses.color_pair(3))

        for node in nodes:
            cas_count_rd = pmon[node].reg(Registers.pmoncntr_2).get(Size.COUNTER) - old_cas_rd[node]
            cas_count_wr = pmon[node].reg(Registers.pmoncntr_3).get(Size.COUNTER) - old_cas_wr[node]
            old_cas_rd[node] = cas_count_rd
            old_cas_wr[node] = cas_count_wr
            mem_bw_rd = cas_count_rd * 64
            mem_bw_wr = cas_count_wr * 64
            mem_bw_total = mem_bw_rd + mem_bw_wr

            row = nodes.index(node) + 1

            stdscr.addstr(row, 0, node, curses.color_pair(3))
            stdscr.addstr(row, 16*cols, humanbytes(cas_count_rd), curses.color_pair(3))
            stdscr.addstr(row, 32*cols, humanbytes(cas_count_wr), curses.color_pair(3))
            stdscr.addstr(row, 48*cols, humanbytes(mem_bw_rd), curses.color_pair(3))
            stdscr.addstr(row, 64*cols, humanbytes(mem_bw_wr), curses.color_pair(3))
            stdscr.addstr(row, 80*cols, humanbytes(mem_bw_total), curses.color_pair(3))

        stdscr.refresh()
        curses.napms(1000)

        k = stdscr.getch()


def main() -> None:
    init()
    reset_counters()
    curses.wrapper(draw_menu)


if __name__ == "__main__":
    main()
