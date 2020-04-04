import asyncio
import discord
import json
import os
import requests

from threading import Lock


def get_config_file_path():
    return './config.json'


def get_ip_string(ip, port):
    if port == 0:
        return ip
    else:
        return ip + ':' + str(port)


class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

        self._task = asyncio.ensure_future(self._job())

    def cancel(self):
        self._task.cancel()


class ConfigData:
    def __init__(self):
        self.token = 'undefined'
        self.last_address = 'unknown'
        self.port = 0
        self.timer_timeout = 60
        self.bound = []
        self.prefix = '+'

        # Messages
        self.msg_ip_changed = '**WARNING:** New IP address: %s!'
        self.msg_cmd_ip = 'The current IP address is: %s.'
        self.msg_cmd_bind = 'This chat is now bound!'
        self.msg_cmd_unbind = 'Chat unbound.'

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class Config:
    def __init__(self, file_path):
        self._file_path = file_path
        self._last_mtime = 0

        self._mutex = Lock()
        self._config_data = ConfigData()

        self.load()

    def load(self):
        if not os.path.isfile(self._file_path):
            self.save()
        else:
            try:
                self._mutex.acquire()
                f = open(self._file_path, 'r')
                obj = json.loads(f.read())
                f.close()

                self._config_data.__dict__ = obj
                self._last_mtime = os.path.getmtime(self._file_path)
            except:
                print('Failed to load config file')
            finally:
                self._mutex.release()

    def save(self):
        try:
            self._mutex.acquire()
            f = open(self._file_path, 'w')
            f.write(self._config_data.to_json())
            f.close()

            self._last_mtime = os.path.getmtime(self._file_path)
        except:
            print('Failed to save config file')
        finally:
            self._mutex.release()

    def _pre_config_operation(self):
        try:
            mtime = os.path.getmtime(self._file_path)
            if self._last_mtime != mtime:
                self.load()
        except:
            print('Failed to get config file data')

    # Gets
    def get_token(self):
        self._pre_config_operation()
        return self._config_data.token

    def get_last_address(self):
        self._pre_config_operation()
        return self._config_data.last_address

    def get_port(self):
        self._pre_config_operation()
        return self._config_data.port

    def get_timer_timeout(self):
        self._pre_config_operation()
        return self._config_data.timer_timeout

    def get_binds(self):
        self._pre_config_operation()
        return self._config_data.bound

    def is_bound(self, chat):
        self._pre_config_operation()
        return chat in self._config_data.bound

    def get_prefix(self):
        self._pre_config_operation()
        return self._config_data.prefix

    def get_ip_changed_message(self):
        self._pre_config_operation()
        return self._config_data.msg_ip_changed % get_ip_string(
            self._config_data.last_address, self._config_data.port)

    def get_ip_command_message(self):
        self._pre_config_operation()
        return self._config_data.msg_cmd_ip % get_ip_string(
            self._config_data.last_address, self._config_data.port)

    def get_bind_command_message(self):
        self._pre_config_operation()
        return self._config_data.msg_cmd_bind

    def get_unbind_command_message(self):
        self._pre_config_operation()
        return self._config_data.msg_cmd_unbind

    # Sets
    def set_last_address(self, new_address):
        self._pre_config_operation()
        self._config_data.last_address = new_address
        self.save()

    def bind(self, chat):
        self._pre_config_operation()
        if chat not in self._config_data.bound:
            self._config_data.bound.append(chat)
            self.save()

    def unbind(self, chat):
        self._pre_config_operation()
        if chat in self._config_data.bound:
            self._config_data.bound.remove(chat)
            self.save()


class Client(discord.Client):
    def __init__(self, config_file_path):
        super().__init__()
        self._config = Config(config_file_path)

        Timer(self._config.get_timer_timeout(), self._ip_check)

        if self._config.get_token() == 'undefined':
            print('Please check the configuration file')
        else:
            self.run(self._config.get_token())

    # Events
    async def on_ready(self):
        await self._ip_check()
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return

        prefix = self._config.get_prefix()
        if not message.content.startswith(prefix):
            return

        if message.content == prefix + 'ip':
            await self._ip_check()
            await message.channel.send(
                self._config.get_ip_command_message())
        elif message.content == prefix + 'bind':
            self._config.bind(message.channel.id)
            await message.channel.send(
                self._config.get_bind_command_message())
        elif message.content == prefix + 'unbind':
            self._config.unbind(message.channel.id)
            await message.channel.send(
                self._config.get_unbind_command_message())

    async def _ip_check(self):
        result = requests.get('https://api.ipify.org')
        if '<' in result.text:
            return
        if self._config.get_last_address() != result.text:
            self._config.set_last_address(result.text)
            for chat in self._config.get_binds():
                try:
                    channel = self.get_channel(chat)
                    await channel.send(
                        self._config.get_ip_changed_message())
                except:
                    continue


while True:
    try:
        Client(get_config_file_path())
    except:
        continue
