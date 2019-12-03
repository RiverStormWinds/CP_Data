#!/usr/bin/python
# -*- coding: gbk -*-
import os
import sys
import shutil
import time
import collections
import subprocess
import struct
import datetime
import decimal
import logging
import itertools
from gl import GlobalLogging as Logging
from dbfread import DBF
from SimpleXMLRPCServer import SimpleXMLRPCServer
import commFuncs as cF

# import Logging
reload(sys)
sys.setdefaultencoding('gbk')


def mycopyfile(flag):
    try:
        srcfile = r'D:\\ABOSS2\\SSKH\\MN\\qtymtzl.dbf'
        dstfile = r'D:\YMAT_MY_COPY\qtymtzl_%s_%s.dbf' % (time.strftime('%Y%m%d%H%M%S'), flag)
        if not os.path.isfile(srcfile):
            print "%s not exist!" % (srcfile)
        else:
            fpath, fname = os.path.split(dstfile)  # 分离文件名和路径
            if not os.path.exists(fpath):
                os.makedirs(fpath)  # 创建路径
            shutil.copyfile(srcfile, dstfile)  # 复制文件
            print "copy %s -> %s" % (srcfile, dstfile)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().info(exc_info)
        return -1, exc_info


def dbfreader(f):
    """Returns an iterator over records in a Xbase DBF file.

    The first row returned contains the field names.
    The second row contains field specs: (type, size, decimal places).
    Subsequent rows contain the data records.
    If a record is marked as deleted, it is skipped.

    File should be opened for binary reads.

    """
    # See DBF format spec at:
    #     http://www.pgts.com.au/download/public/xbase.htm#DBF_STRUCT

    numrec, lenheader = struct.unpack('<xxxxLH22x', f.read(32))
    numfields = (lenheader - 33) // 32

    fields = []
    for fieldno in xrange(numfields):
        name, typ, size, deci = struct.unpack('<11sc4xBB14x', f.read(32))
        name = name.replace('\0', '')  # eliminate NULs from string
        fields.append((name, typ, size, deci))
    yield [field[0] for field in fields]
    yield [tuple(field[1:]) for field in fields]

    terminator = f.read(1)
    # assert terminator == '\r'

    fields.insert(0, ('DeletionFlag', 'C', 1, 0))
    fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in fields])
    fmtsiz = struct.calcsize(fmt)
    for i in xrange(numrec):
        record = struct.unpack(fmt, f.read(fmtsiz))
        if record[0] != ' ':
            continue  # deleted record
        result = []
        for (name, typ, size, deci), value in itertools.izip(fields, record):
            # value = str(value).decode("utf-8").encode('gb2312')
            if name == 'DeletionFlag':
                continue
            if typ == "N":
                value = value.replace('\0', '').lstrip()
                if value == '':
                    value = 0
                elif deci:
                    value = decimal.Decimal(value)
                else:
                    if isinstance(value, int):
                        value = int(value)
            elif typ == 'D':
                y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                value = datetime.date(y, m, d)
            elif typ == 'L':
                value = (value in 'YyTt' and 'T') or (value in 'NnFf' and 'F') or '?'
            elif typ == 'F':
                value = float(value)
            result.append(value)
        yield result


