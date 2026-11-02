"""Linux only: sudo python3 run_experiments.py. Preserve each run separately."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from datetime import datetime


def checked(host, argv, timeout=60):
    process = host.popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise
    output = output.decode(errors="replace")
    if process.returncode:
        raise RuntimeError(f"{host.name}: {argv}: {output}")
    return output


def stop(process, sig=signal.SIGTERM):
    if process and process.poll() is None:
        process.send_signal(sig)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise RuntimeError("Process did not stop cleanly; inspect capture before using results")


def main():
    if sys.platform != "linux" or os.geteuid() != 0:
        raise SystemExit("Run inside Ubuntu: sudo python3 run_experiments.py")
    from mininet.net import Mininet
    from mininet.node import OVSSwitch
    from mininet.link import TCLink
    from generate_group_params import generate_group_params

    base = Path(__file__).resolve().parent
    os.chdir(base)
    result = base / "results" / datetime.now().strftime("run-%Y%m%d-%H%M%S-%f")
    result.mkdir(parents=True)
    params = generate_group_params()
    (result / "group_params.json").write_text(json.dumps(params, indent=2))
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    sink = capture = None
    try:
        h1 = net.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h2 = net.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
        s1 = net.addSwitch("s1", failMode="standalone")
        net.addLink(h1, s1, bw=params["bandwidth_mbps"])
        net.addLink(h2, s1, bw=params["bandwidth_mbps"])
        net.start()
        net.staticArp()
        print("STEP 1: topology started; testing h1 -> h2", flush=True)
        (result / "ping.txt").write_text(checked(h1, ["ping", "-c", "3", "10.0.0.2"]))
        with (result / "sink.log").open("w") as sinklog:
            sink = h2.popen([sys.executable, str(base / "udp_sink.py")], stdout=sinklog, stderr=sinklog)
            time.sleep(0.5)
            if sink.poll() is not None:
                raise RuntimeError("UDP sink failed; inspect sink.log")
            for name, mode in [("before_shaping", "direct"), ("after_tbf", "direct"), ("after_shaping", "leaky")]:
                print(f"STEP 2: capturing {name} ({mode})", flush=True)
                qdisc = ["tc", "qdisc", "replace", "dev", "h1-eth0", "root"]
                qdisc += (["tbf", "rate", "1024kbit", "burst", "2000", "latency", "400ms"]
                          if name == "after_tbf" else ["pfifo", "limit", "1000"])
                checked(h1, qdisc)
                pcap = result / (name + ".pcap")
                sender = result / (name + "_sender.json")
                caplog = result / (name + "_capture.log")
                with caplog.open("w") as log:
                    capture = h2.popen(["tcpdump", "-Z", "root", "-i", "h2-eth0", "-n", "-s", "0", "-U", "-w", str(pcap),
                                        "udp dst port 5000 and src host 10.0.0.1"], stdout=log, stderr=log)
                    for _ in range(50):
                        if capture.poll() is not None:
                            raise RuntimeError(caplog.read_text())
                        if "listening on" in caplog.read_text():
                            break
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("Capture did not report ready")
                    output = checked(h1, [sys.executable, str(base / "generate_burst_traffic.py"), "--mode", mode, "--log", str(sender)])
                    (result / (name + "_sender.log")).write_text(output)
                    time.sleep(6)
                    for _ in range(20):
                        q1 = checked(h1, ["tc", "-s", "qdisc", "show", "dev", "h1-eth0"])
                        q2 = checked(s1, ["tc", "-s", "qdisc", "show", "dev", "s1-eth2"])
                        backlogs = re.findall(r"backlog\s+(\S+)\s+(\d+)p", q1 + q2)
                        if backlogs and all(int(packets) == 0 for _, packets in backlogs):
                            break
                        time.sleep(0.5)
                    else:
                        raise RuntimeError("Network backlog did not drain; results incomplete")
                    (result / (name + "_qdisc.txt")).write_text(q1 + "\nSWITCH OUTPUT:\n" + q2)
                    stop(capture, signal.SIGINT)
                    capture = None
                if not re.search(r"\b0 packets dropped by kernel\b", caplog.read_text()):
                    raise RuntimeError("Capture drops or missing capture summary; do not use as network loss")
                subprocess.run([sys.executable, str(base / "analyze_pcap.py"), str(pcap), "--log", str(sender),
                                "--output", str(result / (name + "_metrics.json"))], check=True)
        print(f"COMPLETE: {result}", flush=True)
    finally:
        try:
            stop(capture, signal.SIGINT)
        finally:
            try:
                stop(sink)
            finally:
                net.stop()


if __name__ == "__main__":
    main()

