# P27LeiqZ07iJqME2sBWyqUzjgjRdCx1j

import asyncio
import discord
import json
import os
import requests

from threading import Lock

config_mutex = Lock()


def getToken():
    return 'MjQ1MDI2Mzg3NTcwODUxODUw.Xhd1EQ.LChBhn2tfoEiaZW9j9Y3J38DtS8'

def getConfigPath():
    return './config.json'

def getPort():
    return 15535

def getIPMessageFormat():
    return 'Endereço de IP: %s:%d'

def getNewIPMessageFormat():
    return '**ATENÇÃO:** Novo endereço de IP: %s:%d'

def getCheckIPTimeout():
    return 600


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

class Config:
    def __init__(self):
        self.last_address = 'unset'
        self.bound = []
        self.load()
    
    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def load(self):
        if not os.path.isfile(getConfigPath()):
            self.save()
        else:
            f = open(getConfigPath(), 'r')
            obj = json.loads(f.read())
            self.__dict__ = obj
            f.close()

    def save(self):
        f = open(getConfigPath(), 'w')
        f.write(self.to_json())
        f.close()

    def set_last_address(self, addr):
        try:
            config_mutex.acquire()
            self.last_address = addr
            self.save()
        finally:
            config_mutex.release()

    def bind(self, chat):
        try:
            config_mutex.acquire()
            if not chat in self.bound:
                self.bound.append(chat)
                self.save()
        finally:
            config_mutex.release()

    def unbind(self, chat):
        try:
            config_mutex.acquire()
            if chat in self.bound:
                self.bound.remove(chat)
                self.save()
        finally:
            config_mutex.release()

    def get_last_address(self):
        return self.last_address

    def get_binds(self):
        return self.bound
    
    def is_bound(self, chat):
        return chat in self.bound

        
config = Config()


class MyClient(discord.Client):
    # Events
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.ip_check()
        Timer(getCheckIPTimeout(), self.ip_check)

    async def on_message(self, message):
        if message.author == client.user:
            return
        elif message.content == '+ip':
            await self.ip_check()
            await message.channel.send(getIPMessageFormat() % (config.get_last_address(), getPort()))
        elif message.content == '+bind':
            config.bind(message.channel.id)
            await message.channel.send('Bound!')
        elif message.content == '+unbind':
            config.unbind(message.channel.id)
            await message.channel.send('Unbound!')

    async def ip_check(self):
        result = requests.get('https://api.ipify.org')
        if '<' in result.text:
            return
        if config.get_last_address() != result.text:
            config.set_last_address(result.text)
            for chat in config.get_binds():
                try:
                    channel = self.get_channel(chat)
                    await channel.send(getNewIPMessageFormat() % (config.get_last_address(), getPort()))
                except:
                    continue

client = MyClient()
client.run(getToken())

