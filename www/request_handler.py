import asyncio
import inspect
import logging

import functools
from aiohttp import web

from www.errors import APIError


def request_handler(func):
    func = asyncio.coroutine(func)

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
            handled_fn = request_handler(fn)
            app.router.add_route(fn.__method__, fn.__route__, handled_fn)


# 生成GET等请求方法的装饰器
def request(path, *, method):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = method
        wrapper.__route__ = path
        return wrapper
    return decorator


get = functools.partial(request, method='GET')
post = functools.partial(request, method='POST')
put = functools.partial(request, method='PUT')
delete = functools.partial(request, method='DELETE')
