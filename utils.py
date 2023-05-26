import asyncio
import datetime
import decimal
import traceback
import uuid
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from functools import partial, reduce
from typing import Dict, List, Any, Callable, Union

import simplejson as json
from aio_pika import connect_robust, Exchange, Message, DeliveryMode, IncomingMessage, Channel
from state_service_utils.enums_client import enums
from vtb_http_interaction.process_authorization_header import MemoryCache
from vtb_http_interaction.services import AuthorizationHttpService, HttpServiceWithRequestId
from vtb_py_logging.log_extra import log_extra
from vtb_py_logging.request_id import RequestId
from vtb_py_logging.utils import get_graph_logger

from .conf import LOG_FULL, STATE_SERVICE_URL, KEYCLOAK_CONFIG, STATE_SERVICE_TOKEN, \
    STATE_SERVICE_MOCK, RETRY_ON_STATUSES, RMQ_SS_ACTION_RECEIVER, RMQ_SS_ADDR, SSL_VERIFY
from .exceptions import StateServiceException
from .logging import create_logger


@dataclass
class OrderAction:
    order_id: str
    action_id: str
    graph_id: str
    graph_version: str = ''


async def add_action_event(*, action: OrderAction, type, subtype, status='', data=None,
                           log_level=LOG_FULL, create_dt=None):
    if not log_level:
        return

    request_data = {
        'type': type,
        'subtype': subtype,
        'status': status,
    }
    if log_level == LOG_FULL:
        request_data['data'] = data

    if create_dt:
        request_data['create_dt'] = create_dt

    request_data.update(action.__dict__)

    await _make_request(
        url=f'{STATE_SERVICE_URL}/actions/',
        data=request_data
    )


