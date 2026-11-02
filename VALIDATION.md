# Validation status

Checked locally on Windows, 2026-09-16:

- All Python source files compile.
- G18 parameter values match the generator transcribed from the assignment.
- Synthetic receiver rows verify unique/duplicate counts, loss and 10 ms throughput calculations.
- Bounded Leaky Bucket verifies FIFO ordering, overflow drop accounting and drain before close.
- Pacing check verifies minimum spacing with a high-resolution monotonic performance clock.

Synthetic checks are software checks, not experimental results for the report.

Not yet verified: Linux Mininet topology, Open vSwitch forwarding, tc configuration, Scapy transmission, actual pcap collection and Wireshark plots. Run these inside the user's Ubuntu VMware VM following README_TH.md.

No measured throughput, network delay or packet loss is claimed in this delivery.

