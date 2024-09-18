from logging import config

log_config = {
    "version":1,
    "root":{
        "handlers" : ["console", "file"],
        "level": "DEBUG"
    },
    "handlers":{
        "console":{
            "formatter": "std_out",
            "class": "logging.StreamHandler",
            "level": "DEBUG"
        },
        "file":{
            "formatter":"std_out",
            "class":"logging.FileHandler",
            "level":"INFO",
            "filename":"hiatus.log"
        }
    },
    "formatters":{
        "std_out": {
            "format": "%(asctime)s : %(levelname)s : %(module)s : %(message)s",
            "datefmt":"%d-%m-%Y %I:%M:%S"
        }
    },
}

config.dictConfig(log_config)