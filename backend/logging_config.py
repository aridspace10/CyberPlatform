import logging
import json


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "level": record.levelname,
            "message": record.getMessage(),
            "time": self.formatTime(record),
        }
        if hasattr(record, "extra_data"):
            log_record.update(record.extra_data)
        return json.dumps(log_record)


def setup_logging():
    logger = logging.getLogger("cyber")

    if logger.hasHandlers():  # جلوگیری duplicate logs
        return logger

    handler = logging.FileHandler("system.log")
    handler.setFormatter(JsonFormatter())

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