def dbfwriter(f, fieldnames, fieldspecs, records):
    """ Return a string suitable for writing directly to a binary dbf file.

    File f should be open for writing in a binary mode.

    Fieldnames should be no longer than ten characters and not include \x00.
    Fieldspecs are in the form (type, size, deci) where
        type is one of:
            C for ascii character data
            M for ascii character memo data (real memo fields not supported)
            D for datetime objects
            N for ints or decimal objects
            L for logical values 'T', 'F', or '?'
        size is the field width
        deci is the number of decimal places in the provided decimal object
    Records can be an iterable over the records (sequences of field values).

    """

    # header info

    ver = 3
    now = datetime.datetime.now()
    yr, mon, day = now.year - 1900, now.month, now.day
    numrec = len(records)
    numfields = len(fieldspecs)
    lenheader = numfields * 32 + 33
    lenrecord = sum(field[1] for field in fieldspecs) + 1
    hdr = struct.pack('<BBBBLHH20x', ver, yr, mon, day, numrec, lenheader, lenrecord)
    f.write(hdr)

    # field specs
    for name, (typ, size, deci) in itertools.izip(fieldnames, fieldspecs):
        # name = str(name).decode("utf-8").encode('gb2312')
        name = str(name).encode('GBK')
        name = name.ljust(11, '\x00')
        fld = struct.pack('<11sc4xBB14x', name, typ, size, deci)
        f.write(fld)

    # terminator
    f.write('\r')

    # records
    for record in records:
        f.write(' ')  # deletion flag
        for (typ, size, deci), value in itertools.izip(fieldspecs, record):
            # value = str(value).decode("utf-8").encode('gb2312')
            value = str(value).encode('GBK')
            if typ == "N":
                value = str(value).rjust(size, ' ')
            elif typ == 'D':
                value = value.strftime('%Y%m%d')
            elif typ == 'L':
                value = str(value)[0].upper()
            else:
                value = str(value)[:size].ljust(size, ' ')
            assert len(value) == size
            f.write(value)

    # End of file
    f.write('\x1A')


