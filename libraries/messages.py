# !/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of the uPiot project, https://github.com/gepd/upiot/
#
# MIT License
#
# Copyright (c) 2017 GEPD
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sublime
import sublime_plugin

import collections
import threading

from ..api import deviot
from .tools import findInOpendView, get_setting
from .I18n import I18n

session = {}
close_panel = False
viewer_name = 'Deviot Viewer'


class Messages:
    port = None
    window = None
    text_queue = collections.deque()
    text_queue_lock = threading.Lock()

    def __init__(self, output_view=None):
        self.translate = I18n().translate
        self.output_view = output_view
        self._init_text = None
        self._name = None

    def initial_text(self, text, *args):
        """Intial message

        Sets the initial string to be push when the Messages instance is
        created

        Arguments:
            text {str} -- string to display
            *args {str} -- arguments to be replaced in the text string
        """
        self._init_text = self.translate(text, *args)

    def panel_name(self, text, *args):
        """Panel name

        Sets the name of the panel when it will be a ST window

        Arguments:
            text {str} -- string to name the panel
            *args {str} -- arguments to be replaced in the text string
        """
        self._name = self.translate(text, *args).strip('\\n')

    def create_panel(self, direction='right', in_file=False):
        """
        Start the print module, if the window was already created
        it's recovered.
        """
        global session

        self.window = sublime.active_window()

        if(not self.output_view and not self.recover_panel(self._name)):
            self.select_output(in_file, direction)

        if(not in_file):
            self.window.run_command("show_panel", {"panel": "output.deviot"})

        # change focus to the panel
        self.set_focus()

        # print initial message
        if(self._init_text):
            self.print(self._init_text)

        # store the session to close the panel in the future
        if(self._name):
            session[self._name] = self

    def select_output(self, in_file, direction):
        """Panel Output

        Selects where the content will be printed, it can be the ST console
        or in a new buffer (view)

        Arguments:
            in_file {bool} -- if it's true a new view will be created

        Keyword Arguments:
            name {str} -- name of the new view (default: {''})
        """
        if(in_file):
            self.output_view = self.new_file_panel(direction)
        else:
            package_name = deviot.plugin_name()
            syntax = "Packages/{0}/Console.tmLanguage".format(package_name)

            self.output_view = self.window.create_output_panel('deviot')
            self.output_view.assign_syntax(syntax)
        self.output_view.set_read_only(True)

    def set_focus(self):
        """Set focus

        Sets the focus to the console window
        """
        window = sublime.active_window()
        window.focus_view(self.output_view)

    def print(self, text, *args):
        """
        Adds the string in the deque list
        """
        # translate strings before append
        text = I18n().translate(text, *args)

        self.text_queue_lock.acquire()
        try:
            if(type(text) == bytes):
                text = text.decode('utf-8')
            self.text_queue.append(text)
        finally:
            self.text_queue_lock.release()

        sublime.set_timeout(self.service_text_queue, 0)

    def service_text_queue(self):
        """
        Handles the deque list to print the messages
        """
        self.text_queue_lock.acquire()

        is_empty = False
        try:
            if(len(self.text_queue) == 0):
                return

            characters = self.text_queue.popleft()
            is_empty = (len(self.text_queue) == 0)

            self.send_to_file(characters)

        finally:
            self.text_queue_lock.release()

        if(not is_empty):
            sublime.set_timeout(self.service_text_queue, 1)

    def send_to_file(self, text):
        """
        Prints the text in the window
        """

        # Cleans output at the 2000 lines, and when auto clean is activated
        size = self.output_view.size()
        auto_clean = get_setting('auto_clean', True)

        if(auto_clean and size > 80 * 20000):  # 20000 lines of 80 charactes
            self.clean_view()

        # append text
        text = text.replace('\r\n', '\n'). replace('\r', '\n')

        # fix only end of lines
        if('\\n' in text[-2:]):
            text = text.replace('\\n', '\n')

        self.output_view.run_command('append', {
                                     'characters': text, "force": True})

        # check automatic scroll option
        automatic_scroll = get_setting('automatic_scroll', True)
        if(len(self.output_view.sel()) > 0 and
           automatic_scroll or not self._name):

            line = self.output_view.rowcol(size)[0] + 1
            self.output_view.run_command("goto_line", {"line": line})

    def clean_view(self):
        """Clean message view

        Cleans all characters in the output_view
        """
        self.window.focus_view(self.output_view)
        self.window.run_command('deviot_clean_view')

    def first_message(self):
        """Deviot console message

        Method to print a message when deviot console is not yet created but
        the "show deviot console" is called
        """
        self.print('_deviot_{0}', deviot.version())
        self.print('deviot_info')

    def recover_panel(self, name):
        """
        Recover the message window object
        """

        window, view = findInOpendView(name)

        if(view):
            self.output_view = view
        return bool(view)

    def new_file_panel(self, direction):
        """Create an empty new file sheet

        Creates an empty sheet to be used as console

        Arguments:
            name {str} -- name to set in the ST view
            direction {str} -- Where the window will be located. options
                               available:
                            'self', 'left', 'right', 'up', 'down'

        Returns:
            obj -- Sublime Text view buffer
        """
        window = sublime.active_window()
        window_position = get_setting('window_position', 1)

        word_wrap = {'setting': 'word_wrap'}
        options = {'direction': direction, 'give_focus': True}

        if(window_position >= 2):
            count_groups = window.num_groups()
            if(count_groups >= window_position):
                group_position = window_position
            else:
                group_position = count_groups

            options['direction'] = 'self'
            # Remove one because it's an index
            window.focus_group(group_position - 1)

        window.run_command('deviot_create_pane', args=options)

        view = window.new_file()
        view.set_name(self._name)
        view.run_command('toggle_setting', word_wrap)
        view.set_scratch(True)

        return view

    def on_pre_close(self, view):
        self.window = view.window()

    def on_close(self, view):
        if(view.name() not in session):
            return

        if(check_empty_panel(self.window)):
            close_panel(self.window)
            self.window = None


def check_empty_panel(window):
    """
    If there is an empty panel will make it active

    Returns:
        bool -- True if there is an empty panel false if not
    """
    num = window.num_groups()

    for n in range(0, num):
        if(not window.views_in_group(n)):
            window.focus_group(n)
            return True
    return False


def close_panel(window):
    close_panel = get_setting('auto_close_panel', True)
    if(not close_panel):
        return

    window.run_command("deviot_destroy_pane", args={"direction": "self"})
