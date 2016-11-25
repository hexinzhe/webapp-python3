import time, uuid

from .orm import Model, StringField, BooleanField, FloatField, TextField


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, map_type='varchar(50)')
    email = StringField(map_type='varchar(50)')
    passwd = StringField(map_type='varchar(50)')
    admin = BooleanField()
    name = StringField(map_type='varchar(50)')
    image = StringField(map_type='varchar(500)')
    created_at = FloatField(default=time.time)


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, map_type='varchar(50)')
    user_id = StringField(map_type='varchar(50)')
    user_name = StringField(map_type='varchar(50)')
    user_image = StringField(map_type='varchar(500)')
    name = StringField(map_type='varchar(50)')
    summary = StringField(map_type='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)


class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, map_type='varchar(50)')
    blog_id = StringField(map_type='varchar(50)')
    user_id = StringField(map_type='varchar(50)')
    user_name = StringField(map_type='varchar(50)')
    user_image = StringField(map_type='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)


# 注意 Page 是一个普通类
class Page(object):
    '''
    Page object for display pages.
    '''
    def __init__(self, item_count, page_index=1, page_size=10):
        '''
        Init Pagination by item_count, page_index and page_size
        '''
        # blog 个数
        self.item_count = item_count
        # 每页显示的 blog 个数
        self.page_size = page_size
        # 算出 page 总个数
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        # 没有 blog 或请求的页面不存在
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s,' \
               ' page_size, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index,
                                                      self.page_size, self.offset, self.limit)