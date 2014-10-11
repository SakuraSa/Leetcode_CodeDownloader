#!/usr/bin/env python
#coding=utf-8

import os
import re
import time
import requests
import datetime
from BeautifulSoup import BeautifulSoup

#url requests setting
host_url           = 'https://oj.leetcode.com'
login_url          = 'https://oj.leetcode.com/accounts/login/'
question_list_url  = 'https://oj.leetcode.com/problems/'
code_base_url      = 'https://oj.leetcode.com/submissions/detail/%s/'
code_list_base_url = 'https://oj.leetcode.com/submissions/%d/'
code_regex         = re.compile("storage\.put\('(python|cpp|java)', '([^']+)'\);")
request_header     = {
    'Host': 'oj.leetcode.com',
    'Origin': 'https://oj.leetcode.com',
    'Referer': 'https://oj.leetcode.com/accounts/login/'
}

#code setting
ext_dic = {'python': '.py', 'cpp': '.cpp', 'java': '.java'}
comment_char_dic = {'python': '#', 'cpp': '//', 'java': '//'}


class LeetcodeDownloader(object):
    def __init__(self, username, password, proxies=None, code_path='codes/', output_encoding='utf-8'):
        self.username = username
        self.password = password
        self.proxies = proxies or {}
        self.code_path = code_path
        self.output_encoding = output_encoding
        self.session = requests.Session()
        if not self.login():
            raise Exception('Error: %s logging failed.' % self.username)

    def login(self):
        login_page = self.session.get(login_url, proxies=self.proxies)
        soup = BeautifulSoup(login_page.text)
        secret_input = soup.find('form').find('input', type='hidden')
        payload = dict(
            login=self.username,
            password=self.password,
        )
        payload[secret_input['name']] = secret_input['value']
        rsp = self.session.post(login_url, proxies=self.proxies, data=payload, headers=request_header)
        return rsp.status_code == 200

    def get_questions(self):
        rsp = self.session.get(question_list_url, proxies=self.proxies)
        soup = BeautifulSoup(rsp.text)
        question_table = soup.find('table', id='problemList')
        question_table_body = question_table.find('tbody')
        for table_row in question_table_body.findAll('tr'):
            table_data = table_row.findAll('td')
            status = table_data[0].find('span')['class']
            name = table_data[1].find('a').text
            url = table_data[1].find('a')['href']
            date = datetime.datetime.strptime(table_data[2].text, '%Y-%m-%d')
            per = float(table_data[3].text.strip('%'))
            yield dict(
                status=status,
                name=name,
                url=url,
                date=date,
                per=per
            )

    def code(self, code_id):
        code_url = code_base_url % code_id
        rsp = self.session.get(code_url, proxies=self.proxies)
        match = code_regex.search(rsp.text)
        return match.group(2).decode('raw_unicode_escape')

    def page_code(self, page_index=0):
        code_url = code_list_base_url % page_index
        rsp = self.session.get(code_url, proxies=self.proxies)
        soup = BeautifulSoup(rsp.text)
        table = soup.find('table', id='result_testcases')
        if table is None:
            return
        table_body = table.find('tbody')
        number_reg = re.compile('\d+')
        lst = list()
        for table_row in table_body.findAll('tr'):
            table_data = table_row.findAll('td')
            name = table_data[1].find('a').text
            questions_url = host_url + table_data[1].find('a')['href']
            status = table_data[2].find('strong').text
            code_id = int(number_reg.search(table_data[2].find('a')['href']).group(0))
            runtime = table_data[3].text.strip()
            lang = table_data[4].text
            lst.append(dict(
                name=name,
                questions_url=questions_url,
                status=status,
                code_id=code_id,
                runtime=runtime,
                lang=lang
            ))
        return lst

    def page_code_all(self):
        page_index = 0
        while 1:
            lst = self.page_code(page_index)
            if lst:
                for data in lst:
                    yield data
            else:
                break
            page_index += 1

    def save_code(self, table_data_list):
        file_path = os.path.join(self.code_path, table_data_list['name'])
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        file_name = "%s-%s" % (table_data_list['status'], table_data_list['code_id'])
        file_ext  = ext_dic.get(table_data_list['lang'], '.txt')
        file_full_name = os.path.join(file_path, file_name + file_ext)
        if not os.path.exists(file_full_name):
            comment_char = comment_char_dic.get(table_data_list['lang'], '//')
            with open(file_full_name, 'w') as file_handle:
                file_handle.write(comment_char + 'Author  : %s\n' % self.username)
                file_handle.write(comment_char + 'Question: %s\n' % table_data_list['name'])
                file_handle.write(comment_char + 'Link    : %s\n' % table_data_list['questions_url'])
                file_handle.write(comment_char + 'Language: %s\n' % table_data_list['lang'])
                file_handle.write(comment_char + 'Status  : %s\n' % table_data_list['status'])
                file_handle.write(comment_char + 'Run Time: %s\n' % table_data_list['runtime'])
                file_handle.write('\n')
                file_handle.write(self.code(table_data_list['code_id']).encode(self.output_encoding))
        return file_full_name

    def get_and_save_all_codes(self):
        for table_data_list in self.page_code_all():
            result = dict(table_data_list)
            result['path'] = self.save_code(table_data_list)
            yield result

if __name__ == '__main__':
    downloader = LeetcodeDownloader(username='YOUR USERNAME', password='YOUR PASSWORD')

    start_time = time.time()
    print ''
    print 'Index'.rjust(6), 'Status'.rjust(30), 'Lang'.rjust(6), 'Questions'
    for index, row in enumerate(downloader.get_and_save_all_codes()):
        print '%6d' % index, '%30s' % row['status'], '%6s' % row['lang'], row['name']
    print ''

    cost_time = time.time() - start_time

    print 'complete in %.2fs' % cost_time
