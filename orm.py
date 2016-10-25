import logging; logging.basicConfig(level=logging.INFO)
import aiomysql


class Model(dict):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mapings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)

        return value

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)


# ORM中最重要的东西，元类。创建类对象的类，可谓之类中之类
class ModelMetaclass(type):
    # 四个参数依次是cls：类的对象（type类型），name：类名，bases：基类（数组类型），attrs：类中所有属性和方法
    def __new__(cls, name, bases, attrs):
        # 排除Model类本身,只处理用户自定义类
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        # 获取table名.如果没定义__table__属性，则默认使用类名
        tableName = attrs.get('__table__', name)
        logging.info('found model: %s (table: %s)' % (name, tableName))

        # 获取所有的Field和主键名
        mappings = dict()
        fields = []
        primaryKey = None

        # 迭代所有属性和方法，保存所有Field属性和主键，用于SQL语句的映射
        # 在这里，k 是属性名或方法名，v 是 k 所代表的对象
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                # 此处的 v 是Field对象
                mappings[k] = v

                # 查找主键
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        # 如果已经存在一个主键
                        raise RuntimeError('Duplicate primary key for field: %s' % k)

                    # 否则将 k 赋给primaryKey
                    primaryKey = k
                else:
                    # 如果不是主键，则将其加进数组，这里保存key，用于SQL语句
                    fields.append(k)

        # 迭代完成，如果没有找到主键
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        # 黑魔法，删掉所有的Field类属性，为了避免属性冲突。它们定义映射关系的目的已经在上面完成了，现在没用了，所以删掉
        for k in mappings.keys():
            attrs.pop(k)

        # 将fields转义,注意后面的lambda的结束位置，到第二个f为止，fields是map的第二个参数
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名

        # 构造默认的SELECT, INSERT, UPDATE, DELETE语句：
        attrs['__select__'] = 'select * from `%s`' % tableName
        attrs['__insert__'] = 'insert into `%s` VALUES (%s)' % (tableName, create_args_string(len(fields) + 1))
        attrs['__update__'] = 'update `%s` set %s WHERE `%s`=?' %\
                              (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` WHERE `%s`=?' % (tableName, primaryKey)

        # 好长的一个函数
        return type.__new__(cls, name, bases, attrs)


# 为各种类型映射提供关系
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):
    # 默认映射类型为varchar(100)
    def __init__(self, name=None, primary_key=False, default=None, map_type='varchar(100)'):
        super().__init__(name, map_type, primary_key, default)


class IntegerField(Field):
    # 默认映射类型为bigint
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class BooleanField(Field):
    # bool值的可设置属性较少
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class FloatField(Field):
    # real就是float
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


# 创建连接池
async def create_pool(loop, **kw):
    logging.info('create database connect pool')

    global __pool
    # 创建连接池
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop

    )

# 映射select语句
async def select(sql, args, size=None):
    log(sql, args)

    global __pool

    with await __pool as conn:
        # 创建游标,执行select返回值为dict，将取得的数据装进dict内
        cur = await conn.cursor(aiomysql.DictCursor)

        # replace掉SQL语句中里面的问号，后面的args为空则传一个空tuple
        await cur.execute(sql.replace('?', '%s'), args or ())

        # fetch到指定数量的记录
        if size:
            rs = await cur.fetchmany(size)
        # 如果没有指定size则获取全部值
        else:
            rs = await cur.fetchall()

        await cur.close()
        # 输出获取的表单的数量
        logging.info('rows returned: %s' % len(rs))

        return rs

# 增删改全在一个函数里
async def execute(sql, args):
    log(sql)
    with await __pool as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            await cur.close()

        except BaseException as e:
            raise
        return affected


# 用于输出格式化的SQL执行语句
def log(sql, args=()):
    escape_sql = sql.replace('?', '%s')
    logging.info('SQL: %s' % escape_sql, args)


# 用于执行insert语句时创建参数占位'?'，因为insert语句参数较多，所以封装一个函数。有几个列属性，就创建几个占位符
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')

    return ', '.join(L)

