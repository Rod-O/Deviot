#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import os

from . import paths
from .file import File
from .menu_files import MenuFiles
from .I18n import I18n

_ = I18n().translate

class TopMenu(MenuFiles):
    def __init__(self):
        super(TopMenu, self).__init__()
        self.create_main_menu()

    def create_main_menu(self):
        """Main Menu
        
        Generates the main menu of the plugin.
        The main menu is built from diferents sources, here
        the diferents sources are called to get the data, the
        data is manipulated (ex. translated) and stored as a
        menu file (menu_name.sublime-menu)
        """
        menu_preset = self.get_template_menu('main_menu.json')
        path = paths.getPluginPath()

        for option in menu_preset:
            option = self.translate_children(option)
            for sub in option['children']:
                try:
                    sub = self.translate_children(sub)
                except KeyError:
                    pass


        self.create_sublime_menu(menu_preset, 'Main', path)

    def translate_children(self, option_dict):
        """Translate Children Menu
        
        Translate a children sublime text menu
        
        Arguments:
            option_dict {dict} -- children to be traslated
        
        Returns:
            dict -- children translated
        """
        for children in option_dict['children']:
            children['caption'] = _(children['caption'])

        return option_dict

