"""Measure receiver frames in aligned 10 ms bins. Does not invent results."""
import argparse
import json
import math
import statistics
import struct
from pathlib import Path


def calculate_metrics(rows, offered, bin_seconds=0.01):
    if not rows:
        raise ValueError("No matching G18 UDP packets; check capture and generator")
    rows = sorted(rows)
    if offered <= 0 or any(seq < 0 or seq >= offered for _, _, seq in rows):
        raise ValueError("Packet sequence or offered count is inconsistent")
    origin = math.floor(rows[0][0] / bin_seconds) * bin_seconds
    bins = {}
    for timestamp, size, _ in rows:
        index = max(0, math.floor((timestamp - origin) / bin_seconds + 1e-6))
        bins[index] = bins.get(index, 0) + size * 8
    window = (max(bins) + 1) * bin_seconds
    gaps = [(b[0] - a[0]) * 1000 for a, b in zip(rows, rows[1:])]
    unique = len({seq for _, _, seq in rows})
    return {
        "captured_packets": len(rows), "unique_received": unique,
        "duplicates": len(rows) - unique, "offered_packets": offered,
        "packet_loss_percent": 100 * (offered - unique) / offered,
        "peak_throughput_mbps": max(bins.values()) / bin_seconds / 1e6,
        "average_throughput_mbps": sum(bins.values()) / window / 1e6,
        "measurement_window_seconds": window,
        "max_interarrival_ms": max(gaps) if gaps else None,
        "jitter_interarrival_population_stddev_ms": statistics.pstdev(gaps) if gaps else None,
        "accounting": "captured Ethernet frame bytes, no FCS/preamble/IFG; 10 ms epoch-aligned bins",
        "delay_note": "Inter-arrival timing at h2, NOT one-way latency",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pcap")
    parser.add_argument("--log", required=True, help="Generator JSON from the SAME run")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    from scapy.all import IP, UDP, PcapReader
    log = json.loads(Path(args.log).read_text(encoding="utf-8"))
    rows = []
    with PcapReader(args.pcap) as packets:
        for pkt in packets:
            if IP not in pkt or UDP not in pkt:
                continue
            if pkt[IP].src != "10.0.0.1" or pkt[IP].dst != "10.0.0.2" or pkt[UDP].dport != 5000:
                continue
            payload = bytes(pkt[UDP].payload)
            if len(payload) >= 8 and payload[:4] == b"G18!":
                rows.append((float(pkt.time), len(bytes(pkt)), struct.unpack("!I", payload[4:8])[0]))
    result = calculate_metrics(rows, log["offered"])
    result["generator_queue_dropped"] = log["queue_dropped"]
    result["kernel_submit_dropped"] = log.get("kernel_submit_dropped", 0)
    result["warning"] = "Loss is valid only after full drain and with zero tcpdump capture drops. Each run uses its own occupied-bin window."
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

