import os
import time
import sys
import copy
import traceback
import requests
from requests.adapters import HTTPAdapter

from model import UserModel, WeiboModel
from weibo import Weibo, get_config
from gdrive import initial_gdrive


class WeiboCrawler(Weibo):
    def __init__(self, config):
        self.drive = initial_gdrive()
        self.gdrive_root = config['gdrive_root']
        self.gdrive_id = ''
        self.object_id = ''
        self.gdrive_files = []
        super().__init__(config)


    def validate_config(self, config):
        """验证配置是否正确"""

        # 验证filter、original_pic_download、retweet_pic_download、original_video_download、retweet_video_download
        argument_list = [
            'filter', 'original_pic_download', 'retweet_pic_download',
            'original_video_download', 'retweet_video_download'
        ]
        for argument in argument_list:
            if config[argument] != 0 and config[argument] != 1:
                sys.exit(u'%s值应为0或1,请重新输入' % config[argument])

        # 验证since_date
        since_date = str(config['since_date'])
        if (not self.is_date(since_date)) and (not since_date.isdigit()):
            sys.exit(u'since_date值应为yyyy-mm-dd形式或整数,请重新输入')

        # 验证write_mode
        write_mode = ['csv', 'json', 'mongo', 'mysql', 'dynamo']
        if not isinstance(config['write_mode'], list):
            sys.exit(u'write_mode值应为list类型')
        for mode in config['write_mode']:
            if mode not in write_mode:
                sys.exit(
                    u'%s为无效模式，请从csv、json、mongo、dynamo和mysql中挑选一个或多个作为write_mode' %
                    mode)

        # 验证user_id_list
        user_id_list = config['user_id_list']
        if (not isinstance(user_id_list,
                           list)) and (not user_id_list.endswith('.txt')):
            sys.exit(u'user_id_list值应为list类型或txt文件路径')
        if not isinstance(user_id_list, list):
            if not os.path.isabs(user_id_list):
                user_id_list = os.path.split(
                    os.path.realpath(__file__))[0] + os.sep + user_id_list
            if not os.path.isfile(user_id_list):
                sys.exit(u'不存在%s文件' % user_id_list)

    
    def user_to_dynamodb(self):
        UserModel.create_table(read_capacity_units=1, write_capacity_units=1)
        user = UserModel(self.user['id'])
        user.screen_name  = self.user['screen_name']
        user.gender  = self.user['gender']
        user.statuses_count  = self.user['statuses_count']
        user.followers_count  = self.user['followers_count']
        user.follow_count  = self.user['follow_count']
        user.registration_time = self.user['registration_time']
        user.sunshine = self.user['sunshine']
        user.birthday = self.user['birthday']
        user.location = self.user['location']
        user.education = self.user['education']
        user.company = self.user['company']
        user.description  = self.user['description']
        user.profile_url  = self.user['profile_url']
        user.profile_image_url  = self.user['profile_image_url']
        user.avatar_hd  = self.user['avatar_hd']
        user.urank  = self.user['urank']
        user.mbrank  = self.user['mbrank']
        user.verified  = self.user['verified']
        user.verified_type  = self.user['verified_type']
        user.verified_reason  = self.user['verified_reason']
        user.save()


    def user_to_database(self):
        if 'csv' in self.write_mode:
            self.user_to_csv()
        if 'mysql' in self.write_mode:
            self.user_to_mysql()
        if 'mongo' in self.write_mode:
            self.user_to_mongodb()
        if 'dynamo' in self.write_mode:
            self.user_to_dynamodb()


    def get_user_info(self):
        user = super().get_user_info()
        self.gdrive_id = self.create_gdrive_directory(self.gdrive_root, user['screen_name'])


    def download_one_file(self, url, file_path, type1, weibo_id, gdrive_saved_id, file_name):
        """下载单个文件(图片/视频)"""
        try:
            if not self.gdrive_files:
                file_list = self.drive.ListFile({'q':"'{}' in parents and trashed=False".format(gdrive_saved_id)}).GetList()
                for file in file_list:
                    self.gdrive_files.append(file['title'])
            if file_name not in self.gdrive_files:
                file1 = self.drive.CreateFile({"parents": [{"kind": "drive#fileLink", "id": gdrive_saved_id}], 'title': file_name})
                s = requests.Session()
                s.mount(url, HTTPAdapter(max_retries=5))
                downloaded = s.get(url, cookies=self.cookie, timeout=(5, 10))
                file1.SetContentBytes(downloaded.content, file_name)
                file1.Upload()
                    

        except Exception as e:
            error_file = self.get_filepath(
                type1) + os.sep + 'not_downloaded.txt'
            with open(error_file, 'ab') as f:
                url = str(weibo_id) + ':' + url + '\n'
                f.write(url.encode(sys.stdout.encoding))
            print('Error: ', e)
            traceback.print_exc()


    def create_gdrive_directory(self, parents, title):
        '''
            Create a new Google Drive directory.
        '''
        try:
            f = self.drive.ListFile({"q": "'{}' in parents and trashed=false and "
                                          "mimeType='application/vnd.google-apps.folder' and "
                                          "title='{}'".format(parents, title)}).GetList()
            if len(f) > 0:
                return f[0]['id']
            folder_metadata = {
                'parents': [{'id': parents}],
                'title': title,
                # The mimetype defines this new file as a folder, so don't change this.
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.drive.CreateFile(folder_metadata)
            folder.Upload()
            return folder['id']
        except Exception as e:
            time.sleep(10)
            return self.create_gdrive_directory(parents, title)


    def handle_download(self, file_type, file_dir, urls, w):
        """处理下载相关操作"""
        file_prefix = w['created_at'][:11].replace('-', '') + '_' + str(
            w['id'])
        gdrive_saved_id = self.create_gdrive_directory(self.gdrive_id, file_type)
        if file_type == 'img': 
            if ',' in urls:
                url_list = urls.split(',')
                for i, url in enumerate(url_list):
                    index = url.rfind('.')
                    if len(url) - index >= 5:
                        file_suffix = '.jpg'
                    else:
                        file_suffix = url[index:]
                    file_name = file_prefix + '_' + str(i + 1) + file_suffix
                    file_path = file_dir + os.sep + file_name
                    self.download_one_file(url, file_path, file_type, w['id'], gdrive_saved_id, file_name)
            else:
                index = urls.rfind('.')
                if len(urls) - index > 5:
                    file_suffix = '.jpg'
                else:
                    file_suffix = urls[index:]
                file_name = file_prefix + file_suffix
                file_path = file_dir + os.sep + file_name
                self.download_one_file(urls, file_path, file_type, w['id'], gdrive_saved_id, file_name)
        else:
            file_suffix = '.mp4'
            if ';' in urls:
                url_list = urls.split(';')
                if url_list[0].endswith('.mov'):
                    file_suffix = '.mov'
                for i, url in enumerate(url_list):
                    file_name = file_prefix + '_' + str(i + 1) + file_suffix
                    file_path = file_dir + os.sep + file_name
                    self.download_one_file(url, file_path, file_type, w['id'], gdrive_saved_id, file_name)
            else:
                if urls.endswith('.mov'):
                    file_suffix = '.mov'
                file_name = file_prefix + file_suffix
                file_path = file_dir + os.sep + file_name
                self.download_one_file(urls, file_path, file_type, w['id'], gdrive_saved_id, file_name)


    def info_to_dynamodb(self, collection, info_list):
        WeiboModel.create_table(read_capacity_units=10, write_capacity_units=10)
        if len(self.write_mode) > 1:
            new_info_list = copy.deepcopy(info_list)
        else:
            new_info_list = info_list
        for info in new_info_list:
            weibo = WeiboModel(info['id'], info['bid'])
            weibo.user_id  = info['user_id']
            weibo.screen_name  = info['screen_name']
            weibo.text  = info['text']
            weibo.article_url = info['article_url']
            weibo.topics  = info['topics']
            weibo.at_users  = info['at_users']
            weibo.pics  = info['pics']
            weibo.video_url  = info['video_url']
            weibo.location  = info['location']
            weibo.created_at  = info['created_at']
            weibo.source  = info['source']
            weibo.attitudes_count  = info['attitudes_count']
            weibo.comments_count  = info['comments_count']
            weibo.reposts_count  = info['reposts_count']
            weibo.save()


    def weibo_to_dynamodb(self, wrote_count):
        """将爬取的微博信息写入DynamoDB数据库"""
        self.info_to_dynamodb('weibo', self.weibo[wrote_count:])
        print(u'%d条微博写入DynamoDB数据库完毕' % self.got_count)


    def write_data(self, wrote_count):
        if self.got_count > wrote_count:
            if 'csv' in self.write_mode:
                self.write_csv(wrote_count)
            if 'json' in self.write_mode:
                self.write_json(wrote_count)
            if 'mysql' in self.write_mode:
                self.weibo_to_mysql(wrote_count)
            if 'mongo' in self.write_mode:
                self.weibo_to_mongodb(wrote_count)
            if 'dynamo' in self.write_mode:
                self.weibo_to_dynamodb(wrote_count)
            if self.original_pic_download:
                self.gdrive_files = []
                self.download_files('img', 'original', wrote_count)
            if self.original_video_download:
                self.gdrive_files = []
                self.download_files('video', 'original', wrote_count)
            if not self.filter:
                if self.retweet_pic_download:
                    self.download_files('img', 'retweet', wrote_count)
                if self.retweet_video_download:
                    self.download_files('video', 'retweet', wrote_count)


def main():
    try:
        config = get_config()
        wb = WeiboCrawler(config)
        wb.start()  # 爬取微博信息
    except Exception as e:
        print('Error: ', e)
        traceback.print_exc()


if __name__ == '__main__':
    main()
