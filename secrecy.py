# -*- coding:gbk -*-
from Crypto.Cipher import AES
import MySQLdb
import gl
import commFuncs as cF


def encrypt_mode_cbc(data, key, iv='www.timesvc.net!', base64=True):
    '''
    /**
    * AES加密字符串
    *
    * @param string data 加密的串
    * @param string key 密钥(只能是16、24、32位)
    * @param string iv 16位长度向量
    * @param bool 编码格式（true:base64 / false:十六进制）
    * @return string 加密后的结果
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
    * AES解密字符串
    *
    * @param string encrypted 待解密的串
    * @param string key 密钥
    * @param string iv 16位长度向量
    * @param bool 编码（true:base64 / false:十六进制）
    * @return string 解密后的结果 or bool
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
    将案例库中未加密的案例命令串
    cmdstring 
    全部进行加密处理并导入案例库
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
    将案例库中未解密的案例命令串
    cmdstring 
    全部进行解密处理并导入案例库
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
        encrypt_database()  # 案例库命令串全部加密
        # decrypt_database() #案例库命令串全部解密
    except BaseException, ex:
        print ex
    pass