def add_action_event_mq(queue: str, chan: Channel, reply_queue: str, futures: Dict, loop: None):
    async def add_action_event_wrap(*, action: OrderAction, type, subtype, status='', data=None,
                                    log_level=LOG_FULL):
        if not log_level:
            return

        request_data = {
            'type': type,
            'subtype': subtype,
            'status': status,
        }
        if log_level == LOG_FULL:
            request_data['data'] = data

        request_data.update(action.__dict__)

        correlation_id = str(uuid.uuid4())
        future = loop.create_future()

        futures[correlation_id] = future
        await chan.default_exchange.publish(
            Message(
                json.dumps(data).encode(),
                correlation_id=correlation_id,
                reply_to=reply_queue,
                content_type='application/json',
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=queue,
        )
        await future

    return add_action_event_wrap


async def add_event(*, action: OrderAction, item_id: str,
                    type, subtype, status='', data=None, create_dt=None):
    """ Создание события в сервисе состояний """
    data = {
        'item_id': item_id,
        'type': type,
        'subtype': subtype,
        'status': status,
        'data': data
    }

    if create_dt:
        data['create_dt'] = create_dt

    data.update(action.__dict__)
    await _make_request(
        url=f'{STATE_SERVICE_URL}/events/',
        data=data
    )


async def add_events(*, action: OrderAction, events: List[Dict]) -> Any:
    """ Создание списка событий в сервисе состояний одним запросом """
    data = {
        'events': events
    }
    data.update(action.__dict__)
    return await _make_request(
        url=f'{STATE_SERVICE_URL}/events/bulk-add-event/',
        data=data
    )


def state_action_decorator(
        is_add_call_kwargs: Union[bool, Callable] = True,
        add_action_event_fn: Callable = add_action_event):
    def func_decorator(func):
        async def wrapper(*, order_action: OrderAction, node, action_type=enums.ActionDeploy.RUN_NODE.value,
                          task_logger, log_level=LOG_FULL, **kwargs):
            node_name = node if isinstance(node, str) else node.path
            await add_action_event_fn(
                action=order_action,
                type=enums.ActionType.DEPLOY.value,
                subtype=action_type,
                status='%s:%s' % (node_name, enums.ActionStatus.STARTED.value),
                data=kwargs,
                log_level=log_level
            )
            try:
                if action_type not in enums.ActionDeploy._value2member_map_.keys():
                    raise StateServiceException(f'Invalid action type: {action_type}')
                if is_add_call_kwargs:
                    kwargs.update({
                        'order_action': order_action,
                        'action_type': action_type,
                        'task_logger': task_logger
                    })
                result = await func(
                    node=node,
                    **kwargs,
                )
                status = '%s:%s' % (node_name, enums.ActionStatus.COMPLETED.value)
            except Exception as e:
                tb = traceback.format_exc()
                result = {
                    'error': str(e),
                    'traceback': tb,
                    'extra': getattr(e, 'extra', {})
                }
                status = '%s:%s' % (node_name, enums.ActionStatus.ERROR.value)
                task_logger.error(
                    f'Error in action ({status}): {tb}')
                if log_level is not None:
                    log_level = LOG_FULL
            await add_action_event_fn(
                action=order_action,
                type=enums.ActionType.DEPLOY.value,
                subtype=action_type,
                status=status,
                data=result,
                log_level=log_level
            )
            return result

        return wrapper

    if callable(is_add_call_kwargs):
        # it means that the decorator was called without its arguments, therefore we
        # are passing argument further to the func_decorator and assigning default argument value
        wrapped_func = is_add_call_kwargs
        is_add_call_kwargs = True
        return func_decorator(wrapped_func)
    else:
        # the decorator was called with arguments, hence we are returning the wrapper just as usual
        return func_decorator


class BaseEventsReceiver(ABC):
    def __init__(self, fn, mq_addr, mq_input_queue, logger_name: str = '', ssl: bool = False):
        self.mq_addr = mq_addr
        self.ssl = ssl
        self.input_queue = mq_input_queue
        self.fn = state_action_decorator()(fn)
        self.logger = create_logger(logger_name)

        self.connection = None
        self.channel = None
        self.queue = None
        self.consumer = None
        self.loop = None

    @staticmethod
    async def on_message(message: IncomingMessage, callback, exchange: Exchange, logger):
        """we do it in staticmethod to allow custom logic in different async realisation"""
        async with message.process():
            data = json.loads(message.body)

            if not isinstance(data, dict):
                raise StateServiceException('Invalid message (need struct): %s', data)

            order_action = OrderAction(
                order_id=data.pop('_order_id'),
                action_id=data.pop('_action_id'),
                graph_id=data.pop('_graph_id'))
            node = data['_name']
            action_type = data.get('_type')

            task_logger = get_graph_logger(logger=logger, order_action=order_action, node=node,
                                           action_type=action_type, orchestrator_id=data.get('_id'))

            request_id = message.headers.get('request_id')
            if not request_id:
                request_id = RequestId.make(prefix='ssu')

            with log_extra(request_id=request_id):
                response = await callback(
                    order_action=order_action,
                    node=node,
                    action_type=action_type,
                    task_logger=task_logger,
                    **data,
                )

            if not isinstance(response, str):
                response = json.dumps(response, default=default_encoder)

            await exchange.publish(
                Message(body=response.encode(), content_type='application/json',
                        correlation_id=message.correlation_id, delivery_mode=DeliveryMode.PERSISTENT),
                routing_key=message.reply_to,
            )

    async def _receive(self, addr, queue_name, queue_kwargs, prefetch_count=None, ssl: bool = False):
        self.connection = await connect_robust(addr, loop=self.loop, ssl=ssl)
        self.channel = await self.connection.channel()
        if prefetch_count:
            await self.channel.set_qos(prefetch_count=prefetch_count)
        self.queue = await self.channel.declare_queue(queue_name, **(queue_kwargs or {}), durable=True)
        self.consumer = await self.queue.consume(partial(
            self.on_message,
            callback=self.fn,
            exchange=self.channel.default_exchange,
            logger=self.logger
        ))

    def run(self, queue_kwargs: dict = None, prefetch_count: int = None, loop=None):
        """ Запуск процесса прослушивания """
        self.loop = loop or asyncio.get_event_loop()

        task = self.loop.create_task(self._receive(
            addr=self.mq_addr,
            queue_name=self.input_queue,
            queue_kwargs=queue_kwargs,
            prefetch_count=prefetch_count,
            ssl=self.ssl
        ))
        self.loop.run_until_complete(task)
        self.logger.info('Awaiting events')
        try:
            self.loop.run_forever()
        except (SystemExit, KeyboardInterrupt):
            self.logger.info('Server stopped')

    async def close(self) -> None:
        """
        Закрытие подключения
        """
        if self.channel:
            await self.channel.close()

        if self.connection:
            await self.connection.close()


class EventsReceiver(BaseEventsReceiver):
    def __init__(self, fn, mq_addr, mq_input_queue, logger_name: str = '', ssl: bool = False):
        super().__init__(fn, mq_addr, mq_input_queue, logger_name, ssl)
        self.fn = state_action_decorator(fn)


class QEventsReceiver(BaseEventsReceiver):
    """
    EventsReceiver implemented using rmq for state service requests.
    """

    def __init__(self, fn, mq_addr, mq_input_queue, logger_name: str = '', ssl: bool = False):
        super().__init__(fn, mq_addr, mq_input_queue, logger_name, ssl)
        self.state_service_connection = None
        self.state_service_channel = None
        self.state_service_queue = None
        self.futures = {}

    async def on_state_service_response(self, message: IncomingMessage) -> None:
        if message.correlation_id is None:
            self.logger(f'Wrong message: {message!r}')
            return

        future: asyncio.Future = self.futures.pop(message.correlation_id)
        future.set_result(message.body)

    async def _receive(self, addr, queue_name, queue_kwargs, prefetch_count=None, ssl: bool = False):
        await super()._receive(addr, queue_name, queue_kwargs, prefetch_count, ssl)
        self.state_service_connection = await connect_robust(RMQ_SS_ADDR, loop=self.loop, ssl=SSL_VERIFY)
        self.state_service_channel = await self.state_service_connection.channel()
        self.state_service_queue = self.state_service_channel.declare_queue(exclusive=True)
        await self.state_service_queue.consume(self.on_state_service_response)
        self.fn = state_action_decorator(
            add_action_event_fn=add_action_event_mq(
                RMQ_SS_ACTION_RECEIVER,
                self.state_service_channel,
                reply_queue=self.state_service_queue.name,
                futures=self.futures,
                loop=self.loop
            )
        )

    async def close(self) -> None:
        """
        Закрытие подключения
        """
        await super().close()
        if self.state_service_channel:
            await self.state_service_channel.close()

        if self.state_service_connection:
            await self.state_service_connection.close()


def items_from_events(events: List[dict], pre_ordered=False) -> list:
    """
        Получает список событий:
            - отсортированных в обратном порядке по времени создания и флагом 'pre_ordered' = True
            - или не сортированных, но имеющих поле со временем создания - 'create_dt'
        Возвращает список item:
            - с полем 'data', содержащим все уникальные ключи 'subtype'. С последними значениями 'subtype'
    """
    if not events:
        return []

    exclude = {'id', 'subtype', 'status', 'data', 'create_dt'}
    items_dict = {}

    if not pre_ordered:
        events = sorted(events, key=lambda x: x['create_dt'], reverse=True)

    for event in events:
        item_id = str(event['item_id'])
        items_dict.setdefault(item_id, {
            **{k: v for k, v in event.items() if k not in exclude},
            **{'data': {}, 'update_dt': event.get('create_dt')},
        })
        if event['subtype'] not in items_dict[item_id]['data']:
            items_dict[item_id]['data'][event['subtype']] = event.get('status') or event.get('data')

    return list(items_dict.values())


def default_encoder(obj):
    """ Default JSON encoder """
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()

    if isinstance(obj, (uuid.UUID, decimal.Decimal)):
        return str(obj)

    return obj


class UpdateTypeAction(Enum):
    """ Тип обновления конфигурации """
    UPDATE = 'update'
    REPLACE = 'replace'


def get_dict_value_by_path(dict_object: dict, path_iter: Union[list, tuple]):
    """ Возвращает значение из словаря с ключом собранным из path """

    def _reduce(dict_node, next_key):
        if dict_node and next_key in dict_node:
            return dict_node[next_key]

        raise StopIteration

    try:
        return reduce(_reduce, path_iter, dict_object)
    except StopIteration:
        return None


def update_dict_by_path(dict_object: Union[dict, list], path_iter: Union[list, tuple], updated_data: Union[list, dict],
                        action_type: UpdateTypeAction) -> dict:
    """ Возвращает корень словаря по ключу собранным из path """
    if not path_iter:
        if action_type == UpdateTypeAction.UPDATE:
            if isinstance(updated_data, list):
                dict_object.extend(updated_data)
            else:
                dict_object.update(updated_data)
        elif action_type == UpdateTypeAction.REPLACE:
            dict_object = updated_data
        else:
            raise NotImplementedError(f'Unrecognized update type: {action_type}')

    elif len(path_iter) == 1:
        if path_iter[0] not in dict_object:
            dict_object[path_iter[0]] = updated_data
        else:
            if action_type == UpdateTypeAction.UPDATE:
                if isinstance(updated_data, list) and isinstance(dict_object[path_iter[0]], list):
                    dict_object[path_iter[0]].extend(updated_data)
                elif isinstance(updated_data, dict) and isinstance(dict_object[path_iter[0]], dict):
                    dict_object[path_iter[0]].update(updated_data)
                else:
                    dict_object[path_iter[0]] = updated_data
            elif action_type == UpdateTypeAction.REPLACE:
                dict_object[path_iter[0]] = updated_data
            else:
                raise NotImplementedError(f'Unrecognized update type: {action_type}')

    # len(path_str) > 1
    else:
        if path_iter[0] not in dict_object:
            dict_object[path_iter[0]] = update_dict_by_path({}, path_iter[1:], updated_data, action_type)
        else:
            result_data = update_dict_by_path(dict_object[path_iter[0]], path_iter[1:], updated_data, action_type)
            if action_type == UpdateTypeAction.UPDATE:
                if isinstance(result_data, list):
                    dict_object[path_iter[0]].extend(result_data)
                else:
                    dict_object[path_iter[0]].update(result_data)
            elif action_type == UpdateTypeAction.REPLACE:
                dict_object[path_iter[0]] = result_data
            else:
                raise NotImplementedError(f'Unrecognized update type: {action_type}')

    return dict_object


def calculate_new_config_data(prev_data: Union[list, dict], updated_data: Union[list, dict], path: str,
                              action_type: UpdateTypeAction) -> dict:
    """ Расчет конфигурации с учетом новых данных """
    new_data = deepcopy(prev_data)
    path_iter = path.split('.') if path else None
    return update_dict_by_path(new_data, path_iter, updated_data, action_type)


async def _make_create_with_drf_token(url, data: dict) -> Any:
    service = HttpServiceWithRequestId(retry_on_statuses=RETRY_ON_STATUSES)
    request = {
        'method': 'POST',
        'url': url,
        'cfg': {
            'timeout': 60,
            'json': data,
            'headers': {'Authorization': f'Token {STATE_SERVICE_TOKEN}'}
        }
    }
    status, response = await service.send_request(**request)

    if status == 400:
        raise StateServiceException(response)
    elif status != 201:
        raise StateServiceException(f'State service request error ({status}): {response}')

    return status, response


async def _make_create_with_keycloak_token(url, data: dict) -> Any:
    service = AuthorizationHttpService(KEYCLOAK_CONFIG, token_cache=MemoryCache(), retry_on_statuses=RETRY_ON_STATUSES)

    request = {
        'method': 'POST',
        'url': url,
        'cfg': {
            'timeout': 60,
            'json': data
        }
    }
    status, response = await service.send_request(**request)

    if status == 400:
        raise StateServiceException(response)
    elif status != 201:
        raise StateServiceException(f'State service request error ({status}): {response}')

    return response


async def _make_request(url, data: dict) -> Any:
    if STATE_SERVICE_MOCK:
        return None, None

    if STATE_SERVICE_TOKEN:
        return await _make_create_with_drf_token(url, data)
    elif KEYCLOAK_CONFIG:
        return await _make_create_with_keycloak_token(url, data)
