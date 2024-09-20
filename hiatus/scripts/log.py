from logging import config
import os

log_config = {
    "version":1,
    "root":{
        "handlers" : ["console", "file", "file_debug"],
        "level": "DEBUG"
    },
    "handlers":{
        "console":{
            "formatter": "std_out",
            "class": "logging.StreamHandler",
            "level": "INFO"
        },
        "file":{
            "formatter":"std_out",
            "class":"logging.FileHandler",
            "level":"INFO",
            "filename":"hiatus.log"
        },
        "file_debug":{
            "formatter":"std_out",
            "class":"logging.FileHandler",
            "level":"DEBUG",
            "filename":"hiatus_debug.log"
        }
    },
    "formatters":{
        "std_out": {
            "format": "%(asctime)s : %(levelname)s : %(module)s : %(message)s",
            "datefmt":"%d-%m-%Y %I:%M:%S"
        }
    },
}

# Récupère le chemin vers le fichier de logs du chantier
hiatus_root = os.path.dirname(os.path.dirname(__file__))
workspace_path = os.path.join(hiatus_root, "workspace.txt")
with open (workspace_path, "r") as f:
    path = f.readline().strip()
    log_config["handlers"]["file"]["filename"] = os.path.join(hiatus_root, path, "hiatus.log")
    log_config["handlers"]["file_debug"]["filename"] = os.path.join(hiatus_root, path, "hiatus_debug.log")

config.dictConfig(log_config)
