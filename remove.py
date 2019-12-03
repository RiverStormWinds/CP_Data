# -*- coding: utf-8 -*-
# !/usr/bin/python
# test_copyfile.py

import os, shutil
import time


def mymovefile(srcfile, dstfile):
    if not os.path.isfile(srcfile):
        print "%s not exist!" % (srcfile)
    else:
        fpath, fname = os.path.split(dstfile)  # 分离文件名和路径
        if not os.path.exists(fpath):
            os.makedirs(fpath)  # 创建路径
        shutil.move(srcfile, dstfile)  # 移动文件
        print "move %s -> %s" % (srcfile, dstfile)


def mycopyfile(srcfile, dstfile):
    if not os.path.isfile(srcfile):
        print "%s not exist!" % (srcfile)
    else:
        fpath, fname = os.path.split(dstfile)  # 分离文件名和路径
        if not os.path.exists(fpath):
            os.makedirs(fpath)  # 创建路径
        shutil.copyfile(srcfile, dstfile)  # 复制文件
        print "copy %s -> %s" % (srcfile, dstfile)


srcfile = r'D:\\ABOSS2\\SSKH\\MN\\qtymtzl.dbf'
dstfile = r'D:\YMAT_MY_COPY\qtymtzl_%s.dbf' % time.strftime('%Y%m%d%H%M%S')

mycopyfile(srcfile, dstfile)