def update_ini_file(path, index_column_name_values, update_column_name_value):
    try:
        Logging.getLog().info(u"path:%s, index_column_name_values:%s, update_column_name_value:%s" % (
        path, str(index_column_name_values), str(update_column_name_value)))
        f1 = open(path, 'r')
        result = []
        for i in f1:
            if 'KHDLJGMC_MN' in i:
                i = update_column_name_value.decode('gbk') + "\n"
            result.append(i)
        print len(result)
        f1.close()
        f2 = open(path, 'w')
        for j in result:
            f2.write(j)
        f2.close()
        return 0, ""
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def dbf_read_write_info(path, index_column_name_values, update_column_name_value):
    # dbf_read_write_info('C:\\test.dbf', "YMTH=180000000040&KHRQ=20161013", "KHMC=花果山水帘洞20180203")
    try:
        Logging.getLog().info(u"path:%s, index_column_name_values:%s, update_column_name_value:%s" % (
        path, str(index_column_name_values), str(update_column_name_value)))
        if "ZDMNHB.ini" in path:
            update_ini_file(path, index_column_name_values, update_column_name_value)
            logging.getLogger("更新成功 ZDMNHB.ini")
            return 0, ("",)
        logging.getLogger("enter dbf_read_write_info")
        # 判断是否需要修改多个文件的内容
        # print path, index_column_name_values, update_column_name_value
        if '|' in update_column_name_value:
            update_column_name_values = update_column_name_value.split("|")
            if update_column_name_values:
                update_column_name_value = update_column_name_values[0]
                if 'delete' in path:
                    path = path.replace("delete", "")
                    delete_dbf_file(path, index_column_name_values, update_column_name_value)
                else:
                    update_dbf_file(path, index_column_name_values, update_column_name_value)
            if len(update_column_name_values) >= 2:
                for i in update_column_name_values[1:]:
                    path, index_column_name_values, update_column_name_value = i.split(";")
                    update_dbf_file(path, index_column_name_values, update_column_name_value)
        elif 'delete' in path:
            path = path.replace("delete", "")
            delete_dbf_file(path, index_column_name_values, update_column_name_value)
        else:
            update_dbf_file(path, index_column_name_values, update_column_name_value)
        return 0, ("",)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def add_dbf_file_data(path, col, value):
    try:
        # col = ["YMTH", "YMTZT", "KHRQ", "XHRQ", "KHFS"]
        # value = ['180000000096', 2, 3, 43, 5]
        Logging.getLog().info(u"add_dbf_file_data path:%s, col:%s, value:%s" % (path, str(col), str(value)))
        # print "add_dbf_file_data"
        # print "path:%s, col:%s, value:%s"%(str(path), str(col), str(value))
        new_data = collections.OrderedDict()
        col = [str(i).strip() for i in col]
        value = [str(i).strip() for i in value]
        add_data = collections.OrderedDict(zip(col, value))
        dbf_data = []
        path = path.strip()
        f = open(path, 'rb')
        fieldspecs = []
        fieldnames = []
        db = list(dbfreader(f))
        f.close()
        flag = False
        if db:
            if db[0]:
                for names in db[0]:
                    names = str(names.encode('utf-8')).strip()
                    fieldnames.append(names)
            if len(db) > 1:
                for record in db[1:]:
                    if flag == False:
                        for child_record in record:
                            if isinstance(child_record, tuple):
                                fieldspecs = record
                                flag = True
                                break
                    else:
                        new_record = []
                        for i in record:
                            if isinstance(i, str):
                                i = i.strip()
                            new_record.append(i)
                        row_data = collections.OrderedDict(zip(fieldnames, new_record))
                        anyone_data = row_data
                        dbf_data.append(row_data.values())
            if dbf_data:
                for i in anyone_data:
                    if i in add_data.keys():
                        new_data[i] = add_data[i]
                    else:
                        new_data[i] = ""
                if new_data:
                    # print "new_data"
                    Logging.getLog().info(str(new_data))
                    dbf_data.append(new_data.values())
            if os.path.exists(path):
                os.remove(path)
            f = open(path, 'wb')
            dbfwriter(f, fieldnames, fieldspecs, dbf_data)
            f.close()
        return 0, ("",)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def update_dbf_file(path, index_column_name_values, update_column_name_value):
    try:
        # dbf_read_write_info('C:\\test.dbf', "YMTH=180000000040&KHRQ=20161013", "KHMC=花果山水帘洞20180203")
        # mycopyfile("before")
        Logging.getLog().info(u"path:%s, index_column_name_values:%s, update_column_name_value:%s" % (
        path, str(index_column_name_values), str(update_column_name_value)))
        index_column_name_values_list = []
        if '&' in index_column_name_values:
            index_column_name_values_list = index_column_name_values.split("&")
        if not index_column_name_values_list:
            index_column_name_values_list.append(index_column_name_values)
        # for index, i in enumerate(index_column_name_values_list):
        #
        # index_column_name = str(index_column_name_values.split("=")[0]).strip()
        # index_column_value = str(index_column_name_values.split("=")[1]).strip()
        update_column_name = str(update_column_name_value.split("=")[0]).strip()
        update_column_value = str(update_column_name_value.split("=")[1]).strip()
        dbf_data = []
        f = open(path, 'rb')
        fieldspecs = []
        fieldnames = []
        db = list(dbfreader(f))
        f.close()
        flag = False
        flag_update = 0
        if db:
            if db[0]:
                for names in db[0]:
                    names = str(names.encode('utf-8')).strip()
                    fieldnames.append(names)
            # dbf_data.append(fieldnames)
            print fieldnames
            if len(db) > 1:
                for record in db[1:]:
                    if flag == False:
                        for child_record in record:
                            if isinstance(child_record, tuple):
                                fieldspecs = record
                                flag = True
                                break
                    else:
                        new_record = []
                        for i in record:
                            if isinstance(i, str):
                                i = i.strip()
                            new_record.append(i)
                        row_data = collections.OrderedDict(zip(fieldnames, new_record))
                        # if flag_update == 0:
                        code_status_list = []
                        for index, i in enumerate(index_column_name_values_list):
                            code_status = 'False'
                            index_column_name = str(i.split("=")[0]).strip()
                            index_column_value = str(i.split("=")[1]).strip()
                            if index_column_name in fieldnames:
                                if str(row_data[str(index_column_name)]).strip() == str(index_column_value).strip():
                                    code_status = 'True'
                                    code_status_list.append(code_status)
                        if len(index_column_name_values_list) == len(code_status_list) and 'True' in code_status_list:
                            row_data[str(update_column_name)] = str(update_column_value)
                            # flag_update = 1
                            Logging.getLog().info("flag_update=1")
                            Logging.getLog().info(str(row_data.values()))
                            # print "flag_update=1"
                            # print row_data.values()
                        dbf_data.append(row_data.values())
        if os.path.exists(path):
            os.remove(path)
        f = open(path, 'wb')
        # print dbf_data[-1]
        dbfwriter(f, fieldnames, fieldspecs, dbf_data)
        f.close()
        # mycopyfile("after")
        return 0, ("",)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def delete_dbf_file(path, index_column_name_values, update_column_name_value):
    try:
        # mycopyfile("before")
        Logging.getLog().info(u"path:%s, index_column_name_values:%s, update_column_name_value:%s" % (
        path, str(index_column_name_values), str(update_column_name_value)))
        index_column_name_values_list = []
        if '&' in index_column_name_values:
            index_column_name_values_list = index_column_name_values.split("&")
        if not index_column_name_values_list:
            index_column_name_values_list.append(index_column_name_values)

        # index_column_name = str(index_column_name_values.split("=")[0]).strip()
        # index_column_value = str(index_column_name_values.split("=")[1]).strip()
        update_column_name = str(update_column_name_value.split("=")[0]).strip()
        update_column_value = str(update_column_name_value.split("=")[1]).strip()
        dbf_data = []
        f = open(path, 'rb')
        fieldspecs = []
        fieldnames = []
        db = list(dbfreader(f))
        f.close()
        flag = False
        if db:
            if db[0]:
                for names in db[0]:
                    names = str(names.encode('utf-8')).strip()
                    fieldnames.append(names)
            # dbf_data.append(fieldnames)
            print fieldnames
            if len(db) > 1:
                for record in db[1:]:
                    flag_update = 0
                    if flag == False:
                        for child_record in record:
                            if isinstance(child_record, tuple):
                                fieldspecs = record
                                flag = True
                                break
                    else:
                        new_record = []
                        for i in record:
                            if isinstance(i, str):
                                i = i.strip()
                            new_record.append(i)
                        row_data = collections.OrderedDict(zip(fieldnames, new_record))
                        code_status_list = []
                        for index, i in enumerate(index_column_name_values_list):
                            code_status = 'False'
                            index_column_name = str(i.split("=")[0]).strip()
                            index_column_value = str(i.split("=")[1]).strip()
                            if index_column_name in fieldnames:
                                if str(row_data[str(index_column_name)]).strip() == str(index_column_value).strip():
                                    code_status = 'True'
                                    code_status_list.append(code_status)
                        if len(index_column_name_values_list) == len(code_status_list) and 'True' in code_status_list:
                            # row_data[str(update_column_name)] = str(update_column_value)
                            flag_update = 1
                            Logging.getLog().info("flag_update=1")
                            Logging.getLog().info(str(row_data.values()))
                            # print "flag_update=1"
                            # print row_data.values()
                        # # if flag_update == 0:
                        # if index_column_name in fieldnames:
                        #     if str(row_data[str(index_column_name)]).strip() == str(index_column_value).strip():
                        #         # row_data[str(update_column_name)] = str(update_column_value)
                        #         flag_update = 1
                        #         print "已删除"
                        # print row_data.values()
                        # print "flag_update=0"
                        if flag_update != 1:
                            dbf_data.append(row_data.values())
                        else:
                            Logging.getLog().info(str(row_data.values()))
                            # print row_data.values()
        if os.path.exists(path):
            os.remove(path)
        f = open(path, 'wb')
        # print dbf_data[-1]
        dbfwriter(f, fieldnames, fieldspecs, dbf_data)
        f.close()
        mycopyfile("after")
        return 0, ("",)
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, exc_info


