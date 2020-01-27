#!/bin/bash

STARTING_PWD=$(pwd)
INSTALL_LOCATION=${1-${STARTING_PWD}}
CURA_VERSION=${2-4.4.1}

BUILD_DIR=$(mktemp -d)
CURA_ZIP_PATH=${BUILD_DIR}"/"cura.zip
CURA_DATA_PATH=${BUILD_DIR}"/Cura-"${CURA_VERSION}


echo ${CURA_VERSION}
echo ${INSTALL_LOCATION}
wget -O ${CURA_ZIP_PATH} "https://github.com/Ultimaker/Cura/archive/${CURA_VERSION}.zip"
unzip ${CURA_ZIP_PATH} -d ${BUILD_DIR}
cp -rf ${CURA_DATA_PATH}"/resources/"* ${INSTALL_LOCATION}


\rm -rf ${BUILD_DIR}
