#!/usr/bin/python
# coding=gbk
'''
    ftp�Զ����ء��Զ��ϴ��ű������Եݹ�Ŀ¼����   FTP��ȡ����ģʽ  server ��ͨ2121�˿ڣ�  �ͻ��˿�ͨ1024���ϵ�
'''

from ftplib import FTP
import os, sys, string, datetime, time
import socket
import commFuncs as cF
from gl import GlobalLogging as Logging
import shutil


class XFer:
    def __init__(self, hostaddr, username, password, remotedir, port=21):
        self.hostaddr = hostaddr
        self.username = username
        self.password = password
        self.remotedir = remotedir
        self.port = port
        self.ftp = FTP()
        self.file_list = []

        # ���汾�θ��µ��ļ�list
        self.updated_file_list = []
        # self.ftp.set_debuglevel(2)

    def __del__(self):
        self.ftp.close()
        # self.ftp.set_debuglevel(0)

    def login(self):
        ftp = self.ftp
        try:
            timeout = 60
            socket.setdefaulttimeout(timeout)
            ftp.set_pasv(False)
            # ftp.set_pasv(True)
            # Logging.getLog().debug(u'��ʼ���ӵ� %s' % (self.hostaddr))
            ftp.connect(self.hostaddr, self.port)
            # Logging.getLog().debug(u'�ɹ����ӵ� %s' % (self.hostaddr))
            # Logging.getLog().debug(u'��ʼ��¼�� %s' % (self.hostaddr))
            ftp.login(self.username, self.password)
            Logging.getLog().debug(u'�ɹ����Ӳ���¼�� %s' % (self.hostaddr))
            debug_print(ftp.getwelcome())
            return 0, ""
        except Exception:
            deal_error(u"���ӻ��¼ʧ��")
            return -1, u"���ӻ��¼ʧ��"
        try:
            ftp.cwd(self.remotedir)
        except(Exception):
            deal_error(u'�л�Ŀ¼ʧ��')
            return -1, u'�л�Ŀ¼ʧ��'

    def is_same_size(self, localfile, remotefile):
        try:
            self.ftp.sendcmd("TYPE i")
            remotefile_size = self.ftp.size(remotefile)
        except:
            exc_file = cF.getExceptionInfo()
            #Logging.getLog().debug("�ļ���С��ͬ�� ��������")
            Logging.getLog().error(exc_file)
            remotefile_size = -1
        try:
            if os.path.exists(localfile):
                localfile_size = os.path.getsize(localfile)
            else:
                localfile_size = -1
        except:
            exc_file = cF.getExceptionInfo()
            Logging.getLog().debug(exc_file)
            localfile_size = -1
        # debug_print('lo:%d re:%d' % (localfile_size, remotefile_size), )
        if remotefile_size == localfile_size:
            return 1
        else:
            debug_print('lo:%d re:%d' % (localfile_size, remotefile_size), )
            return 0

    def download_file(self, localfile, remotefile):
        # local_files = ""
        # try:
        #    debug_print(u'>>>>>>>>>>>>�����ļ� %s ... ...' % localfile)
        # except Exception as e:
        #     try:
        #         local_files = localfile.decode("gbk")
        #     except Exception as e:
        #         local_files = localfile.decode("utf-8")
        #     finally:
        #         print localfile
        if self.is_same_size(localfile, remotefile) and 'JZYYAutoTest.jar' not in localfile:
            # debug_print(u'%s �ļ���С��ͬ����������' % localfile)
            return
        else:
            try:
               debug_print(u'>>>>>>>>>>>>�����ļ� %s ... ...' % localfile)
            except Exception as e:
                print localfile
            # debug_print(u'>>>>>>>>>>>>�����ļ� %s ... ...' % localfile)
            # Logging.getLog().debug(u'>>>>>>>>>>>>�����ļ� %s ... ...' % localfile)
        file_handler = ""
        try:
            file_handler = open(localfile, 'wb')
        except Exception as e:
            try:
                localfile = localfile.decode("gbk")
                file_handler = open(localfile, 'wb')
            except Exception as e:
                localfile = localfile.decode("utf-8")
                file_handler = open(localfile, 'wb')
        # file_handler = open(localfile, 'wb')
        self.ftp.retrbinary('RETR %s' % (remotefile), file_handler.write)
        file_handler.close()

        self.updated_file_list.append(localfile)

    def download_files(self, localdir='./', remotedir='./'):
        print localdir, remotedir
        try:
            self.ftp.cwd(remotedir)
        except:
            debug_print(u'Ŀ¼%s�����ڣ�����...' % remotedir)
            return
        if not os.path.isdir(localdir):
            os.makedirs(localdir)
        debug_print(u'�л���Ŀ¼ %s' % self.ftp.pwd())
        self.file_list = []
        self.ftp.dir(self.get_file_list)
        remotenames = self.file_list
        # print(remotenames)
        # return
        for item in remotenames:
            filetype = item[0]
            filename = item[1]
            local = os.path.join(localdir, filename)
            if filetype == 'd':
                # self.download_files(local, filename)
                # ����������Ŀ¼����Ϊ���Ŀ¼������ֻ����zip�ļ�
                continue
            elif filetype == '-':
                self.download_file(local, filename)
            try:
                if filename[-4:] == '.zip' and "Script" not in localdir:
                    cF.unzip_file(local, localdir)
            except Exception as e:
                print e
        self.ftp.cwd('..')
        debug_print(u'�����ϲ�Ŀ¼ %s' % self.ftp.pwd())

    def download_files_init(self, localdir='./', remotedir='./', file_name=""):
        print localdir, remotedir
        try:
            self.ftp.cwd(remotedir)
        except:
            debug_print(u'Ŀ¼%s�����ڣ�����...' % remotedir)
            return
        if not os.path.isdir(localdir):
            os.makedirs(localdir)
        debug_print(u'�л���Ŀ¼ %s' % self.ftp.pwd())
        self.file_list = []
        self.ftp.dir(self.get_file_list)
        remotenames = self.file_list
        # print(remotenames)
        # return
        for item in remotenames:
            filetype = item[0]
            filename = item[1]
            local = os.path.join(localdir, filename)
            if str(filename).split('.')[0] == str(file_name):
                self.download_file(local, filename)
        self.ftp.cwd('..')
        debug_print(u'�����ϲ�Ŀ¼ %s' % self.ftp.pwd())

    def upload_file_ex(self, localfile, remotedir='./'):
        '''
        ��Ҫע�⣬�������ֻ����ഴ��һ�㲻���ڵ�Ŀ¼fixme��
        '''
        Logging.getLog().debug("upload_file_ex(%s,%s)" % (localfile, remotedir))

        if not os.path.isfile(localfile):
            Logging.getLog().debug("file not exist")
            return

        filename = localfile[localfile.rfind('/') + 1:]

        try:
            self.ftp.cwd(remotedir)
        except:
            debug_print(u'��Ŀ¼������ ,����һ�� %s' % remotedir)
            self.ftp.mkd(remotedir)

            try:
                self.ftp.cwd(remotedir)
            except:
                debug_print(u'��Ŀ¼������ ,����һ�� %s' % remotedir)
                self.ftp.mkd(remotedir)

        # if self.is_same_size(localfile, filename):
        #     debug_print('����[���]: %s' %localfile)
        #     return
        try:
            file_handler = open(localfile, 'rb')
            self.ftp.storbinary('STOR %s' % filename, file_handler)
            file_handler.close()
            debug_print(u'�Ѵ���: %s' % localfile)
        except:
            exc_info = cF.getExceptionInfo()
            Logging.getLog().debug(exc_info)
            return -1, exc_info

    def upload_file(self, localfile, remotefile):
        if not os.path.isfile(localfile):
            return
        if self.is_same_size(localfile, remotefile):
            debug_print(u'����[���]: %s' % localfile)
            return
        file_handler = open(localfile, 'rb')
        self.ftp.storbinary('STOR %s' % remotefile, file_handler)
        file_handler.close()
        debug_print(u'�Ѵ���: %s' % localfile)

    def upload_files(self, localdir='./', remotedir='./'):
        if not os.path.isdir(localdir):
            return
        localnames = os.listdir(localdir)
        try:
            self.ftp.cwd(remotedir)
        except:
            debug_print(u'��Ŀ¼������ ,����һ�� %s' % remotedir)
            self.ftp.mkd(remotedir)
        for item in localnames:
            src = os.path.join(localdir, item)
            if os.path.isdir(src):
                try:
                    self.ftp.mkd(item)
                except:
                    debug_print(u'Ŀ¼�Ѵ��� %s' % item)
                self.upload_files(src, item)
            else:
                self.upload_file(src, item)
        self.ftp.cwd('..')

    # def compress_file_zip(self, filename,compressdir):
    #    #if not os.path.isfile(compressdir):
    #    #    Logging.getLog().debug("file not exist")
    #    #    return
    #    try:
    #        self.ftp.cwd(compressdir)
    #    except:
    #        debug_print(u'Ŀ¼%s�����ڣ�����...' % compressdir)
    #        return
    #    shutil.make_archive(filename,'zip',compressdir)

    def get_file_list(self, line):
        ret_arr = []
        file_arr = self.get_filename(line)
        if file_arr[1] not in ['.', '..']:
            self.file_list.append(file_arr)

    def get_filename(self, line):
        pos = line.rfind(' ')
        # while (line[pos] != ' '):
        #     pos += 1
        # while (line[pos] == ' '):
        #     pos += 1
        file_arr = [line[0], line[pos+1:]]
        return file_arr

    def get_updated_file_list(self):
        return self.updated_file_list


def debug_print(s):
    Logging.getLog().debug(s)


def deal_error(e):
    timenow = time.localtime()
    datenow = time.strftime('%Y-%m-%d', timenow)
    logstr = u'%s ��������: %s' % (datenow, e)
    debug_print(logstr)
    file.write(logstr)
    sys.exit()


if __name__ == '__main__':
    f = XFer('10.176.65.17', 'agent', '123456', '.', 2121)
    f.login()
    f.upload_file_ex('./logs/3926.zip', '/Log')
    # f.upload_file_ex('./logs/3922/6610698.log', '/Log/3922')
    # f.download_files('.\\logs\\7219', r'.\Log\7219')
