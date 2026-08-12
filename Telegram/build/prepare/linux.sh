#!/bin/bash

set -e
FullExecPath=$PWD
pushd `dirname $0` > /dev/null
FullScriptPath=`pwd`
popd > /dev/null

eval "$(python3 "$FullScriptPath/../build_target.py" linux-environment "$@")"
export BUILD_TARGET BUILD_MODE BUILD_KEY QT_MAJOR QT_VERSION

cd $FullScriptPath/../docker/centos_env
poetry install
poetry run gen_dockerfile | DOCKER_BUILDKIT=1 docker build -t tdesktop:centos_env -
cd $FullExecPath
