# coding: utf-8
# Copyright (C) zhongjie luo <l.zhjie@qq.com>
from telnetlib import Telnet, DO, DONT, IAC, WILL, WONT, TTYPE, SB, SE, theNULL, ECHO, NOP
import time
import select
import sys

ttype_doing = False


# https://www.cnblogs.com/dazhaxie/archive/2012/06/27/2566054.html
# 终端类型协商
def option_callback(socket, cmd, opt):
    global ttype_doing
    print ord(cmd), ord(opt)
    if cmd in (DO, DONT):
        if opt == TTYPE and cmd == DO:
            if ttype_doing is False:
                ttype_doing = True
                socket.sendall(IAC + WONT + opt)
                socket.sendall(IAC + WILL + opt)
            return
        socket.sendall(IAC + WONT + opt)
        return
    if cmd in (WILL, WONT):
        if opt == TTYPE and cmd == WILL:
            socket.sendall(IAC + WONT + opt)
            socket.sendall(IAC + DO + opt)
            return
        socket.sendall(IAC + DONT + opt)
        return
    if cmd == SB and opt == ECHO:
        socket.sendall(IAC + SB + TTYPE + theNULL + "VT100" + IAC + SE)


class MyTelnet(object):
    """https://www.csie.ntu.edu.tw/~r92094/c++/VT100.html"""
    def __init__(self, host, user, password, timeout=1, port=23, command_prompt="> "):
        tel_ = Telnet(host, port, timeout)
        # tel_.set_debuglevel(11)
        # tel_.set_option_negotiation_callback(option_callback)
        tel_.read_until(":")
        tel_.write("%s\n" % user)
        tel_.read_until(":")
        tel_.write("%s\n" % password)
        while 1:
            temp = tel_.read_until("\033[6n", timeout=0.1)
            sys.stdout.write(temp)
            if temp.endswith(command_prompt):
                break
            tel_.write("\033[;R")
        self._tel = tel_
        self._cp = command_prompt
        self._timeout = timeout

    def __del__(self):
        self._tel.close()

    def read_until(self):
        result = ""
        timeout = self._timeout
        b_time = time.time()
        while 1:
            if time.time() - b_time >= timeout:
                return None
            ready = select.select([self._tel.sock], [], [], 1)
            for sock in ready[0]:
                temp = MyTelnet.socket_read_all(sock)
                temp = temp.replace("\r\x00", "_")
                result += temp
                if result.endswith(self._cp):
                    return result

    def clear_buffer(self):
        ready = select.select([self._tel.sock], [], [], 0)
        for sock in ready[0]:
            MyTelnet.socket_read_all(sock)

    def change_path(self, paths):
        self.clear_buffer()
        for path in paths:
            self._tel.write("%s\r\n" % path)
            self.read_until()

    def command(self, cmd, clear_buffer=False, encoding="ascii"):
        if clear_buffer:
            self.clear_buffer()
        self._tel.write("%s\r\n" % cmd.encode(encoding))
        return self.read_until()

    @staticmethod
    def socket_read_all(socket):
        length = 1024
        content = socket.recv(length)
        if len(content) >= length:
            try:
                while 1:
                    temp = socket.recv(length)
                    if temp is None or len(temp) == 0:
                        break
                    content += temp
            except:
                pass
        return content


if __name__ == "__main__":
    tel = MyTelnet("127.0.0.1", "admin", "")
    tel.change_path(["ip", "firewall", "address-list"])
    print tel.command("print without-paging")
