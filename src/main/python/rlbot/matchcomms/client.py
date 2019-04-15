from contextlib import contextmanager, closing
from dataclasses import dataclass, field
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty  # TODO(python 3.7+): use SimpleQueue
from threading import Thread
from typing import Iterator, Dict, Any, Tuple, Set
import asyncio
import json
import multiprocessing as mp
import socket
import traceback

import websockets
from websockets.client import WebSocketClientProtocol

from rlbot.utils.logging_utils import get_logger
from rlbot.matchcomms.shared import MatchcommsPaths, JSON


class MatchcommsClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.incoming_broadcast = Queue()
        self.outgoing_broadcast = Queue()

        self.event_loop = asyncio.new_event_loop()
        self.event_loop.create_task(self._run_queue_io())
        self.thread = Thread(target=self.event_loop.run_forever, daemon=True)
        self.thread.start()

    async def _run_queue_io(self):
        try:
            async with websockets.connect(self.uri + MatchcommsPaths.BROADCAST) as websocket:
                io_task = self.event_loop.create_task(asyncio.wait(
                    [
                        read_into_queue(websocket, self.incoming_broadcast),
                        send_from_queue(websocket, self.outgoing_broadcast),
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                ))
                done, pending = await io_task  # should only finish when it is cancelled in close()
                for d in done:
                    d.print_stack()
                assert False, "The io task should only finish when canceled."
        except asyncio.CancelledError as e:
            pass  # We expect a cancel from self.close()

    def close(self):
        # Ensure all tasks are cancelled before stopping.
        # TODO(Python 3.7): always use asyncio.all_tasks
        get_all_tasks = asyncio.all_tasks if hasattr(asyncio, 'all_tasks') else asyncio.Task.all_tasks
        all_tasks = get_all_tasks(loop=self.event_loop)
        for task in all_tasks:
            task.cancel()
        for i in range(100):
            num_canned = sum(task.cancelled() or task.done() for task in all_tasks)
            if num_canned == len(all_tasks):
                break
            self.thread.join(0.01)

        self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        self.thread.join(1)
        assert not self.thread.is_alive()

async def read_into_queue(websocket: WebSocketClientProtocol, incoming: Queue):
    async for message in websocket:
        try:
            incoming.put(json.loads(message))
        except json.decoder.JSONDecodeError:
            print('Failed to decode this message:', repr(message))
            traceback.print_exc()



async def send_from_queue(websocket: WebSocketClientProtocol, outgoing: Queue):
    while True:
        # TODO: use something like https://github.com/aio-libs/janus to avoid polling
        while outgoing.empty():
            await asyncio.sleep(0.01)

        obj = outgoing.get_nowait()
        try:
            json_str = json.dumps(obj) # Serialize the object that was put on the outgoing queue
        except TypeError:
            traceback.print_exc()
        else:
            await websocket.send(json_str)


if __name__ == '__main__':
    from rlbot.matchcomms.server import self_test
    self_test()
