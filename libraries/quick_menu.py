#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sublime
from glob import glob

from ..platformio.project_recognition import ProjectRecognition
from .quick_panel import quick_panel
from .paths import getBoardsFileDataPath
from .tools import get_setting, save_setting
from .preferences_bridge import PreferencesBridge
from .serial import serial_port_list
from .I18n import I18n

_ = None

class QuickMenu(PreferencesBridge):
    def __init__(self):
        super(QuickMenu, self).__init__()
        self.index = 0
        self.quick_list = []
        self.deeper = 0

        global _
        _ = I18n().translate

    def quick_boards(self):
        """Boards Menu
        
        Shows the quick panel with the availables boards in
        deviot
        """
        boards_list = self.quick_boards_list()
        quick_panel(boards_list, self.callback_board)

    def callback_board(self, selected):
        """Board Callback
        
        The quick panel returns the index of the option selected,
        this index is used to get the id of the board and the id
        is stored in the setting file.

        last_action is used to run the compilation or upload if was
        the action before call the list of boards
        
        Arguments:
            selected {int} -- index of the selected board
        """
        if(selected == -1):
            save_setting('last_action', None)
            return

        boards_list = self.quick_boards_list()
        board_select = boards_list[selected][-1]
        board_id = board_select.split("|")[-1].strip()

        self.save_selected_board(board_id)
        self.run_last_action()
        self.set_status_information()

    def quick_boards_list(self):
        """Boards List
        
        PlatformIO returns a JSON list with all information of the boards,
        the quick panel requires a list with a different format. We will only
        show the name (caption), id and vendor.
        
        Returns:
            list -- boards list
        """
        from .file import File

        selected_boards = self.get_selected_boards()
        boards_path = getBoardsFileDataPath()
        boards_file = File(boards_path)
        boards = boards_file.read_json()
        boards_list = []

        for board in boards:
            id = board['id']
            vendor = board['vendor']

            if(id in selected_boards):
                start = '- '
            else:
                start = '+ '

            caption = start + board['name']
            extra = "%s | %s" % (vendor, id)
            boards_list.append([caption, extra])

        return boards_list

    def quick_environments(self):
        """Environment Panel
        
        Displays the quick panel with the available environments
        """
        environments_list = self.quick_environment_list()
        quick_panel(environments_list, self.callback_environment, index=self.index)

    def callback_environment(self, selected):
        """Environment Callback
        
        Callback to store the select environment

        last_action is used to run the compilation or upload if was
        the action before call the list of environments
        
        Arguments:
            selected {int} -- option selected (index)
        """
        if(selected == -1):
            save_setting('last_action', None)
            return

        environments_list = self.quick_environment_list()
        environment_select = environments_list[selected][1]
        environment = environment_select.split("|")[-1].strip()

        self.save_environment(environment)
        self.run_last_action()
        self.set_status_information()

    def quick_environment_list(self):
        """
        gets a list with all selected environments and format it
        to be shown in the quick panel
        """
        from .file import File

        environments_list = []
        boards = self.quick_boards_list()
        environments = self.get_selected_boards()
        environment = self.get_environment()
        new_environments = environments

        index = 0
        total = len(environments)
        count = total

        if(environments):
            for value in boards:
                data = value[1].split("|")
                caption = value[0][2:]
                id = data[1].strip()
                vendor = data[0].strip()

                for listed in environments:
                    if(listed == id):
                        vendor = "%s | %s" % (vendor, id)
                        environments_list.append([caption, vendor])
                        new_environments.remove(listed)
                        count -= 1

                        if(environment == listed):
                            self.index = index

                        index += 1

                if(not count):
                    break

        if(new_environments):
            for board in new_environments:
                caption = board
                vendor = "Unknown | {0}".format(board)
                environments_list.append([caption, vendor])

        return environments_list

    def quick_overwrite_baud(self):
        """Upload baud rate
        
        Shows the list of baud rates to override when 
        upload an sketch to a device
        """
        self.quick_list = self.quick_overwrite_baud_list()
        
        quick_panel(self.quick_list, self.callback_overwrite_baud)

    def callback_overwrite_baud(self, selected):
        """Baud rate callback
        
        Stores the option selected in the preferences file
        
        Arguments:
            selected {int} -- index of the selected baud rate
        """
        if(selected == -1):
            return

        selected = self.quick_list[selected]

        if(selected == 'None'):
            selected = None

        save_setting('upload_baudrate', selected)

    def quick_overwrite_baud_list(self):
        """Baud rate list
        
        List of baud rates used to overwrite the upload speed
        
        Returns:
            list -- list of baud rates
        """
        baudrate_list = ["None", "1200", "1800", "2400", "4800", "9600", "19200", "38400", 
                        "57600", "115200", "230400", "460800", "500000", "576000",
                        "921600", "1000000", "1152000"]

        return baudrate_list

    def quick_serial_ports(self):
        """List of Serial Ports
        
        Show the list of serial ports availables in the quick panel
        """
        self.quick_list = self.quick_serial_list()

        quick_panel(self.quick_list, self.callback_serial_ports)

    def callback_serial_ports(self, selected):
        """Selected Port Callback
        
        Stores the selected serial port in the preferences file
        
        Arguments:
            selected {str} -- Port selected ex. 'COM1'
        """
        if(selected <= 0):
            save_setting('last_action', None)
            return

        if(selected == 1):
            self.window.run_command('deviot_set_ip')
            return

        port_selected = self.quick_list[selected][1]
        save_setting('port_id', port_selected)

        self.run_last_action()
        self.set_status_information()

    def quick_serial_list(self):
        """Serial Port List
        
        Gets the list of serial ports and mdns services and
        return it
        
        Returns:
            list -- available serial ports/mdns services
        """

        header = _("select_port_list").upper()
        ports_list = self.get_ports_list()
        ports_list.insert(0, [header])
        ports_list.insert(1, [_("menu_add_ip")])     

        if(len(ports_list) < 2):
            ports_list = [_("menu_no_serial_mdns").upper()]

        return ports_list

    def quick_language(self):
        """Language Panel
        
        Shows the panel to selecte the language of the plugin
        """
        language_list = self.quick_language_list()
        quick_panel(language_list, self.callback_language, index=self.index)

    def quick_language_list(self):
        """Language List
        
        Builts the list with the available languages in Deviot
        
        Returns:
            list -- English language / Language String list
        """

        i18n = I18n()
        index = 0
        language_list = []
        lang_ids = i18n.get_lang_ids()
        current = get_setting('lang_id', 'en')

        for lang_id in lang_ids:
            language = i18n.get_lang_name(lang_id)
            language_list.append([language[1], language[0]])

            if(current == lang_id):
                self.index = index

            index += 1

        return language_list

    def callback_language(self, selected):
        """Language Callback
        
        Stores the user language selection
        
        Arguments:
            selected {int} -- user selection
        """
        if(selected == -1):
            return

        from .top_menu import TopMenu
        
        lang_ids = I18n().get_lang_ids()
        port_selected = lang_ids[selected]
        
        save_setting('lang_id', port_selected)
        save_setting('compile_lang', True)
        self.window.run_command("deviot_reload")


    def quick_import(self):
        """Import Panel
        
        Shows a list of libraries to import in the current sketch
        """
        libraries_list = self.quick_import_list()
        quick_panel(libraries_list, self.callback_import)

    def callback_import(self, selected):
        """Import Callback
        
        After select the library it will be inserted by the insert_libary
        command, it will include the path of the library to includes
        
        Arguments:
            selected {int} -- user index selection
        """
        if(selected <= 0):
            return

        libraries_list = self.quick_import_list()
        library_import = libraries_list[selected][1]

        window = sublime.active_window()
        window.run_command('insert_library', {'path': library_import})

    def quick_import_list(self):
        """Import List
        
        To generate the list of libraries, it search first in the two main folder of the plugin
        the first one in '~/.platformio/packages', that folder contain the libraries includes by default
        by each platform (avr, expressif, etc). The second folder is located in '~/platformio/lib' there
        are stored all the libraries installed by the user from the management libraries
        
        Returns:
            [list] -- quick panel list with libraries
        """
        user_pio_libs = os.path.join('platformio', 'lib')
        libraries_folders = self.get_libraries_folders()
        
        quick_list = self.libraries_list()
        quick_list.insert(0, [_("select_library").upper()])

        if(len(quick_list) <= 1):
            quick_list = [[_("menu_no_libraries")]]

        return quick_list

    def quick_libraries(self):
        """List of libraries
        
        Show the list of libraries availables. The callback will show
        the list of examples.
        """
        self.quick_list = self.libraries_list(example_list=True)
        self.quick_list.insert(0, [_("select_library").upper()])

        if(len(self.quick_list) <= 1):
            self.quick_list = [[_("menu_no_examples")]]

        quick_panel(self.quick_list, self.callback_library)

    def callback_library(self, selected):
        """Show Examples
        
        After the previous selection of the library, here will be search
        all folders inside of the "example" folder and will be considerated
        an example to open
        
        Arguments:
            selected {int} -- user index selection
        """
        if(selected <= 0):
            return

        library_path = self.quick_list[selected][1]
        examples_path = os.path.join(library_path, 'examples', '*')

        self.quick_list = [[_("select_example").upper()]]

        for files in glob(examples_path):
            caption = os.path.basename(files)
            self.quick_list.append([caption, files])

        quick_panel(self.quick_list, self.callback_example)

    def callback_example(self, selected):
        """Open Example
        
        Search the files .ino and .pde in the path of the example selected
        and open it in a new window
        
        Arguments:
            selected {int} -- user index selection
        """
        if(selected <= 0):
            return

        example_path = self.quick_list[selected][1]

        has_file = True
        temp_list = []
        check_path = os.path.join(example_path, '*')
        
        for path in glob(check_path):
            caption = os.path.basename(path)
            temp_list.append([caption, path])
            
            if(not os.path.isfile(path)):
                has_file = False
        
        if(not has_file):
            self.quick_list = temp_list
            self.quick_list.insert(0, [_("select_example").upper()])
            quick_panel(self.quick_list, self.callback_deeper)
            return

        self.open_file(example_path)


    def callback_deeper(self, selected):
        """Examples
        
        If an example folder has more folder (instead of .ino .pde files)
        this method will be  call to show the extra examples
        
        Arguments:
            selected {int} -- user index selection
        """
        if(selected <= 0):
            return

        example_path = self.quick_list[selected][1]

        self.open_file(example_path)
        
    def open_file(self, sketch_path):
        """Open sketch
        
        search in the given path a ino or pde file extension
        and open it in a new windows when it's found
        
        Arguments:
            sketch_path {str} -- path (file/folder) where to search
        """
        window = sublime.active_window()

        if(sketch_path.endswith(('.ino', '.pde'))):
            window.open_file(sketch_path)

        files = os.path.join(sketch_path, '*')
        files = glob(files)

        for file in files:
            if(file.endswith(('.ino', '.pde'))):
                window.open_file(file)

    def libraries_list(self, example_list=False):
        """List of Libraries
        
        Make a list of the libraries availables. This list is
        used in the import library and examples.
        
        Returns:
            [list/list] -- name of folder and path [[name, path]]
        """
        from re import search
        
        platform = self.get_platform()

        platform = platform if(platform) else "all"
        libraries_folders = self.get_libraries_folders(platform)
        
        quick_list = []
        check_list = []

        for library in libraries_folders:
            sub_library = glob(library)

            for content in sub_library:
                caption = os.path.basename(content)
                new_caption = caption.split("_ID")
                if(new_caption is not None):
                    caption = new_caption[0]

                if('__cores__' in content):
                    cores = os.path.join(content, '*')
                    cores = glob(cores)

                    for sub_core in cores:
                        libs_core = os.path.join(sub_core, '*')
                        libs_core = glob(libs_core)

                        for lib_core in libs_core:
                            caption = os.path.basename(lib_core)
                            quick_list.append([caption, lib_core])
                            check_list.append([caption])
                    
                if caption not in quick_list and '__cores__' not in caption and caption not in check_list:
                    store_data = True
                    if(example_list):
                        examples_path = os.path.join(content, 'examples')
                        store_data = True if os.path.exists(examples_path) else False
                    
                    if(store_data):
                        quick_list.append([caption, content])
                        check_list.append(caption)

        return quick_list
