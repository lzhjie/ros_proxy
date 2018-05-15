# coding: utf-8
# Copyright (C) zhongjie luo <l.zhjie@qq.com>
from thirdparty.Options import Options, Option
from thirdparty.telnet import MyTelnet
import urlparse
import json
import time
import traceback
import re
import httplib
import socket


class RosProxy:
    def __init__(self, host, port, user, password):
        # 0 allow-address                              169.0.1.195
        self.__pattern_address_list = re.compile(r"\n\D*?(\d+)\s+([\w-]+)\s+([0-9.]+)")
        self._tel = MyTelnet(host, user, password, port=port, timeout=5)
        self._tel.change_path(["ip", "firewall", "address-list"])
        pass

    def get_address_list(self):
        """return {name:({ip:number}, "set(ip)")}"""
        result = self._tel.command("print without-paging", clear_buffer=True)
        list = self.__pattern_address_list.findall(result)
        result = {}
        for number, name, ip in list:
            ip_dict, ip_set = result.get("name", result.setdefault(name, ({}, set())))
            if ip in ip_dict:
                print("duplicated, remove")
                self.address_remove(number, name, ip)
                continue
            ip_dict[ip] = number
            ip_set.add(ip)
        return result

    def address_add(self, name, ip):
        print("add, name: %s, ip: %s" % (name, ip))
        self._tel.command(b"add list=%s address=%s" % (name, ip))

    def address_remove(self, number, name, ip):
        print("remove, number: %s, name: %s, ip: %s" % (number, name, ip))
        self._tel.command(b"remove number=%s" % (number))
        pass


class HttpClientKeepAlive:
    def __init__(self, uri, source_address):
        temp = urlparse.urlparse(uri)
        self._client = httplib.HTTPConnection(temp.hostname, temp.port, source_address=source_address)
        self._headers = {'Connection': 'keep-alive'}
        # print self.get("export.json")
        self._device = json.loads(self.get("device.json"))["name"].values()

    def get(self, method):
        try:
            self._client.request('GET', method, headers=self._headers)
        except socket.error:
            self._client.close()
            raise
        rsp = self._client.getresponse()
        return rsp.read()

    def get_ip_strategy(self):
        temp = json.loads(self.get("export.json"), encoding="unicode_escape")
        result = {i: set() for i in self._device}
        for ip, name in zip(temp["c_ip"].values(), temp["d_name"].values()):
            ip_set = result.get(name, result.setdefault(name, set()))
            ip_set.add(ip)
        return result

    def server_reset(self):
        self.get("reset")


def update_ip_strategy(ip_ros, ip_new, ros_adapter):
    print("%s update_ip_strategy" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
    for name, ip_set_n in ip_new.items():
        ip_dict, ip_set_o = ip_ros.get(name, ({}, set()))
        for ip in ip_set_n - ip_set_o:
            ros_adapter.address_add(name, ip)
        for ip in ip_set_o - ip_set_n:
            ros_adapter.address_remove(ip_dict[ip], name, ip)


def do_main():
    options = (
        Option("uri", "u", "http://127.0.0.1:8787",
               help=u"获取策略uri"),
        Option("export_interval", "ei", 5,
               help=u"获取策略间隔"),
        Option("reset_interval", "ri", 60,
               help=u"重置策略服务器数据"),
        Option("source_address", "s", "0.0.0.0:8786",
               help=u"http客户端绑定地址"),
        Option("ip", "i", "127.0.0.1", mandatory=True,
               help=u"RouterOS telnet IP"),
        Option("port", "p", 23,
               help=u"RouterOS telnet PORT"),
        Option("user", "U", "admin",
               help=u"RouterOS telnet user"),
        Option("password", "P", "",
               help=u"RouterOS telnet password"),
    )
    options = Options(options)
    options.parse_option(True)
    uri = options.get("uri")
    pull_interval = max(options.get("export_interval"), 1)
    reset_interval = max(options.get("reset_interval"), 5)

    source_address = options.get("source_address").split(":")
    http_client = HttpClientKeepAlive(uri, (source_address[0], int(source_address[1])))
    ros_adapter = RosProxy(options.get("ip"), options.get("port"),
                           options.get("user"), options.get("password"))
    last_pull = -pull_interval
    last_reset = time.time()
    while 1:
        try:
            cur_time = time.time()
            pull_passed = cur_time - last_pull
            reset_passed = cur_time - last_reset
            if pull_passed >= pull_interval:
                last_pull = cur_time
                ips = http_client.get_ip_strategy()
                ros = ros_adapter.get_address_list()
                update_ip_strategy(ros, ips, ros_adapter)
                # 获取数据后重置，保证ping次数
                if reset_passed >= reset_interval:
                    last_reset = cur_time
                    http_client.server_reset()
            rest_pull = pull_interval - (cur_time - last_pull)
            rest_reset = reset_interval - (cur_time - last_reset)
            sleep_time = min(rest_pull, rest_reset) - (time.time() - cur_time)
            time.sleep(max(sleep_time, 1))
        except (SystemExit, KeyboardInterrupt):
            break
        except socket.error:
            ros_adapter = RosProxy(options.get("ip"), options.get("port"),
                                   options.get("user"), options.get("password"))
        except:
            print traceback.print_exc()


if __name__ == "__main__":
    do_main()
