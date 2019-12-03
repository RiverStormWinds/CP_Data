# coding:utf-8

import os
import re
import chardet

def flush_script(allFile):
    for file in allFile:
        file_str = re.split('\.', file)
        if file_str[-1] == 'py' and file_str[0] != 'flush_script':  # 抽取所有的py文件
            with open(file, 'r', encoding='gbk') as f:
                print(f.readline())


if __name__ == '__main__':
    allFile = os.listdir(os.getcwd())
    flush_script(allFile)




