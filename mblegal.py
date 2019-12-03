# -*- coding:gbk -*-
import sys
import Queue
import commFuncs as cF
import gl
from gl import GlobalLogging as Logging
from collections import OrderedDict

reload(sys)
sys.setdefaultencoding('utf8')
threadQueue = Queue.Queue()

custid_dict = {'c_T': '32425910', 'c_F': '32425911'}
fundid_dict = {'T_fundid_0_rmb': '', 'T_fundid_0_usd': '', 'T_fundid_0_HKD': '', 'T_fundid_1_rmb': '',
               'T_credit_fundid_0_rmb': '', 'F_fundid_0_rmb': '', 'F_fundid_0_usd': '', 'F_fundid_0_HKD': '',
               'F_fundid_1_rmb': '', 'F_credit_fundid_0_rmb': ''}
secuid = {'T_secuid_1': '', 'T_secuid_2': '', 'T_secuid_5': '', 'T_secuid_9': '', 'T_secuid_A': '', 'T_secuid_D': '',
          'T_secuid_H': '', 'T_secuid_J': '', 'T_secuid_S': '', 'T_secuid_T': '', 'F_secuid_1': '', 'F_secuid_2': '',
          'F_secuid_5': '', 'F_secuid_9': '', 'F_secuid_A': '', 'F_secuid_D': '', 'F_secuid_H': '', 'F_secuid_J': '',
          'F_secuid_S': '', 'F_secuid_T': ''}
param_list = ['T_fundid_0_rmb', 'T_fundid_0_usd', 'T_fundid_0_HKD', 'T_fundid_1_rmb', 'T_credit_fundid_0_rmb',
              'F_fundid_0_rmb', 'F_fundid_0_usd', 'F_fundid_0_HKD', 'F_fundid_1_rmb', 'F_credit_fundid_0_rmb',
              'T_secuid_1', 'T_secuid_2', 'T_secuid_5', 'T_secuid_9', 'T_secuid_A', 'T_secuid_D', 'T_secuid_H',
              'T_secuid_J', 'T_secuid_S', 'T_secuid_T', 'F_secuid_1', 'F_secuid_2', 'F_secuid_5', 'F_secuid_9',
              'F_secuid_A', 'F_secuid_D', 'F_secuid_H', 'F_secuid_J', 'F_secuid_S', 'F_secuid_T', 'c_T', 'c_F', 'o_T',
              'o_F']
param_dict = {}


