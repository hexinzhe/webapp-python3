import os
import uuid

import pytest
import time

from www import orm
from www.orm import Model, StringField


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):
    __table__ = 'users'
    id = StringField(primary_key=True, default=next_id, map_type='varchar(50)')
    name = StringField()


# @pytest.fixture(scope='module')
# def event_loop():
#     loop = asyncio.get_event_loop()
#     yield loop
#     loop.close()


@pytest.fixture
def table(event_loop):
    async def create_pool():
        # 创建连接池
        await orm.create_pool(event_loop, user='root', password='123', db='awesome')

    def create_table():
        sql = 'test.sql'
        usr = 'root'
        passwd = '123'
        sql = 'mysql -u%s -p%s < %s' % (usr, passwd, sql)
        os.system('mysql -u%s -p%s < %s' % (usr, passwd, sql))

    # 使用SQL语句创建库和表
    create_table()
    event_loop.run_until_complete(create_pool())
    yield
    # 关闭连接池
    event_loop.run_until_complete(orm.close_pool())


# 测试getValueDefault
def test_get_value_default():
    pass


# 测试创建（插入表）
@pytest.mark.asyncio
@pytest.mark.usefixtures('table')
async def test_insert():
    user = User(name='hexinzhe')
    await user.save()


@pytest.mark.asyncio
@pytest.mark.usefixtures('table')
async def test_delete():
    user = User(name='hexinzhe')
    await user.save()
    print(user)
    await user.remove()


@pytest.mark.asyncio
@pytest.mark.usefixtures('table')
async def test_find():
    user = User(name='hexinzhe')
    await user.save()
    print(user)
    user = User(name='shaniu', id='123')
    await user.save()
    print(user)

    # 查找
    users = await User.findAll()
    print(users)

    count = await User.findNumber('count(*)')
    print(count)

    user = await User.find('123')
    print(user)


@pytest.mark.asyncio
@pytest.mark.usefixtures('table')
async def test_update():
    user = User(name='hexinzhe')
    await user.save()
    print(user)

    user.name = 'shaniu'
    await user.update()
    user = await User.findAll('name=?',['shaniu'])
    print(user)
