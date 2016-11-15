import asyncio
import inspect
import logging

import functools
import os

from aiohttp import web

from www.errors import APIError


def request_handler(func):
    # 本框架中最重要的函数，处理handle，将事先通过data_factory处理好的data（放在request.__data__中）与handle的参数
    # 相互匹配，并进行参数检查。最后调用handle，传入从data中获取到的值，返回handle执行后的返回值，供response_factory
    # 处理包装成response成品
    async def response(request):
        required_args = inspect.signature(func).parameters
        logging.info('required args: %s' % required_args)

        # 从读入的数据（通过middleware读取到，存放在request.__data__）中获取所需的arg(name)和值
        kw = {arg: value for arg, value in request.__data__.items() if arg in required_args}
        for k, v in request.match_info.items():
            # 如果match_info和args里面有同名key，就记录一下，便于出错时查找
            if k in kw:
                logging.warning('Duplicate arg name in args and match info: %s' % k)
            kw[k] = v

        # 如果func有request参数的话也加进去，因为request不可能从__data__取得，所以需要在这里加一下
        if 'request' in required_args:
            kw['request'] = request

        # 检查kw里面是否记录了全部func的参数键值对,所有参数是否都正确
        for key, arg in required_args.items():
            # 如果有名为request的参数，是否是可变参数，如*request,**request
            if key == 'request' and arg.kind in (arg.VAR_POSITIONAL, arg.VAR_KEYWORD):
                return web.HTTPBadRequest(text='request parameter cannot be the var argument.')
            # 如果某个参数名不在kw内又没有设定默认值，并且参数类型不是可变参数
            if arg.kind not in (arg.VAR_POSITIONAL, arg.VAR_KEYWORD) and arg.name not in kw and arg.default == arg.empty:
                # 就说明传参传少了
                return web.HTTPBadRequest(text='Missing argument: %s' % arg.name)

        logging.info('call with args: %s' % kw)
        try:
            return await func(**kw)
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

    return response


# 添加一个模块的所有路由
def add_routes(app, module_name):
    # 先导入模块
    try:
        mod = __import__(module_name, fromlist='get_submodule')
    except ImportError as e:
        raise e

    # 遍历mod的方法和属性
    for attr in dir(mod):
        # 首先忽略 _ 开头的方法或变量
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn) and hasattr(fn, '__method__') and hasattr(fn, '__route__'):
            logging.info('add route %s %s => %s(%s)' % (fn.__method__, fn.__route__, fn.__name__,
                                                        ', '.join(inspect.signature(fn).parameters.keys())))
            app.router.add_route(fn.__method__, fn.__route__, request_handler(fn))


def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))


# 生成GET等请求方法的装饰器
def request(path, *, method):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kw):
            # 将被修饰的handle包装为coroutine，如果其本身就是coroutine，该函数内部会自行判断，无需自己手动判断
            # 通过这一步，使得handle也可以是"非coroutine function"。
            # 这句话不能随意加，之前加在request_handler的第一句，结果导致coroutine被多包装一次
            corofunc = asyncio.coroutine(func)
            return await corofunc(*args, **kw)
        wrapper.__method__ = method
        wrapper.__route__ = path
        return wrapper
    return decorator


get = functools.partial(request, method='GET')
post = functools.partial(request, method='POST')
put = functools.partial(request, method='PUT')
delete = functools.partial(request, method='DELETE')