def RunAutoitScript(param):
    """
    运行当前服务路径下的脚本
    param：脚本名称
    """

    log_info = ""

    cmd_str = '.\\Script\\%s' % (param)

    try:
        Logging.getLog().info(u"param:%s" % (str(param)))
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        # Logging.getLog().debug("ready to execute")
        proc = subprocess.Popen(cmd_str, shell=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        # proc.wait()
        while proc.poll() is None:
            line = proc.stdout.readline()
            line = line.strip()
            if line:
                # print "%s" % line
                Logging.getLog().info("%s" % line)
        # 退出监控线程
        # Logging.getLog().debug("quit subprocess")
        # print "quit subprocess with returncode = %s" % str(proc.returncode)
        Logging.getLog().info("quit subprocess with returncode = %s" % str(proc.returncode))
        # output_info = proc.stdout.readlines()
        # log_info = "".join(output_info)
        if proc.returncode == 0:
            return 0, ""
        else:
            return -1, u"脚本执行出错"

    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
        return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info)


def RunAutoitHsChangeMoney(param):
    """
    运行当前服务路径下的脚本
    param：脚本名称
    """
    Logging.getLog().info(u"param:%s" % (str(param)))
    log_info = []
    params = param.split(",")
    path = params[0]
    name = params[1]
    cmd_str = u'%s\\HsChangeMoney\\%s' % (path, name)
    Logging.getLog().info(u"cmd_str:%s" % (cmd_str))
    # print cmd_str
    try:
        si = subprocess.STARTUPINFO
        si.wShowWindow = subprocess.SW_HIDE
        proc = subprocess.Popen(cmd_str, shell=False, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        while proc.poll() is None:
            line = proc.stdout.readline()
            line = line.strip()
            if line:
                log_info.append(line)
        log_info = ",".join(log_info)
        try:
            log_info = log_info.decode('gbk')
        except Exception as e:
            log_info = log_info.decode('utf-8')
        Logging.getLog().info(log_info)
        # print log_info
        Logging.getLog().info("quit subprocess with returncode = %s" % str(proc.returncode))
        # print "quit subprocess with returncode = %s" % str(proc.returncode)
        if proc.returncode == 0:
            return 0, log_info
        else:
            return -1, log_info
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
        return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info)


