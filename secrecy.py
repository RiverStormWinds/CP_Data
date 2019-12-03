# -*- coding:gbk -*-
from Crypto.Cipher import AES
import MySQLdb
import gl
import commFuncs as cF


def encrypt_mode_cbc(data, key, iv='www.timesvc.net!', base64=True):
    '''
    /**
    * AES�����ַ���
    *
    * @param string data ���ܵĴ�
    * @param string key ��Կ(ֻ����16��24��32λ)
    * @param string iv 16λ��������
    * @param bool �����ʽ��true:base64 / false:ʮ�����ƣ�
    * @return string ���ܺ�Ľ��
    */
    '''
    # data = data.encode('gbk')
    lenth = len(data)
    num = lenth % 16
    data = data.ljust(lenth + 16 - num)
    obj = AES.new(key, AES.MODE_CBC, iv)
    result = obj.encrypt(data)
    return result.encode('base64') if base64 is True else result.encode('hex')


def decrypt_mode_cbc(encrypted, key, iv='www.timesvc.net!', base64=True):
    '''
    /**
    * AES�����ַ���
    *
    * @param string encrypted �����ܵĴ�
    * @param string key ��Կ
    * @param string iv 16λ��������
    * @param bool ���루true:base64 / false:ʮ�����ƣ�
    * @return string ���ܺ�Ľ�� or bool
    */
    '''
    # encrypted = data.encode('gbk')
    encrypted = encrypted.decode('base64') if base64 is True else encrypted.decode('hex')
    if encrypted is not '':
        obj = AES.new(key, AES.MODE_CBC, iv)
        return obj.decrypt(encrypted)
    else:
        return False


def encrypt_database():
    '''
    ����������δ���ܵİ������
    cmdstring 
    ȫ�����м��ܴ������밸����
    '''
    sql = "select sno,sdkpos,sdkposdesc, groupname,case_index,casename,cmdstring from tbl_cases "
    ds = cF.executeCaseSQL(sql)
    for rec in ds:
        try:
            if rec["cmdstring"].__contains__(':'):
                encrypt_cmdstring = encrypt_mode_cbc(rec["cmdstring"].encode('gbk'), 'abcdefghijklmnop')
                sql1 = "update tbl_cases set cmdstring=binary(%s) where sno = %s"
                cmd = (encrypt_cmdstring.decode('gbk'), rec["sno"])
                cF.executeCaseSQL(sql1, cmd)
                print rec["sno"], rec["cmdstring"]
            else:
                pass
        except BaseException, ex:
            print ex


def decrypt_database():
    '''
    ����������δ���ܵİ������
    cmdstring 
    ȫ�����н��ܴ������밸����
    '''
    sql = "select sno,sdkpos,sdkposdesc, groupname,case_index,casename,cmdstring from tbl_cases "
    ds = cF.executeCaseSQL(sql)
    for rec in ds:
        try:
            if rec["cmdstring"].__contains__(':'):
                pass
            else:
                decrypt_cmdstring = decrypt_mode_cbc(rec["cmdstring"].encode('gbk'), 'abcdefghijklmnop')
                sql1 = "update tbl_cases set cmdstring=%s where sno = %s"
                cmd = (decrypt_cmdstring, rec["sno"])
                cF.executeCaseSQL(sql1, cmd)
                print rec["sno"], rec["cmdstring"]
        except BaseException, ex:
            print ex


if __name__ == '__main__':
    try:
        cF.readConfigFile()
        encrypt = encrypt_mode_cbc(
            'funcid:410411,custid:@custid@,custorgid:@orgid@,trdpwd:@trdpwd@,netaddr:0,orgid:@orgid@,operway:4,ext:0,market:2,secuid:@sz_a_credit_secuid@,fundid:@credit_fundid@,stkcode:000789,bsflag:B,price:@openprice@,qty:200,ordergroup:-1,bankcode:@credit_bankcode@,remark:,bankpwd:@trdpwd@',
            'abcdefghijklmnop')
        print encrypt
        print decrypt_mode_cbc(encrypt, 'abcdefghijklmnop')
        encrypt_database()  # ���������ȫ������
        # decrypt_database() #���������ȫ������
    except BaseException, ex:
        print ex
    pass
