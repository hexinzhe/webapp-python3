import uuid

import pytest
import time

from orm import Model, StringField


class User(Model):
    id = StringField(primary_key=True, default=next_id, map_type='varchar(50)')
    name = StringField()


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


# 测试getValueDefault
def test_get_value_default():
    pass

# 测试创建（插入表）
async def test_insert():
    user = User('hexinzhe')
