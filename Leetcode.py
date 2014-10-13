#!/usr/bin/env python
#coding=utf-8

import os
import re
import requests
import datetime
import BeautifulSoup

#url requests setting
host_url                = 'https://oj.leetcode.com'
login_url               = 'https://oj.leetcode.com/accounts/login/'
question_list_url       = 'https://oj.leetcode.com/problems/'
code_base_url           = 'https://oj.leetcode.com/submissions/detail/%s/'
code_list_base_url      = 'https://oj.leetcode.com/submissions/%d/'
github_login_url        = 'https://oj.leetcode.com/accounts/github/login/'
code_regex              = re.compile("storage\.put\('(python|cpp|java)', '([^']+)'\);")
leetcode_request_header = {
    'Host': 'oj.leetcode.com',
    'Origin': 'https://oj.leetcode.com',
    'Referer': 'https://oj.leetcode.com/accounts/login/'
}
github_request_header   = {
    'Host': 'github.com',
    'Origin': 'https://github.com',
    'Referer': 'https://github.com/'
}

#code setting
ext_dic = {'python': '.py', 'cpp': '.cpp', 'java': '.java'}
comment_char_dic = {'python': '#', 'cpp': '//', 'java': '//'}


class LeetcodeDownloader(object):
    def __init__(self, proxies=None, code_path='codes/', output_encoding='utf-8', session=None):
        self.proxies = proxies or {}
        self.code_path = code_path
        self.output_encoding = output_encoding
        self.session = session or requests.Session()
        self.session.proxies = self.proxies
        self.username = self.password = ''

    def login(self, username, password):
        self.username = username
        self.password = password
        login_page = self.session.get(login_url)
        soup = BeautifulSoup.BeautifulSoup(login_page.text)
        secret_input = soup.find('form').find('input', type='hidden')
        payload = dict(
            login=self.username,
            password=self.password,
        )
        payload[secret_input['name']] = secret_input['value']
        self.session.post(login_url, data=payload, headers=leetcode_request_header)
        return self.is_logged_in

    @property
    def is_logged_in(self):
        return bool(self.session.cookies.get("PHPSESSID", None))

    def login_from_github(self, username, password):
        self.username = username
        self.password = password
        leetcode_github_login_page = self.session.get('https://github.com/login')
        soup = BeautifulSoup.BeautifulSoup(leetcode_github_login_page.text)
        post_div = soup.find('div', id='login')
        github_post_url = 'https://github.com/session'
        payload = dict()
        for ip in post_div.findAll('input'):
            value = ip.get('value', None)
            if value:
                payload[ip['name']] = value
        payload['login'], payload['password'] = username, password
        self.session.post(github_post_url, data=payload, headers=github_request_header)
        if self.session.cookies['logged_in'] != 'yes':
            return False
        rsp = self.session.get(github_login_url)
        return rsp.status_code == 200

    def get_questions(self):
        rsp = self.session.get(question_list_url)
        soup = BeautifulSoup.BeautifulSoup(rsp.text)
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

    def get_question_description(self, url):
        rsp = self.session.get(url)
        soup = BeautifulSoup.BeautifulSoup(rsp.text)
        name = soup.find("h3").text
        accepted_count = int(soup.find("span", attrs={"class": "total-ac text-info"}).find("strong").text)
        submission_count = int(soup.find("span", attrs={"class": "total-submit text-info"}).find("strong").text)

        def transform(div):
            lst = []
            for item in div:
                if isinstance(item, BeautifulSoup.NavigableString):
                    lst.append(item)
                elif isinstance(item, BeautifulSoup.Tag):
                    if item.name == "p":
                        lst.append("%s\n" % transform(item))
                    elif item.name == "b":
                        lst.append("###%s###" % transform(item))
                    elif item.name == "a":
                        lst.append("[%s](%s)" % (transform(item), item["href"]))
                    elif item.name == "code":
                        lst.append("`%s`" % transform(item))
                    elif item.name == "pre":
                        lst.append("```%s```" % transform(item))
                    elif item.name == "ul":
                        lst.append(transform(item))
                    elif item.name == "div":
                        lst.append(transform(item))
                    elif item.name == "li":
                        lst.append("* %s" % transform(item))
                    elif item.name == "br":
                        lst.append("\n")
                    else:
                        lst.append(item.text)
            return "".join(lst)
        description = transform(soup.find("div", attrs={"class": "question-content"}))

        return {
            'name': name,
            'accepted_count': accepted_count,
            'submission_count': submission_count,
            'description': description.replace("\r", "")
        }

    def code(self, code_id):
        code_url = code_base_url % code_id
        rsp = self.session.get(code_url)
        match = code_regex.search(rsp.text)
        return match.group(2).decode('raw_unicode_escape')

    def page_code(self, page_index=0):
        code_url = code_list_base_url % page_index
        rsp = self.session.get(code_url)
        soup = BeautifulSoup.BeautifulSoup(rsp.text)
        table = soup.find('table', id='result_testcases')
        if table is None:
            return []
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
            description = self.get_question_description(table_data_list['questions_url'])
            with open(file_full_name, 'w') as file_handle:
                file_handle.write(comment_char + 'Author     : %s\n' % self.username)
                file_handle.write(comment_char + 'Question   : %s\n' % table_data_list['name'])
                file_handle.write(comment_char + 'Link       : %s\n' % table_data_list['questions_url'])
                file_handle.write(comment_char + 'Language   : %s\n' % table_data_list['lang'])
                file_handle.write(comment_char + 'Status     : %s\n' % table_data_list['status'])
                file_handle.write(comment_char + 'Run Time   : %s\n' % table_data_list['runtime'])
                file_handle.write(comment_char + 'Description: \n')
                for line in description["description"].split("\n"):
                    if line.strip():
                        file_handle.write(comment_char)
                        file_handle.write(line.encode(self.output_encoding))
                        file_handle.write("\n")
                file_handle.write('\n')
                file_handle.write(comment_char + 'Code       : \n')
                file_handle.write(self.code(table_data_list['code_id'])
                                  .encode(self.output_encoding)
                                  .replace('\r', ''))
        return file_full_name

    def get_and_save_all_codes(self):
        for table_data_list in self.page_code_all():
            result = dict(table_data_list)
            result['path'] = self.save_code(table_data_list)
            yield result


if __name__ == '__main__':
    #login form leetcode account
    USERNAME = 'YOUR USERNAME'
    PASSWORD = 'YOUR PASSWORD'
    #login form github account
    #downloader.login_from_github(username='YOUR USERNAME', password='YOUR PASSWORD')

    from taskbar import TaskBar

    downloader = LeetcodeDownloader()
    print "Logging..."
    if downloader.login(username=USERNAME, password=PASSWORD):
        print "ok, logged in."
    else:
        print "error, logging failed."
        exit()

    def func(row):
        result = dict(row)
        result['path'] = downloader.save_code(row)
        return result

    task_bar = TaskBar(40)
    print "Loading submissions..."
    task_param_list = list((func, ([table_data_list], {})) for table_data_list in downloader.page_code_all())
    print "Downloading submissions..."
    task_bar.do_task(task_param_list)
