# Vehicle API/Command Executor Agent
import asyncio
from utils.logging_config import get_logger

logger = get_logger(__name__)

class VehicleAPIExecutor:
    def __init__(self):
        self.command_queue = asyncio.Queue()
        self.command_log = []

    async def send_command(self, command):
        await self.command_queue.put(command)
        self.command_log.append(command)
        return command.get("commandId")

    def get_command_log(self):
        return self.command_log
