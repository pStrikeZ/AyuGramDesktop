#!/usr/bin/env python3
from os import environ
from os.path import dirname, join
import sys
from jinja2 import Environment, FileSystemLoader

sys.path.append(join(dirname(__file__), '../..'))
from qt_versions import version_for_major

def checkEnv(envName, defaultValue):
    if isinstance(defaultValue, bool):
        return bool(len(environ[envName])) if envName in environ else defaultValue
    return environ[envName] if envName in environ else defaultValue

def main():
    qtMajor = int(checkEnv("QT_MAJOR", 6))
    print(Environment(loader=FileSystemLoader(dirname(__file__))).get_template("Dockerfile").render(
        DEBUG=checkEnv("DEBUG", True),
        MINSIZE=checkEnv("MINSIZE", False),
        LTO=checkEnv("LTO", True),
        ASAN=checkEnv("ASAN", False),
        JOBS=checkEnv("JOBS", ""),
        QT_VERSION=checkEnv("QT_VERSION", version_for_major(qtMajor)),
    ))

if __name__ == '__main__':
    main()
