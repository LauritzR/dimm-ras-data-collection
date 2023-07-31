import logging

logging.basicConfig(
    format="[%(asctime)s][%(threadName)s][%(levelname).1s][%(module)s::%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d-%H:%M:%S",
    level=logging.DEBUG,
)
logger = logging.getLogger("vme")
pmon_logger = logging.getLogger("vme.pmon")
