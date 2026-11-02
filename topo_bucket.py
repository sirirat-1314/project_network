"""Run on Linux: sudo python3 topo_bucket.py"""
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSSwitch
from generate_group_params import generate_group_params


def main():
    p = generate_group_params()
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    try:
        h1 = net.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h2 = net.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
        s1 = net.addSwitch("s1", failMode="standalone")
        net.addLink(h1, s1, bw=p["bandwidth_mbps"])
        net.addLink(h2, s1, bw=p["bandwidth_mbps"])
        net.start()
        net.staticArp()
        print("G18: h1 (10.0.0.1) -- s1 -- h2 (10.0.0.2), 2 Mbps links")
        print("Run h1 ping -c 3 h2 before experiments.")
        CLI(net)
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    main()

