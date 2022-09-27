"""Шина сообщений

Запускает обработку команд и событий
(Вызывает соответствующие обработчики)
"""

# pylint: disable=broad-except
from __future__ import annotations
import logging
from typing import List, Dict, Callable, Type, Union, TYPE_CHECKING
from src.auth_client.domain import commands, events
from . import handlers

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)

Message = Union[commands.Command, events.Event]


def handle(
    message: Message,
    uow: unit_of_work.AbstractUnitOfWork,
):
    """Обработать очередь сообщений
    
    Запускает обработчики для каждого сообщения из очереди в зависимости от типа сообщения"""
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            cmd_result = handle_command(message, queue, uow)
            results.append(cmd_result)
        else:
            raise Exception(f"{message} was not an Event or Command")
    return results


def handle_event(
    event: events.Event,
    queue: List[Message],
    uow: unit_of_work.AbstractUnitOfWork,
):
    """Обработать сообщение с типом Событие (event)"""
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            logger.debug("handling event %s with handler %s", event, handler)
            handler(event, uow=uow)
            queue.extend(uow.collect_new_events())
        except Exception:
            logger.exception("Exception handling event %s", event)
            continue


def handle_command(
    command: commands.Command,
    queue: List[Message],
    uow: unit_of_work.AbstractUnitOfWork,
):
    """Обработать сообщение с типом Команда (command)"""
    logger.debug("handling command %s", command)
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow=uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        logger.exception("Exception handling command %s", command)
        raise

# events Dict
EVENT_HANDLERS = {
    events.StateExpired: [handlers.state_expired],
    events.AuthCodeRecieved: [handlers.auth_code_recieved]
}  # type: Dict[Type[events.Event], List[Callable]]

# commands Dict
COMMAND_HANDLERS = {
    commands.CreateState: handlers.create_state,
    commands.ValidateState: handlers.validate_state,
    commands.CreateAuthorization: handlers.create_authorization,
    # commands.CreateBatch: handlers.add_batch,
    # commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}  # type: Dict[Type[commands.Command], Callable]
