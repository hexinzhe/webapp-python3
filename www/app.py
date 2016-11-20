import logging; logging.basicConfig(level=logging.INFO)

from www import config, init_jinja2, datetime_filter
from www import orm
from www.factories import logger_factory, data_factory, response_factory, auth_factory
from www.request_handler import add_routes, add_static
import asyncio, os, json, time
from aiohttp import web


async def init(loop):
    await orm.create_pool(loop, **config.configs['db'])
    app = web.Application(loop=loop, middlewares=[
        logger_factory, data_factory, auth_factory, response_factory
    ])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handles')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
