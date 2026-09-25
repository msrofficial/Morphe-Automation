#!/usr/bin/env bash
set -e
# Termux quick start
pkg update -y && pkg install -y git python openjdk-21 zip unzip
if [ ! -d Morphe-Automation ]; then git clone https://github.com/msrofficial/Morphe-Automation; fi
cd Morphe-Automation
pip install -r requirements.txt
./build.sh
