# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Test suite for module topology.platforms.shell.
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

# mock is located in unittest from Python 3.3 onwards, but as an external
# package in Python 2.7, that is why the following is done:
try:
    from unittest.mock import patch, Mock, call
except ImportError:
    from mock import patch, Mock, call

from pytest import fixture, raises

from topology.platforms.shell import (
    _NonExistingConnectionError, PExpectBashShell
)


class Shell(PExpectBashShell):
    def _get_connect_command(self):
        return 'test connection command '


@fixture(scope='function')
def shell():
    return Shell('prompt')


@fixture(scope='function')
def spawn(request):
    patch_spawn = patch('topology.platforms.shell.spawn')
    mock_spawn = patch_spawn.start()

    def create_mock(*args, **kwargs):
        class SpawnMock(Mock):
            def __init__(self, *args, **kwargs):
                super(SpawnMock, self).__init__(*args, **kwargs)
                self._connected = True

            def close(self):
                self._connected = False

            def isalive(self):
                return self._connected

        return SpawnMock()

    mock_spawn.configure_mock(**{'side_effect': create_mock})

    def finalizer():
        patch_spawn.stop()

    request.addfinalizer(finalizer)

    return mock_spawn


def test_spawn_args(spawn, shell):
    """
    Test that the arguments for Pexpect spawn are correct.
    """
    shell.connect()

    spawn.assert_called_with(
        'test connection command', echo=False, env={'TERM': 'dumb'}
    )

    shell = Shell(
        '', spawn_args={'env': {'TERM': 'smart'}, 'echo': True}
    )

    shell.connect()

    spawn.assert_called_with(
        'test connection command', env={'TERM': 'smart'}, echo=True
    )


def test_create_shell(spawn, shell):
    """
    Test that a new connection is added to the shell by calling ``connect``.
    """
    assert not list(shell._connections.keys())

    shell.connect()

    assert list(shell._connections.keys()) == ['0']

    shell.connect(connection='1')

    assert list(shell._connections.keys()) == ['0', '1']


def test_initial_default_connection(spawn, shell):
    """
    Test that a default undefined connection exists before attempting a
    connection to the shell.
    """

    assert not shell._default_connection


def test_specific_default_connection(spawn, shell):
    """
    Test that the specified connection is used when specified.
    Test that the default connection is used when the connection is not
    specified.
    """

    shell.connect()
    shell.connect(connection='1')

    shell.send_command('command', connection='1')

    shell._connections['1'].sendline.assert_called_with('command')

    with raises(AssertionError):
        shell._connections['0'].sendline.assert_called_with('command')

    shell.send_command('command')
    shell._connections['0'].sendline.assert_called_with('command')


def test_default_connection(spawn, shell):
    """
    Test that the default_connection property works as expected.
    """

    assert shell.default_connection is None

    shell.connect()

    assert shell.default_connection == '0'

    shell.connect(connection='1')

    assert shell.default_connection == '0'

    with raises(_NonExistingConnectionError):
        shell.default_connection = '2'

    shell.default_connection = '1'

    assert shell.default_connection == '1'


def test_send_command(spawn, shell):
    """
    Test that send_command works properly.
    """

    shell.send_command('command')

    shell._connections[shell._default_connection].sendline.assert_called_with(
        'command'
    )


def test_get_response(spawn, shell):
    """
    Test that get_response works properly.
    """

    with raises(Exception):
        shell.get_response()

    shell.send_command('command')

    shell._connections[shell._default_connection].configure_mock(
        **{'before.decode.return_value': 'response'}
    )

    assert shell.get_response() == 'response'

    shell._connections[
        shell._default_connection
    ].before.decode.assert_called_with(shell._encoding)


def test_non_existing_connection(spawn, shell):
    """
    Test that a non existing connection is detected when there is an attempt to
    use it.
    """

    shell.connect()
    shell.connect(connection='1')

    with raises(_NonExistingConnectionError):
        shell.is_connected(connection='2')


def test_is_connected(spawn, shell):
    """
    Test that is_connected returns correctly.
    """

    assert not shell.is_connected()

    shell.connect()

    assert shell.is_connected()

    shell.connect(connection='1')

    assert shell.is_connected(connection='1')


def test_disconnect(spawn, shell):
    """
    Test that disconnect works properly.
    """

    shell.connect()
    shell.disconnect()

    assert not shell.is_connected()

    with raises(Exception):
        shell.disconnect()

    shell.connect(connection='1')
    shell.disconnect(connection='1')

    assert not shell.is_connected(connection='1')

    with raises(Exception):
        shell.disconnect(connection='1')


def test_setup_shell(spawn, shell):
    """
    Test that _setup_shell works properly.
    """

    initial_prompt = shell._initial_prompt

    shell.connect()

    shell._connections[
        shell._default_connection
    ].sendline.assert_has_calls(
        [
            call('stty -echo'),
            call('export PS1={}'.format(PExpectBashShell.FORCED_PROMPT))
        ]
    )

    assert shell._initial_prompt == initial_prompt

    shell.connect(connection='1')

    shell._connections['1'].sendline.assert_has_calls(
        [
            call('stty -echo'),
            call('export PS1={}'.format(PExpectBashShell.FORCED_PROMPT))
        ]
    )

    assert shell._initial_prompt == initial_prompt
