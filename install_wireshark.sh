#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mkdir -p installation-logs
log="installation-logs/wireshark-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$log") 2>&1
trap 'echo "INSTALL_FAILED: see installation log"' ERR
test "$(id -u)" -eq 0
echo 'Checking Ubuntu repository DNS...'
getent ahostsv4 th.archive.ubuntu.com
getent ahostsv4 security.ubuntu.com
apt-get update -o Acquire::Retries=3
# Offline PCAP analysis needs no non-root packet-capture privileges.
DEBIAN_FRONTEND=noninteractive apt-get install -y wireshark -o Acquire::Retries=3
/usr/bin/wireshark --version
echo 'INSTALL_COMPLETE: Wireshark is installed. Launch the GUI as the normal user.'

