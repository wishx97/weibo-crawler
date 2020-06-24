from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, BooleanAttribute, UTCDateTimeAttribute

from weibo import get_config

config = get_config()

class UserModel(Model):
    """
    A DynamoDB User
    """
    class Meta:
        table_name = "weibo-user"
        aws_access_key_id = config['aws_access_key_id']
        aws_secret_access_key = config['aws_secret_access_key']

    id  = UnicodeAttribute(hash_key=True)
    screen_name  = UnicodeAttribute(null=True)
    gender  = UnicodeAttribute(null=True)
    statuses_count  = NumberAttribute(null=True)
    followers_count  = NumberAttribute(null=True)
    follow_count  = NumberAttribute(null=True)
    registration_time = UnicodeAttribute(null=True)
    sunshine = UnicodeAttribute(null=True)
    birthday = UnicodeAttribute(null=True)
    location = UnicodeAttribute(null=True)
    education = UnicodeAttribute(null=True)
    company = UnicodeAttribute(null=True)
    description  = UnicodeAttribute(null=True)
    profile_url  = UnicodeAttribute(null=True)
    profile_image_url = UnicodeAttribute(null=True)
    avatar_hd  = UnicodeAttribute(null=True)
    urank  = NumberAttribute(null=True)
    mbrank  = NumberAttribute(null=True)
    verified  = BooleanAttribute(null=True)
    verified_type  = NumberAttribute(null=True)
    verified_reason  = UnicodeAttribute(null=True)


class WeiboModel(Model):
    class Meta:
        table_name = "weibo-post"
        aws_access_key_id = config['aws_access_key_id']
        aws_secret_access_key = config['aws_secret_access_key']

    id  = NumberAttribute(hash_key=True)
    bid  = UnicodeAttribute(range_key=True)
    user_id  = NumberAttribute(null=True)
    screen_name  = UnicodeAttribute(null=True)
    text  = UnicodeAttribute(null=True)
    article_url = UnicodeAttribute(null=True)
    topics  = UnicodeAttribute(null=True)
    at_users  = UnicodeAttribute(null=True)
    pics  = UnicodeAttribute(null=True)
    video_url  = UnicodeAttribute(null=True)
    location  = UnicodeAttribute(null=True)
    created_at  = UnicodeAttribute(null=True)
    source  = UnicodeAttribute(null=True)
    attitudes_count  = NumberAttribute(null=True)
    comments_count  = NumberAttribute(null=True)
    reposts_count  = NumberAttribute(null=True)
    