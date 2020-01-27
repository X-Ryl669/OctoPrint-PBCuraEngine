#!/bin/bash

BASE_DIR=$(echo ~)
CURA_VERSION=${1}


cd ${BASE_DIR}
git clone https://github.com/Ultimaker/CuraEngine.git
cd ${BASE_DIR}
git clone https://github.com/Ultimaker/libArcus.git

apt install libprotobuf17 libprotobuf-dev libprotoc-dev python3-dev python3-sip-dev cmake build-essential protobuf-compiler protobuf-c-compiler


# wget https://github.com/protocolbuffers/protobuf/releases/download/v3.11.2/protobuf-cpp-3.11.2.tar.gz
# extract ./protobuf-cpp-3.11.2.tar.gz
# cd
# ./autogen.sh
# ./configure
# make
# make install


cd ${BASE_DIR}/libArcus
git pull origin ${CURA_VERSION}
git checkout ${CURA_VERSION}
sed -i 's/\"Build \" ON/\"Build \" OFF/g' ./CMakeLists.txt
sed -i 's/\"Build the example programs\" ON/\"Build the example programs\" OFF/g' ./CMakeLists.txt
mkdir build && cd build
chmod 777 ../build
cmake ../
make
su -l -c'cd '$(echo ${BASE_DIR}/libArcus/build)';make install'

cd ${BASE_DIR}/CuraEngine
git pull origin ${CURA_VERSION}
git checkout ${CURA_VERSION}
mkdir build && cd build
cmake ../
make