def addindex(cmdstring, casename):
    # ���
    key_values_f = {'c_F': u'�Ǳ��˿ͻ�����',
                    'F_fundid_0_rmb': u'�Ǳ��˵ķ�������������ʽ��ʺ�',
                    'F_fundid_0_usd': u'�Ǳ��˵ķ�������Ԫ���ʽ��ʺ�',
                    'F_fundid_0_HKD': u'�Ǳ��˵ķ����ø۱����ʽ��ʺ�',
                    'F_fundid_1_rmb': u'�Ǳ��˵ķ���������Ҹ��ʽ��ʺ�',
                    'F_credit_fundid_0_rmb': u'�Ǳ��˵�������������ʽ��ʺ�',
                    'F_secuid_1': u'�г�1�ķǱ��˹ɶ�����',
                    'F_secuid_2': u'�г�2�ķǱ��˹ɶ�����',
                    'F_secuid_5': u'�г�5�ķǱ��˹ɶ�����',
                    'F_secuid_9': u'�г�9�ķǱ��˹ɶ�����',
                    'F_secuid_A': u'�г�A�ķǱ��˹ɶ�����',
                    'F_secuid_D': u'�г�D�ķǱ��˹ɶ�����',
                    'F_secuid_H': u'�г�H�ķǱ��˹ɶ�����',
                    'F_secuid_J': u'�г�J�ķǱ��˹ɶ�����',
                    'F_secuid_S': u'�г�S�ķǱ��˹ɶ�����',
                    'F_secuid_T': u'�г�T�ķǱ��˹ɶ�����',
                    'o_F': u'�Ǳ��˻�������'}
    key_values = {'c_T': u'���˵Ŀͻ�����',
                  'c_F': u'�Ǳ��˿ͻ�����',
                  'T_fundid_0_rmb': u'���˵ķ�������������ʽ��ʺ�',
                  'T_fundid_0_usd': u'���˵ķ�������Ԫ���ʽ��ʺ�',
                  'T_fundid_0_HKD': u'���˵ķ����ø۱����ʽ��ʺ�',
                  'T_fundid_1_rmb': u'���˵���������Ҹ��ʽ��ʺ�',
                  'T_credit_fundid_0_rmb': u'���˵ķ�������������ʽ��ʺ�',
                  'F_fundid_0_rmb': u'�Ǳ��˵ķ�������������ʽ��ʺ�',
                  'F_fundid_0_usd': u'�Ǳ��˵ķ�������Ԫ���ʽ��ʺ�',
                  'F_fundid_0_HKD': u'�Ǳ��˵ķ����ø۱����ʽ��ʺ�',
                  'F_fundid_1_rmb': u'�Ǳ��˵ķ���������Ҹ��ʽ��ʺ�',
                  'F_credit_fundid_0_rmb': u'�Ǳ��˵�������������ʽ��ʺ�',
                  'T_secuid_1': u'�г�1�ı��˹ɶ�����',
                  'T_secuid_2': u'�г�2�ı��˹ɶ�����',
                  'T_secuid_5': u'�г�5�ı��˹ɶ�����',
                  'T_secuid_9': u'�г�9�ı��˹ɶ�����',
                  'T_secuid_A': u'�г�A�ı��˹ɶ�����',
                  'T_secuid_D': u'�г�D�ı��˹ɶ�����',
                  'T_secuid_H': u'�г�H�ı��˹ɶ�����',
                  'T_secuid_J': u'�г�J�ı��˹ɶ�����',
                  'T_secuid_S': u'�г�S�ı��˹ɶ�����',
                  'T_secuid_T': u'�г�T�ı��˹ɶ�����',
                  'F_secuid_1': u'�г�1�ķǱ��˹ɶ�����',
                  'F_secuid_2': u'�г�2�ķǱ��˹ɶ�����',
                  'F_secuid_5': u'�г�5�ķǱ��˹ɶ�����',
                  'F_secuid_9': u'�г�9�ķǱ��˹ɶ�����',
                  'F_secuid_A': u'�г�A�ķǱ��˹ɶ�����',
                  'F_secuid_D': u'�г�D�ķǱ��˹ɶ�����',
                  'F_secuid_H': u'�г�H�ķǱ��˹ɶ�����',
                  'F_secuid_J': u'�г�J�ķǱ��˹ɶ�����',
                  'F_secuid_S': u'�г�S�ķǱ��˹ɶ�����',
                  'F_secuid_T': u'�г�T�ķǱ��˹ɶ�����',
                  '1': u'�г�1',
                  '2': u'�г�2',
                  '5': u'�г�5',
                  '9': u'�г�9',
                  'A': u'�г�A',
                  'D': u'�г�D',
                  'H': u'�г�H',
                  'J': u'�г�J',
                  'S': u'�г�S',
                  'T': u'�г�T',
                  'o_T': u'���˻�������',
                  'o_F': u'�Ǳ��˻�������',
                  '2I': u'�������2I',
                  '2J': u'�������2J',
                  '02': u'�������02',
                  '03': u'�������03',
                  '00': u'�������00',
                  '01': u'�������01',
                  '06': u'�������06',
                  '07': u'�������07',
                  '04': u'�������04',
                  '05': u'�������05',
                  '0:': u'�������0:',
                  '0;': u'�������0;',
                  '08': u'�������08',
                  '09': u'�������09',
                  '0>': u'�������0>',
                  '0?': u'�������0?',
                  '0<': u'�������0<',
                  '0=': u'�������0=',
                  '0#': u'�������0#',
                  '0!': u'�������0!',
                  '0+': u'�������0+',
                  '0(': u'�������0(',
                  '0)': u'�������0)',
                  '0.': u'�������0.',
                  '0&': u'�������0&',
                  '0': u'�������0',
                  '0R': u'�������0R',
                  '0S': u'�������0S',
                  '0P': u'�������0P',
                  '0Q': u'�������0Q',
                  '0V': u'�������0V',
                  '0W': u'�������0W',
                  '0T': u'�������0T',
                  '0U': u'�������0U',
                  '0Z': u'�������0Z',
                  '0[': u'�������0[',
                  '0X': u'�������0X',
                  '0Y': u'�������0Y',
                  '0^': u'�������0^',
                  '0_': u'�������0_',
                  '0]': u'�������0]',
                  '0B': u'�������0B',
                  '0C': u'�������0C',
                  '0A': u'�������0A',
                  '0F': u'�������0F',
                  '0G': u'�������0G',
                  '0D': u'�������0D',
                  '0E': u'�������0E',
                  '0J': u'�������0J',
                  '0K': u'�������0K',
                  '0H': u'�������0H',
                  '0I': u'�������0I',
                  '0N': u'�������0N',
                  '0O': u'�������0O',
                  '0L': u'�������0L',
                  '0M': u'�������0M',
                  '0r': u'�������0r',
                  '0s': u'�������0s',
                  '0p': u'�������0p',
                  '0q': u'�������0q',
                  '0v': u'�������0v',
                  '0w': u'�������0w',
                  '0t': u'�������0t',
                  '0u': u'�������0u',
                  '0z': u'�������0z',
                  '0{': u'�������0{',
                  '0x': u'�������0x',
                  '0y': u'�������0y',
                  '0~': u'�������0~',
                  '0}': u'�������0}',
                  '0b': u'�������0b',
                  '0c': u'�������0c',
                  '0`': u'�������0`',
                  '0a': u'�������0a',
                  '0f': u'�������0f',
                  '0g': u'�������0g',
                  '0d': u'�������0d',
                  '0e': u'�������0e',
                  '0j': u'�������0j',
                  '0k': u'�������0k',
                  '0h': u'�������0h',
                  '0i': u'�������0i',
                  '0n': u'�������0n',
                  '0o': u'�������0o',
                  '0l': u'�������0l',
                  '0m': u'�������0m',
                  'ZZ': u'�������ZZ',
                  '1D': u'�������1D',
                  '1t': u'�������1t',
                  '1v': u'�������1v',
                  '1y': u'�������1y',
                  '1x': u'�������1x',
                  '11': u'�������11',
                  '10': u'�������10',
                  '13': u'�������13',
                  '12': u'�������12',
                  '0,': u'�������0,',
                  '1': u'ʱ��Ƭ1',
                  '2': u'ʱ��Ƭ2',
                  '3': u'ʱ��Ƭ3',
                  '4': u'ʱ��Ƭ4',
                  '5': u'ʱ��Ƭ5',
                  '6': u'ʱ��Ƭ6',
                  'qty_below_min': u'������С������',
                  'qty_normal': u'����������',
                  'qty_beyond_maxmize': u'�����������',
                  'price_below_min': u'���ڵ�ͣ�۸�',
                  'price_normal': u'�����۸�',
                  'price_beyond_maxmize': u'������ͣ�۸�'
                  }
    try:
        case_name = casename.replace('-', '&')
        for key_f in key_values_f:
            if not key_values_f[key_f] in case_name:
                continue
            else:
                case_name = case_name.replace(key_values_f[key_f], key_f)
        for key in key_values:
            if not key_values[key] in casename:
                continue
            else:
                case_name = case_name.replace(key_values[key], key)

        case_name = case_name.replace('&&', '&')
        cstr_dict = {}
        for item in cmdstring.split('#'):
            cstr_dict[item.split('=')[0]] = item.split('=')[1]
        cstr_dict['custid'] = case_name.split('&')[0]
        cstr_dict['custorgid'] = case_name.split('&')[4]
        cstr_dict['orgid'] = case_name.split('&')[4]
        cstr_dict['secuid'] = case_name.split('&')[2]
        cstr_dict['fundid'] = case_name.split('&')[1]
        c_str = cmdstring
        for c_item in cstr_dict.keys():
            if c_item == 'custid':
                c_str = c_str.replace((c_str.split('custid=')[1]).split('#')[0], '@' + cstr_dict[c_item] + '@')
            elif c_item == 'custorgid':
                c_str = c_str.replace((c_str.split('custorgid=')[1]).split('#')[0], '@' + cstr_dict[c_item] + '@')
            elif c_item == 'orgid':
                c_str = c_str.replace((c_str.split('orgid=')[1]).split('#')[0], '@' + cstr_dict[c_item] + '@')
            elif c_item == 'fundid':
                c_str = c_str.replace((c_str.split('fundid=')[1]).split('#')[0], '@' + cstr_dict[c_item] + '@')
            elif c_item == 'secuid':
                c_str = c_str.replace((c_str.split('secuid=')[1]).split('#')[0], '@' + cstr_dict[c_item] + '@')
            else:
                continue
        return c_str

    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


