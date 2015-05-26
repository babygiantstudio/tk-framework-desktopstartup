# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Console based authentication. This module implements UX and prompting for a 
workflow where the user gets prompted via stdin/stdout.

--------------------------------------------------------------------------------
NOTE! This module is part of the authentication library internals and should
not be called directly. Interfaces and implementation of this module may change
at any point.
--------------------------------------------------------------------------------
"""

from . import session_cache
from .errors import AuthenticationError, AuthenticationCancelled

from getpass import getpass
import logging

logger = logging.getLogger("sg_auth.console")


class ConsoleAuthenticationHandlerBase(object):
    """
    Base class for authenticating on the console. It will take care of the credential retrieval loop,
    requesting new credentials as long as they are invalid or until the user provides the right one
    or cancels the authentication. This class should not be instantiated directly, instead it is used
    through the authenticate and renew_session methods.
    """

    def authenticate(self, hostname, login, http_proxy):
        """
        Prompts the user for this password to retrieve a new session token and rewews
        the session token.
        :param hostname: Host to renew a token for.
        :param login: User to renew a token for.
        :param http_proxy: Proxy to use for the request. Can be None.
        :returns: The (hostname, login, session token) tuple.
        :raises AuthenticationCancelled: If the user aborts the login process, this exception
                                         is raised.

        """
        logger.debug("Requesting password on command line.")
        while True:
            # Get the credentials from the user
            try:
                hostname, login, password = self._get_user_credentials(hostname, login)
            except EOFError:
                # Insert a \n on the current line so the print is displayed on a new time.
                print
                raise AuthenticationCancelled()

            session_token = self._get_session_token(hostname, login, password, http_proxy)
            if session_token:
                return hostname, login, session_token

    def _get_user_credentials(self, hostname, login):
        """
        Prompts the user for his credentials.
        :param host Host to authenticate for.
        :param login: User that needs authentication.
        :param http_proxy: Proxy to connect to when authenticating.
        :returns: A tuple of (hostname, login, password)
        :raises AuthenticationCancelled: If the user cancels the authentication process,
                this exception will be thrown.
        """
        raise NotImplementedError

    def _get_password(self):
        """
        Prompts the user for his password. The password will not be visible on the console.
        :raises: AuthenticationCancelled If the user enters an empty password, the exception
                                         will be thrown.
        """
        password = getpass("Password (empty to abort): ")
        if not password:
            raise AuthenticationCancelled()
        return password

    def _get_keyboard_input(self, label, default_value=""):
        """
        Queries for keyboard input.
        :param label: The name of the input we require.
        :param default_value: The value to use if the user has entered no input.
        :returns: The user input or default_value if nothing was entered.
        """
        text = label
        if default_value:
            text += " [%s]" % default_value
        text += ": "
        user_input = None
        while not user_input:
            user_input = raw_input(text) or default_value
        return user_input

    def _get_session_token(self, hostname, login, password, http_proxy):
        """
        Retrieves a session token for the given credentials. If it fails, the user is informed
        :param hostname: The host to connect to.
        :param login: The user to get a session for.
        :param password: Password for the user.
        :param http_proxy: Proxy to use. Can be None.
        :returns: If the credentials were valid, returns a session token, otherwise returns None.
        """
        try:
            return session_cache.generate_session_token(hostname, login, password, http_proxy)
        except AuthenticationError:
            print "Login failed."
            return None


class ConsoleRenewSessionHandler(ConsoleAuthenticationHandlerBase):
    """
    Handles session renewal. Prompts for the user's password. This class should
    not be instantiated directly and be used through the authenticate and
    renew_session methods.
    """
    def _get_user_credentials(self, hostname, login):
        """
        Reads the user password from the keyboard.
        :param hostname: Name of the host we will be logging on.
        :param login: Current user
        :returns: The user's password.
        """
        print "%s, your current session has expired." % login
        print "Please enter your password to renew your session for %s" % hostname
        return hostname, login, self._get_password()


class ConsoleLoginHandler(ConsoleAuthenticationHandlerBase):
    """
    Handles username/password authentication. This class should not be
    instantiated directly and be used through the authenticate and renew_session
    methods.
    """
    def __init__(self, fixed_host):
        super(ConsoleLoginHandler, self).__init__()
        self._fixed_host = fixed_host

    def _get_user_credentials(self, hostname, login):
        """
        Reads the user credentials from the keyboard.
        :param hostname: Name of the host we will be logging on.
        :param login: Default value for the login.
        :returns: A tuple of (login, password) strings.
        """
        if self._fixed_host:
            print "Please enter your login credentials for %s" % hostname
        else:
            print "Please enter your login credentials."
            hostname = self._get_keyboard_input("Host", hostname)
        login = self._get_keyboard_input("Login", login)
        password = self._get_password()
        return hostname, login, password
