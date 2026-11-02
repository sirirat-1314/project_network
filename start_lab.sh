#!/usr/bin/env bash
# Run this from Ubuntu: sudo bash /home/sirirat/Project_Network/G18_codex/start_lab.sh
set -Eeuo pipefail
export LC_ALL=C
umask 022
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [ "$(id -u)" -ne 0 ]; then
    echo 'Please run with sudo; Mininet needs Linux network administration privileges.'
    exit 1
fi
mkdir -p results
log="results/launch-$(date +%Y%m%d-%H%M%S)-$$.log"
exec > >(tee -a "$log") 2>&1
trap 'echo "FAILED at line $LINENO. Read the log shown above; no complete result is claimed."' ERR
echo "Launch log: $PWD/$log"
echo '1. Check and install the missing Scapy package.'
if ! /usr/bin/python3 -c 'import scapy' >/dev/null 2>&1; then
    apt-get update
    apt-get install -y --no-install-recommends python3-scapy
fi
echo '2. Check Python dependencies and Open vSwitch.'
/usr/bin/python3 -c 'import mininet, scapy; print("Mininet and Scapy imports OK")'
if ! systemctl is-active --quiet openvswitch-switch; then
    systemctl start openvswitch-switch
fi
ovs-vsctl show
echo '3. Run baseline, Linux TBF, and Python Leaky Bucket experiments.'
/usr/bin/python3 -u run_experiments.py
echo 'DONE: captures, sender logs, qdisc statistics and measured metrics are in results/.'