def getStkcode(market, serverid):
    '''
    �����ݿ��ȡ�����г�����
    ����Ӧд���ֵ�Market_dict
    '''
    ret, conn = cF.ConnectToRunDB(serverid)

    if ret < 0:
        return -1, conn
    cursor = conn.cursor()
    sql = "select top 1 stkcode from run..stktrd where market='%s'" % market
    k = cursor.execute(sql)
    rec = k.fetchone()
    if rec == None:
        return -1, u'������'
    else:
        stkcode = rec[0].strip()

    return 0, stkcode


def ReplaceParam(casename, cmdstring, serverid):
    # ���
    try:
        print u'this is the answer'
        custid_dict['c_T'] = gl.g_paramInfoDict.get(serverid)['0']['custid']
        custid_dict['c_F'] = gl.g_paramInfoDict.get(serverid)['1']['custid']
        # ������
        cmdstring = addindex(cmdstring, casename)
        ret, conn = cF.ConnectToRunDB(serverid)
        if ret < 0:
            return -1, conn

        if conn < 0:
            return
        cursor = conn.cursor()
        sql = "select f1.fundid T_fundid_0_rmb," \
              " f2.fundid T_fundid_0_usd," \
              " f3.fundid T_fundid_0_HKD," \
              " f4.fundid T_fundid_1_rmb," \
              " f5.fundid T_credit_fundid_0_rmb," \
              " f6.fundid F_fundid_0_rmb," \
              " f7.fundid F_fundid_0_usd," \
              " f8.fundid F_fundid_0_HKD," \
              " f9.fundid F_fundid_1_rmb," \
              " f10.fundid F_credit_fundid_0_rmb," \
              " s1.secuid T_secuid_1,s2.secuid T_secuid_2," \
              " s3.secuid T_secuid_5,s4.secuid T_secuid_9," \
              " s5.secuid T_secuid_A,s6.secuid T_secuid_D," \
              " s7.secuid T_secuid_H,s8.secuid T_secuid_J," \
              " s9.secuid T_secuid_S,s10.secuid T_secuid_T," \
              " s11.secuid F_secuid_1,s12.secuid F_secuid_2," \
              " s13.secuid F_secuid_5,s14.secuid F_secuid_9," \
              " s15.secuid F_secuid_A,s16.secuid F_secuid_D," \
              " s17.secuid F_secuid_H,s18.secuid F_secuid_J," \
              " s19.secuid F_secuid_S,s20.secuid F_secuid_T," \
              " c1.custid c_T,c2.custid c_F," \
              " c1.orgid o_T,c2.orgid o_F" \
              " from run..fundasset f1, run..fundasset f2, run..fundasset f3, run..fundasset f4, run..fundasset f5, run..fundasset f6, run..fundasset f7, run..fundasset f8, run..fundasset f9, run..fundasset f10," \
              " run..secuid s1, run..secuid s2, run..secuid s3, run..secuid s4, run..secuid s5, run..secuid s6, run..secuid s7, run..secuid s8, run..secuid s9, run..secuid s10," \
              " run..secuid s11, run..secuid s12, run..secuid s13, run..secuid s14, run..secuid s15, run..secuid s16, run..secuid s17, run..secuid s18, run..secuid s19, run..secuid s20," \
              " run..customer c1,run..customer c2" \
              " where f1.moneytype='0' and f1.fundseq='0'" \
              " and f2.moneytype='1' and f2.fundseq='0'" \
              " and f3.moneytype='2' and f3.fundseq='0'" \
              " and f4.moneytype='0' and f4.fundseq='2'" \
              " and f5.moneytype='0' and f5.fundseq='1'" \
              " and f6.moneytype='0' and f6.fundseq='0'" \
              " and f7.moneytype='1' and f7.fundseq='0'" \
              " and f8.moneytype='2' and f8.fundseq='0'" \
              " and f9.moneytype='0' and f9.fundseq='2'" \
              " and f10.moneytype='0' and f10.fundseq='1'" \
              " and s1.market='1' and s2.market='2' and s3.market='5'" \
              " and s4.market='9' and s5.market='A' and s6.market='D'" \
              "  and s7.market='H' and s8.market='J' and s9.market='S'" \
              " and s10.market='T' and s11.market='1' and s12.market='2'" \
              " and s13.market='5' and s14.market='9' and s15.market='A'" \
              " and s16.market='D' and s17.market='H' and s18.market='J'" \
              " and s19.market='S' and s20.market='T' and s1.creditflag='0' and s2.creditflag='0'" \
              " and s3.secuotherkind2='1' and s11.creditflag='0' and s12.creditflag='0' and s13.secuotherkind2='1'" \
              " and f1.custid=c1.custid and f2.custid=c1.custid and f3.custid=c1.custid and f4.custid=c1.custid and f5.custid=c1.custid and s1.custid=c1.custid and s2.custid=c1.custid and s3.custid=c1.custid and s4.custid=c1.custid and s5.custid=c1.custid and s6.custid=c1.custid and s7.custid=c1.custid and s8.custid=c1.custid and s9.custid=c1.custid and s10.custid=c1.custid" \
              " and f6.custid=c2.custid and f7.custid=c2.custid and f8.custid=c2.custid and f9.custid=c2.custid and f10.custid=c2.custid and s11.custid=c2.custid and s12.custid=c2.custid and s13.custid=c2.custid and s14.custid=c2.custid and s15.custid=c2.custid and s16.custid=c2.custid and s17.custid=c2.custid and s18.custid=c2.custid and s19.custid=c2.custid and s20.custid=c2.custid " \
              " and c1.custid='%s' and c2.custid='%s'" % (custid_dict['c_T'], custid_dict['c_F'])

        k = cursor.execute(sql)
        rec = k.fetchone()
        if param_list and rec:
            for i, key in enumerate(param_list):
                if rec[i]:
                    param_dict[key] = str(rec[i]).strip()

        c_str = cmdstring

        market = casename.split('-')[3][-1]
        ret, stkcode = getStkcode(market, serverid)
        if ret < 0:
            stkcode = '-1'
        c_str = c_str.replace('stkcode:' + (c_str.split('stkcode=')[1]).split(',')[0], 'stkcode=' + stkcode)
        for i, key in enumerate(param_dict.keys()):
            r_key = '@' + key + '@'
            if c_str.__contains__(r_key):
                c_str = c_str.replace(r_key, param_dict[key])

        return 0, c_str
    except:
        exc_info = cF.getExceptionInfo()
        Logging.getLog().error(exc_info)
        return -1, (exc_info,)


if __name__ == "__main__":
    cF.readConfigFile()
    ReplaceParam()
