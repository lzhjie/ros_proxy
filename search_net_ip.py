#!/usr/bin/python
import re
import sys


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python %s xx.xx.xx.xx/xx[:] file_name" % sys.argv[0])
    nets = sys.argv[1].split(":")
    with open(sys.argv[2]) as fp:
        ips = re.findall(r"(?:\d+[.]){3}\d+", fp.read())
    ip2bin = lambda ip,mask_len: "".join(map(lambda x:bin(x+256)[3:], map(int, ip.split("."))))[:int(mask_len)]
    ips_b = map(ip2bin, ips, [32]*len(ips))
    nets_b = map(ip2bin, *zip(*map(lambda x:x.split("/"), nets)))
    for j, net in enumerate(nets_b):
        for i, ip in enumerate(ips_b):
            if ip.startswith(net):
                print("%s %s" % (nets[j], ips[i]))
