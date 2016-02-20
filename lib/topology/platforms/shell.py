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
topology shell api module.
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from logging import getLogger
from re import sub as regex_sub
from abc import ABCMeta, abstractmethod

from pexpect import spawn
from six import add_metaclass


log = getLogger(__name__)


TERM_CODES_REGEX = r'\x1b[E|\[](\?)?([0-9]{1,2}(;[0-9]{1,2})?)?[m|K|h|H|r]?'
"""
Regular expression to match terminal control codes.

A terminal control code is a special sequence of characters that sent by some
applications to control certain features of the terminal. It is responsibility
of the terminal application (driver) to interpret those control codes.
However, when using pexpect, the incoming buffer will still have those control
codes and will not interpret or do anything with them other than store them.
This regular expression allows to remove them as they are unneeded for the
purpose of executing commands and parsing their outputs
(unless proven otherwise).

``\\x1b``
  Match prefix that indicates the next characters are part of a terminal code
  string.
``[E|\\[]``
  Match either ``E`` or ``[``.
``(\\?)?``
  Match zero or one ``?``.
``([0-9]{1,2}``
  Match 1 or 2 numerical digits.
``(;[0-9]{1,2})?``
  Match zero or one occurences of the following pattern: ``;`` followed by 1
  or 2 numerical digits.
``)?``
  Means the pattern composed by the the last 2 parts above can be found zero or
  one times.
``[m|K|h|H|r]?``
  Match zero or one occurrences of either ``m``, ``K``, ``h``, ``H`` or ``r``.
"""


@add_metaclass(ABCMeta)
class BaseShell(object):

    @abstractmethod
    def send_command(self, command, matches=None, newline=True, timeout=None):
        """
        FIXME: Document.
        """

    @abstractmethod
    def get_response(self):
        """
        FIXME: Document.
        """

    @abstractmethod
    def is_connected(self):
        """
        FIXME: Document.
        """

    @abstractmethod
    def connect(self):
        """
        FIXME: Document.
        """

    @abstractmethod
    def disconnect(self):
        pass

    def execute(self, command):
        """
        FIXME: Document.
        """
        self.send_command(command)
        return self.get_response()

    def __call__(self, command):
        return self.execute(command)


@add_metaclass(ABCMeta)
class PExpectShell(BaseShell):
    """
    See :class:`BaseShell`.
    """

    def __init__(
            self, prompt,
            initial_command=None, initial_prompt=None,
            password=None, password_match='[pP]assword:',
            prefix=None, timeout=None, encoding='utf-8'):

        self._initial_command = initial_command
        self._prompt = prompt
        self._initial_prompt = initial_prompt
        self._password = password
        self._password_match = password_match
        self._prefix = prefix
        self._timeout = timeout or -1
        self._encoding = encoding

        self._spawn = None
        self._last_command = None

    @abstractmethod
    def _get_connect_command(self):
        """
        FIXME: Document.
        """

    def send_command(self, command, matches=None, newline=True, timeout=None):
        """
        FIXME: Document.
        """
        # Connect if not connected
        if not self.is_connected():
            self.connect()

        # Create possible expect matches
        if matches is None:
            matches = [self._prompt]

        # Append prefix if required
        if self._prefix is None:
            command = self._prefix + command

        # Save last command in cache to allow to remove echos in get_response()
        self._last_command = command

        # Send line and expect matches
        if newline:
            self._spawn.sendline(command)
        else:
            self._spawn.send(command)

        # Expect matches
        if timeout is None:
            timeout = self._timeout

        match_index = self._child.expect(matches, timeout=timeout)
        return match_index

    def get_response(self):
        """
        FIXME: Document.
        """
        # Convert binary representation to unicode using encoding
        text = self._spawn.before.decode(self._encoding)

        # Remove leading and trailing whitespaces and normalize newlines
        text = text.strip().replace('\r', '')

        # Remove control codes
        text = regex_sub(TERM_CODES_REGEX, '', text)

        # Split text into lines
        lines = text.splitlines()

        # Delete buffer with output right now, as it can be very large
        del text

        # Remove echo command if it exists
        if lines and self._last_command is not None \
                and lines[0].strip() == self._last_command.strip():
            lines.pop(0)

        return '\n'.join(lines)

    def is_connected(self):
        """
        FIXME: Document.
        """
        return self._spawn is not None and self._spawn.isalive()

    def connect(self):
        """
        FIXME: Document.
        """
        if self.is_connected():
            raise Exception('Shell already connected.')

        # Create a child process
        self._spawn = spawn(
            self._get_connect_command().strip(),
            env={'TERM': 'dumb'}, echo=False
        )

        # If connection is via password
        if self._password is not None:
            self._spawn.expect([self._password_match], timeout=self._timeout)
            self._spawn.sendline(self._password)
            self._password = None

        # Execute initial command if required
        if self._initial_command is not None:
            self._spawn.expect(self._initial_prompt, timeout=self._timeout)
            self._spawn.sendline(self._initial_command)

        # Wait for command response to match the prompt
        self._spawn.expect(self._prompt, timeout=self._timeout)

    def disconnect(self):
        """
        FIXME: Document.
        """
        if not self.is_connected():
            raise Exception('Shell already disconnected.')
        self._spawn.close()


__all__ = ['TERM_CODES_REGEX', 'BaseShell', 'PExpectShell']