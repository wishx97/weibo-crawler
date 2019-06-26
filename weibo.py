#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import json
import math
import random
import sys
import traceback
from collections import OrderedDict
from time import sleep

import requests
from lxml import etree
from tqdm import tqdm


class Weibo(object):
    def __init__(self, user_id, filter=0):
        """Weibo类初始化"""
        if not isinstance(user_id, int):
            sys.exit(u'user_id值应为一串数字形式,请重新输入')
        if not isinstance(filter, int):
            sys.exit(u'filter值应为数字,请重新输入')
        if filter != 0 and filter != 1:
            sys.exit(u'filter值应为0或1,请重新输入')
        self.user_id = user_id  # 用户id,即需要我们输入的数字,如昵称为"Dear-迪丽热巴"的id为1669879400
        self.filter = filter
        self.weibo = []  # 存储爬取到的所有微博信息
        self.user = {}

    def get_json(self, params):
        """获取网页中json数据"""
        url = 'https://m.weibo.cn/api/container/getIndex?'
        r = requests.get(url, params=params)
        return r.json()

    def get_weibo_json(self, page):
        """获取网页中微博json数据"""
        params = {'containerid': '107603' + str(self.user_id), 'page': page}
        js = self.get_json(params)
        return js

    def get_user_info(self):
        """获取用户信息"""
        params = {'containerid': '100505' + str(self.user_id)}
        js = self.get_json(params)
        if js['ok']:
            info = js['data']['userInfo']
            if info.get('toolbar_menus'):
                del info['toolbar_menus']
            user_info = self.standardize_info(info)
            self.user = user_info
            return user_info

    def get_long_weibo(self, id):
        """获取长微博"""
        url = 'https://m.weibo.cn/detail/%s' % id
        html = requests.get(url).text
        html = html[html.find('"status":'):]
        html = html[:html.rfind('"hotScheme"')]
        html = html[:html.rfind(',')]
        html = '{' + html + '}'
        js = json.loads(html, strict=False)
        weibo_info = js['status']
        weibo = self.parse_weibo(weibo_info)
        return weibo

    def get_pics(self, weibo_info):
        """获取微博原始图片url"""
        if weibo_info.get('pics'):
            pic_info = weibo_info['pics']
            pic_list = [pic['large']['url'] for pic in pic_info]
            pics = ','.join(pic_list)
        else:
            pics = ''
        return pics

    def get_location(self, selector):
        """获取微博发布位置"""
        location_icon = 'timeline_card_small_location_default.png'
        span_list = selector.xpath('//span')
        location = ''
        for i, span in enumerate(span_list):
            if span.xpath('img/@src'):
                if location_icon in span.xpath('img/@src')[0]:
                    location = span_list[i + 1].xpath('string(.)')
                    break
        return location

    def get_topics(self, selector):
        """获取参与的微博话题"""
        span_list = selector.xpath("//span[@class='surl-text']")
        topics = ''
        topic_list = []
        for span in span_list:
            text = span.xpath('string(.)')
            if len(text) > 2 and text[0] == '#' and text[-1] == '#':
                topic_list.append(text[1:-1])
        if topic_list:
            topics = ','.join(topic_list)
        return topics

    def get_at_users(self, selector):
        """获取@用户"""
        a_list = selector.xpath('//a')
        at_users = ''
        at_list = []
        for a in a_list:
            if '@' + a.xpath('@href')[0][3:] == a.xpath('string(.)'):
                at_list.append(a.xpath('string(.)')[1:])
        if at_list:
            at_users = ','.join(at_list)
        return at_users

    def string_to_int(self, string):
        """字符串转换为整数"""
        if isinstance(string, int):
            return string
        elif string.endswith(u'万+'):
            string = int(string[:-2] + '0000')
        elif string.endswith(u'万'):
            string = int(string[:-1] + '0000')
        return int(string)

    def standardize_info(self, weibo):
        """标准化信息，去除乱码"""
        for k, v in weibo.items():
            if 'int' not in str(type(v)) and 'long' not in str(
                    type(v)) and 'bool' not in str(type(v)):
                weibo[k] = v.replace(u"\u200b", "").encode(
                    sys.stdout.encoding, "ignore").decode(sys.stdout.encoding)
        return weibo

    def parse_weibo(self, weibo_info):
        weibo = OrderedDict()
        weibo['user_id'] = weibo_info['user']['id']
        weibo['screen_name'] = weibo_info['user']['screen_name']
        weibo['id'] = int(weibo_info['id'])
        text_body = weibo_info['text']
        selector = etree.HTML(text_body)
        weibo['text'] = etree.HTML(text_body).xpath('string(.)')
        weibo['reposts_count'] = self.string_to_int(
            weibo_info['reposts_count'])
        weibo['comments_count'] = self.string_to_int(
            weibo_info['comments_count'])
        weibo['attitudes_count'] = self.string_to_int(
            weibo_info['attitudes_count'])
        weibo['source'] = weibo_info['source']
        weibo['created_at'] = weibo_info['created_at']
        weibo['pics'] = self.get_pics(weibo_info)
        weibo['location'] = self.get_location(selector)
        weibo['at_users'] = self.get_at_users(selector)
        weibo['topics'] = self.get_topics(selector)
        return self.standardize_info(weibo)

    def print_user_info(self):
        """打印用户信息"""
        print('+' * 100)
        print(u'用户信息')
        print(u'用户id：%d' % self.user['id'])
        print(u'用户昵称：%s' % self.user['screen_name'])
        gender = u'女' if self.user['gender'] == 'f' else u'男'
        print(u'性别：%s' % gender)
        print(u'微博数：%d' % self.user['statuses_count'])
        print(u'粉丝数：%d' % self.user['followers_count'])
        print(u'关注数：%d' % self.user['follow_count'])
        if self.user.get('verified_reason'):
            print(self.user['verified_reason'])
        print(self.user['description'])
        print('+' * 100)

    def print_one_weibo(self, weibo):
        """打印一条微博"""
        print(u'用户id：%d' % weibo['user_id'])
        print(u'用户昵称：%s' % weibo['screen_name'])
        print(u'微博id：%d' % weibo['id'])
        print(u'微博正文：%s' % weibo['text'])
        print(u'原始图片url：%s' % weibo['pics'])
        print(u'微博位置：%s' % weibo['location'])
        print(u'发布时间：%s' % weibo['created_at'])
        print(u'发布工具：%s' % weibo['source'])
        print(u'点赞数：%d' % weibo['attitudes_count'])
        print(u'评论数：%d' % weibo['comments_count'])
        print(u'转发数：%d' % weibo['reposts_count'])
        print(u'话题：%s' % weibo['topics'])
        print(u'@用户：%s' % weibo['at_users'])

    def print_weibo(self, weibo):
        """打印微博，若为转发微博，会同时打印原创和转发部分"""
        if weibo.get('retweet'):
            print('*' * 100)
            print(u'转发部分：')
            self.print_one_weibo(weibo['retweet'])
            print('*' * 100)
            print(u'原创部分：')
        self.print_one_weibo(weibo)
        print('-' * 120)

    def get_one_weibo(self, info):
        """获取一条微博的全部信息"""
        weibo_info = info['mblog']
        weibo_id = weibo_info['id']
        retweeted_status = weibo_info.get('retweeted_status')
        is_long = weibo_info['isLongText']
        if retweeted_status:  # 转发
            retweet_id = retweeted_status['id']
            is_long_retweet = retweeted_status['isLongText']
            if is_long:
                weibo = self.get_long_weibo(weibo_id)
            else:
                weibo = self.parse_weibo(weibo_info)
            if is_long_retweet:
                retweet = self.get_long_weibo(retweet_id)
            else:
                retweet = self.parse_weibo(retweeted_status)
            weibo['retweet'] = retweet
        else:  # 原创
            if is_long:
                weibo = self.get_long_weibo(weibo_id)
            else:
                weibo = self.parse_weibo(weibo_info)
        return weibo

    def get_one_page(self, page):
        """获取一页的全部微博"""
        try:
            js = self.get_weibo_json(page)
            if js['ok']:
                weibos = js['data']['cards']
                for w in weibos:
                    if w['card_type'] == 9:
                        wb = self.get_one_weibo(w)
                        if (not self.filter) or ('retweet' not in wb.keys()):
                            self.weibo.append(wb)
                            self.print_weibo(wb)
        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    def get_page_count(self):
        """获取微博页数"""
        weibo_count = self.user['statuses_count']
        page_count = int(math.ceil(weibo_count / 10.0))
        return page_count

    def get_pages(self):
        """获取全部微博"""
        self.get_user_info()
        page_count = self.get_page_count()
        self.print_user_info()
        page1 = 0
        random_pages = random.randint(1, 5)
        for page in tqdm(range(1, page_count + 1), desc=u"进度"):
            print(u'第%d页' % page)
            self.get_one_page(page)

            # 通过加入随机等待避免被限制。爬虫速度过快容易被系统限制(一段时间后限
            # 制会自动解除)，加入随机等待模拟人的操作，可降低被系统限制的风险。默
            # 认是每爬取1到5页随机等待6到10秒，如果仍然被限，可适当增加sleep时间
            if page - page1 == random_pages and page < page_count:
                sleep(random.randint(6, 10))
                page1 = page
                random_pages = random.randint(1, 5)


def main():
    try:
        user_id = 1669879400  # 可以改成任意合法的用户id（爬虫的微博id除外）
        filter = 1  # 值为0表示爬取全部微博（原创微博+转发微博），值为1表示只爬取原创微博
        wb = Weibo(user_id, filter)
        wb.get_pages()
    except Exception as e:
        print('Error: ', e)
        traceback.print_exc()


if __name__ == '__main__':
    main()