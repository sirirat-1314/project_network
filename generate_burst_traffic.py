"""Send only inside the assignment's Mininet h1 namespace."""
import argparse
import errno
import json
import math
import struct
import time
from pathlib import Path
from generate_group_params import generate_group_params
from leaky_bucket_shaper import LeakyBucket


def submit_frame(sock, frame, counters):
    """A qdisc rejection is an observed loss, not a reason to retry the input."""
    try:
        sock.send(frame)
    except OSError as exc:
        if exc.errno != errno.ENOBUFS:
            raise
        counters["kernel_submit_dropped"] += 1
    else:
        counters["sent"] += 1


def main(default_mode="direct"):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["direct", "leaky"], default=default_mode)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()
    from scapy.all import Ether, IP, UDP, Raw, conf, get_if_addr

    if get_if_addr("h1-eth0") != "10.0.0.1":
        raise RuntimeError("Run this script from Mininet h1 only")
    p = generate_group_params()
    # The PDF uses packet_size_bytes as Raw payload size, not whole IP size.
    packets = []
    for seq in range(10 * p["burst_size_packets"]):
        payload = b"G18!" + struct.pack("!I", seq) + b"X" * (p["packet_size_bytes"] - 8)
        packets.append(bytes(Ether(src="00:00:00:00:00:01", dst="00:00:00:00:00:02") /
                       IP(src="10.0.0.1", dst="10.0.0.2") /
                       UDP(sport=40000, dport=5000) / Raw(payload)))
    frame_bytes = len(packets[0])
    rate_bps = p["token_rate_kbit"] * 1000
    drain_pps = rate_bps / (frame_bytes * 8)
    # Queue capacity is a design choice derived from the 400 ms wait budget.
    # It is distinct from the token pool size (16 kbit).
    capacity = max(1, math.floor(drain_pps * p["latency_ms"] / 1000))
    sock = conf.L2socket(iface="h1-eth0")
    bucket = None
    counters = {"sent": 0, "kernel_submit_dropped": 0}
    output = lambda frame: submit_frame(sock, frame, counters)
    burst_times = []
    started = time.time()
    try:
        if args.mode == "leaky":
            bucket = LeakyBucket(drain_pps, capacity, output)
        for burst in range(10):
            burst_times.append(time.time())
            lo = burst * p["burst_size_packets"]
            for pkt in packets[lo:lo + p["burst_size_packets"]]:
                if bucket:
                    bucket.add_packet(pkt)
                else:
                    output(pkt)
            print(f"Burst {burst + 1}/10: {p['burst_size_packets']} offered", flush=True)
            # Same semantics as the PDF: pause AFTER sending/enqueueing a burst.
            time.sleep(p["burst_interval_ms"] / 1000)
    finally:
        try:
            if bucket:
                bucket.close()
        finally:
            sock.close()
    result = dict(parameters=p, mode=args.mode, offered=len(packets),
                  sent=counters["sent"],
                  kernel_submit_dropped=counters["kernel_submit_dropped"],
                  queue_dropped=bucket.dropped if bucket else 0,
                  payload_bytes=p["packet_size_bytes"], frame_bytes=frame_bytes,
                  drain_pps=drain_pps if bucket else None,
                  queue_capacity_packets=capacity if bucket else None,
                  started_epoch=started, finished_epoch=time.time(),
                  burst_start_epochs=burst_times)
    if result["offered"] != result["sent"] + result["queue_dropped"] + result["kernel_submit_dropped"]:
        raise RuntimeError("Packet accounting mismatch")
    Path(args.log).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

