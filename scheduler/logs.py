import logging
from redbot.core.data_manager import core_data_path


def get_logger(name: str):

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: %(message)s",
        datefmt="[%d/%m/%Y %H:%M]",
    )

    logfile_path = core_data_path() / f"{name}.log"
    fhandler = logging.handlers.RotatingFileHandler(  # type: ignore
        filename=str(logfile_path),
        encoding="utf-8",
        mode="a",
        maxBytes=10 ** 7,
        backupCount=5,
    )
    fhandler.setFormatter(fmt)
    logger.addHandler(fhandler)

    return logger
