# coding: utf-8
# Copyright (C) zhongjie luo <l.zhjie@qq.com>
from thirdparty.service import do_service
from ros_proxy import do_main


if __name__ == "__main__":
    do_service(do_main, "ros_proxy")