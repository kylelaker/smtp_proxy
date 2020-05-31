#!/usr/bin/env python3

"""
Acts a sort of SMTP proxy.

Some devices aren't so bright and authenticate to SMTP servers incorrectly. This can be a bit
of an inconvenience. This will accept the messages from those devices, using no authentication,
and then authenticate to another SMTP server (like Gmail, SES, or SendGrid) to have them be
delivered.
"""

import asyncio
import os
import smtplib
import sys

import aiosmtpd
import click
import ruamel.yaml as yaml

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message


class ConfigurationError(Exception):
    pass


def parse_config(config_file):
    """
    Parses the configuration file. Since it's simple, it's sort of easier to just do
    the checking in a fairly explicit hard-coded way.

    The expected structure looks something like:

    .. code-block: YAML
        server:
          listen:
            addr: 0.0.0.0
            port: 8025
        proxy:
          hostname: smtp.sendgrid.net
          port: 25
          username: apikey
          tls: STARTTLS
          password: SG.xxxxxxxxxxxxxxxxxxxxxxxx

    :param config: The stream/file that holds the configuration
    :raises ConfigurationError: when the configuration is invalid
    :returns: The parsed configuration
    :rtype: dict
    """
    try:
        config = yaml.safe_load(config_file)
    except yaml.YAMLError as err:
        raise ConfigurationError(str(err))

    if not config:
        raise ConfigurationError("configuration is empty")

    if 'server' not in config:
        raise ConfigurationError("'server' is missing from config")
    if 'listen' not in config['server']:
        raise ConfigurationError("'server.listen' is missing from config")
    for section in ('addr', 'port'):
        if section not in config['server']['listen']:
            raise ConfigurationError(f"'server.listen.{section}' is missing from config")
    if 'proxy' not in config:
        raise ConfigurationError("'proxy' is missing from config")
    for section in ('hostname', 'port', 'username', 'password', 'tls'):
        if section not in config['proxy']:
            raise ConfigurationError(f"'proxy.{section}' is missing from config")
    if config['proxy']['tls'] not in (True, False, 'STARTTLS'):
        raise ConfigurationError("'proxy.tls' must be one of [True, False, 'STARTTLS']")
    return config


class MessageProxy(Message):
    """
    An aiosmtpd Handler to proxy messages.

    Receives the message and initiates a connection to the remote server to end it. A new
    connection to the remote server will be established for each message. Any failures from
    sending will not be reported back to the client.
    """

    def __init__(self, proxy_config, message_class=None):
        super().__init__(message_class)
        self.proxy_config = proxy_config

    def _initialize_client(self, hostname, port, username, password, tls, **kwargs):
        if tls is True:
            smtp_init = smtplib.SMTP_SSL
        else:
            smtp_init = smtplib.SMTP
        client = smtp_init(hostname, port)
        if str(tls).lower() == 'starttls':
            client.starttls()
        client.login(username, password)
        return client

    def handle_message(self, message):
        client = self._initialize_client(**self.proxy_config)
        client.send_message(message)
        client.quit()


async def server_main(loop, proxy_config, server_config):
    """
    Initialize the controller for asyncio.
    """

    controller = Controller(
        MessageProxy(proxy_config),
        hostname=server_config['listen']['addr'],
        port=server_config['listen']['port'],
    )
    controller.start()


@click.command('smtp-proxy')
@click.option(
    '--config-file',
    '-f',
    type=click.File(),
    help="The path to the configuration file",
    required=True,
)
def main(config_file):

    try:
        config = parse_config(config_file)
    except ConfigurationError as e:
        print(e)
        return 1

    server = config['server']
    proxy = config['proxy']
    loop = asyncio.get_event_loop()
    loop.create_task(server_main(loop, proxy, server))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
