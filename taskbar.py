#!/usr/bin/env python
#coding=utf-8

__author__ = 'Rnd495'

import sys
import time
import thread


class TaskBar(object):
    def __init__(self, bar_length=20):
        object.__init__(self)
        self.out = sys.stdout
        self.bar_length = max(bar_length, 9)
        self.time_cost = 0.0
        self.spt = 0.0
        self.running = False
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.finish()

    def finish(self):
        self.out.write("\r\n")

    def line(self, text):
        self.out.write("\r%s\r" % text)

    def show(self, percent=1.0, description=""):
        buf = ['[']
        mark_flag = False
        for buf_index in range(self.bar_length - 2):
            bar_per = buf_index / float(self.bar_length - 2)
            if bar_per <= percent:
                buf.append('=')
            else:
                buf.append(' ' if mark_flag else '>')
                mark_flag = True
        buf.append(']')
        per_text = "%.1f%%" % (percent * 100)
        index_start = (len(buf) - len(per_text)) / 2
        for index, char in enumerate(per_text):
            if char != ' ':
                buf[index + index_start] = char
        buf.append(description)
        self.line(''.join(buf))

    def do_task(self, task_params_list, show_total=True):
        start_time = time.time()
        count = len(task_params_list)
        result_list = []
        for index, (task, (args, kwargs)) in enumerate(task_params_list):
            time_cost = time.time() - start_time
            esp_time = 0.0
            spt = 0.0
            if index > 0 and time_cost > 0.01:
                esp_time = time_cost / index * count
                spt = index / time_cost
            self.show(index / float(count),
                      " [%d/%d] %.1fs/%.1fs %.2fspt" % (index + 1, count, time_cost, esp_time, spt))
            result_list.append(task(*args, **kwargs))
        self.time_cost = time_cost = time.time() - start_time
        self.spt = spt = count / time_cost
        self.show(1.0, " [%d/%d] %.1fs/%.1fs %.2fspt" % (count, count, time_cost, time_cost, spt))
        self.finish()
        if show_total:
            print "Total %d Tasks complete in %.2fs with %.2fspt" % (count, time_cost, spt)
        return result_list

    def processing(self, task, title="", show_total=True, *args, **kwargs):
        start_time = time.time()
        self.running = True
        self.value = None

        def func(*args, **kwargs):
            self.value = task(*args, **kwargs)
            self.running = False

        thread.start_new_thread(func, args, kwargs)
        cursor = "<%s>" % ("=" * max(self.bar_length / 3 - 2, 1))
        cursor_index = -len(cursor)
        while self.running:
            self.time_cost = time.time() - start_time
            buf = ['[']
            for buf_index in range(self.bar_length - 2):
                if cursor_index <= buf_index < cursor_index + len(cursor):
                    buf.append(cursor[buf_index - cursor_index])
                else:
                    buf.append(" ")
            buf.append(']')
            cursor_index = (cursor_index + 1 + len(cursor)) % (self.bar_length - 2 + 2 * len(cursor)) - len(cursor)

            per_text = "%.2fs" % self.time_cost
            index_start = (len(buf) - len(per_text)) / 2
            for index, char in enumerate(per_text):
                if char != ' ':
                    buf[index + index_start] = char
            buf.append(title)
            self.line(''.join(buf))
            time.sleep(0.05)
        self.finish()
        if show_total:
            print "Task complete in %.2fs" % self.time_cost
        return self.value


if __name__ == '__main__':
    tb = TaskBar(100)
    tb.do_task([(time.sleep, ([0.01], {})) for i in range(100)])
    tb.processing(lambda: time.sleep(3))