def read_dbf_file(path):
    try:
        Logging.getLog().info(u"path:%s" % (str(path)))
        f = open(path, 'rb')
        db = list(dbfreader(f))
        num = len(db)
        if num >= 2:
            num = num - 1
        print num
    except BaseException, ex:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info))
        return -1, u"异常发生，请检查日志文件,提示信息为:%s" % (exc_info)


if __name__ == '__main__':
    # read_dbf_file(r'D:\test.dbf')
    # add_dbf_file_data("D:\\propcg122034.dbf",['SBBH','ZQZH','TZRMC','JSHY','XWH','SFZH','YWLX'],[1,2,3,4,5,6,7])
    # # add_dbf_file_data("D:\\test.dbf")
    # # path = r"D:\code\test\qtymtzl一码通模拟库.dbf"
    # # index_column_name_values = "YMTH=180000000096"
    # # update_column_name_value = "LXDZ="
    # # dbf_read_write_info('C:\\test.dbf', "YMTH=180000000096",
    # #                     "LXDZ=花果山水帘洞20180203|C:\\test2.dbf;YMTH=180000000096;LXDZ=")
    # # dbf_read_write_info('D:\\ZDMNHB.ini', "KHDLJGMC_MN=国泰君安证券股份有限公司",
    # #                     "KHDLJGMC_MN=国泰君安证券股份有限公司GTJA")


    s = SimpleXMLRPCServer(('0.0.0.0', 8888))
    s.register_function(dbf_read_write_info)
    s.register_function(RunAutoitScript)
    s.register_function(add_dbf_file_data)
    s.serve_forever()


    # dbf_read_write_info('C:\\test.dbf', "deleteYMTH=180000000040&KHRQ=20161013","KHMC=花果山水帘洞20180203")
    # delete_dbf_file('C:\\test.dbf', "YMTH=180000000040&KHRQ=20161013","KHMC=花果山水帘洞20180203")
