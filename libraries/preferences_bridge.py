#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

from ..api import deviot
from .tools import get_setting, save_setting
from ..platformio.pio_bridge import PioBridge
from ..libraries.readconfig import ReadConfig

logger = deviot.create_logger('Deviot')


class PreferencesBridge(PioBridge):
    # Flags to be used with last action feature
    COMPILE = 1
    UPLOAD = 2

    def __init__(self):
        super(PreferencesBridge, self).__init__()
        deviot.set_logger_level()
        self.init_option = None

    def save_selected_board(self, board_id):
        """Store Board

        Stores the given board in the preferences file, if the board
        is already in the file, it will be removed

        Arguments:
            board_id {str} -- id of the board ex. 'uno'
        """
        settings = get_setting('boards', [])
        save_flag = True

        if(not settings):
            settings.append(board_id)
        else:
            if(board_id not in settings):
                settings.append(board_id)
            else:
                settings.remove(board_id)
                try:
                    self.remove_ini_environment(board_id)
                except:
                    pass

                if(len(settings) > 0):
                    board_id = settings[-1]
                else:
                    board_id = ''

        save_setting('boards', settings)

        self.save_environment(board_id)

    def get_selected_boards(self):
        """Get Board/s

        List of all boards in the project, the list includes
        the one selected in deviot, and the one initialized in the
        platformio.ini file, they're mixed and excluding the duplicates

        Returns:
            list -- list of boards
        """
        settings = get_setting('boards', [])
        boards = self.get_envs_initialized()

        if(boards):
            settings.extend(boards)

        if(settings):
            settings = list(set(settings))

        return settings

    def save_environment(self, board_id):
        """Save Environment

        Stores the environment/board selected to work with.
        This board will be used to compile the sketch

        Arguments:
            board_id {str} -- id of the board ex. 'uno'
        """
        save_setting('select_environment', board_id)

    def get_environment(self):
        """Get Environment

        Get the environment selected for the project/file in the current view

        Returns:
            str -- environment/board id ex. 'uno'
        """
        settings = get_setting('select_environment', None)

        return settings

    def get_platform(self):
        """Get Platform

        Gets the platform from the current selected environment (board)

        Returns:
            str -- platform name
        """
        from .file import File

        environment = self.get_environment()

        boards_path = deviot.boards_file_path()
        boards_file = File(boards_path)
        boards = boards_file.read_json()

        for board in boards:
            if(board['id'] == environment):
                return board['platform'].lower()

    def get_ports_list(self):
        """Ports List

        Get the list of serial port and mdns services and return it

        Returns:
            list -- serial ports / mdns services
        """
        from .serial import serial_port_list

        ports_list = serial_port_list()
        services = self.get_mdns_services()

        ports_list.extend(services)

        return ports_list

    def get_serial_port(self):
        """Serial Port Selected

        Get the serial port stored in the preferences file

        Returns:
            str -- port id ex 'COM1'
        """
        port_id = get_setting('port_id', None)

        return port_id

    def read_pio_preferences(self):
        """Reads data/preferences

        Reads the information stored in the platformio.ini file and
        load it in deviot
        """
        ini_path = self.get_ini_path()

        # open platformio.ini to read the preferences
        config = ReadConfig()
        config.read(ini_path)

        environment = 'env:{0}'.format(self.board_id)

        # stop if environment wasn't initialized yet
        if(not config.has_section(environment)):
            return

        programmer_list = {
            'stk500v1': 'check',
            'stk500v2': 'avrmkii',
            'usbtiny': 'usbtiny',
            'arduinoisp': 'arduinoisp',
            'usbasp': 'usbasp',
            'dapa': 'parallel'
        }

        if(config.has_option(environment, 'upload_protocol')):
            option = config.get(environment, 'upload_protocol')[0]

            programmer = programmer_list[option]
            if(programmer == 'check'):
                flags = config.get(environment, 'upload_flags')
                if(flags == '-P$UPLOAD_PORT'):
                    option = 'avr'
                else:
                    option = 'arduinoasisp'
        else:
            option = False
        save_setting('programmer_id', option)

    def run_last_action(self):
        """Last Action

        If the user start to compile or upload the sketch and none board or
        port is selected, the quick panel is displayed to select the
        corresponding option.
        As the quick panel is a async method, the compilation or upload will
        not continue. Before upload or compile a flag is stored to what run
        after the selection
        """
        from .tools import get_sysetting
        last_action = get_sysetting('last_action', None)
        try:
            last_action = int(last_action)
        except:
            pass

        if(last_action == self.COMPILE):
            from ..platformio.compile import Compile
            Compile()
        elif(last_action == self.UPLOAD):
            from ..platformio.upload import Upload
            Upload()

    def programmer(self, wipe=False):
        """Programmer

        Adds the programmer strings in the platformio.ini file, it considerate
        environment and programmer selected

        Arguments:
            programmer {str} -- id of chosen option
        """
        logger.debug("==============")
        logger.debug("programmer")

        write_file = False
        ini_path = self.get_ini_path()
        programmer = get_setting('programmer_id', None)

        # open platformio.ini and get the environment
        config = ReadConfig()
        config.read(ini_path)
        environment = 'env:{0}'.format(self.board_id)

        # stop if environment wasn't initialized yet
        if(not config.has_section(environment)):
            return

        options = ['upload_protocol', 'upload_flags', 'upload_speed', 'upload_port']

        # remove previous configuration
        if(config.has_option(environment, options[0])):
            for option in options:
                config.remove_option(environment, option)
                write_file = True

        # add programmer option if it was selected
        if(programmer and not wipe):
            if(programmer == 'avr'):
                config.set(environment, 'upload_protocol', 'stk500v1')
                config.set(environment, 'upload_flags', '-P$UPLOAD_PORT')
                config.set(environment, 'upload_port', self.port_id)
            elif(programmer == 'avrmkii'):
                config.set(environment, 'upload_protocol', 'stk500v2')
                config.set(environment, 'upload_flags', '-Pusb')
            elif(programmer == 'usbtiny'):
                config.set(environment, 'upload_protocol', 'usbtiny')
            elif(programmer == 'arduinoisp'):
                config.set(environment, 'upload_protocol', 'arduinoisp')
            elif(programmer == 'usbasp'):
                config.set(environment, 'upload_protocol', 'usbasp')
                config.set(environment, 'upload_flags', '-Pusb')
            elif(programmer == 'parallel'):
                config.set(environment, 'upload_protocol', 'dapa')
                config.set(environment, 'upload_flags', '-F')
            elif(programmer == 'arduinoasisp'):
                config.set(environment, 'upload_protocol', 'stk500v1')
                config.set(environment, 'upload_flags', '-P$UPLOAD_PORT -b$UPLOAD_SPEED')
                config.set(environment, 'upload_speed', '19200')
                config.set(environment, 'upload_port', self.port_id)
            write_file = True

        # save in file
        if(write_file):
            logger.debug("write ini file")
            with open(ini_path, 'w') as configfile:
                config.write(configfile)

    def add_option(self, option_name, wipe=False, append=False):
        """Add option

        Adds the option `option_name` into platformio.ini. The value
        of this option will be get from the setting file

        Arguments:
            option_name {str} -- name of the value

        Keyword Arguments:
            wipe {bool} -- when is true remove the option
                            from platformio.ini (default: {False})
            append {bool} -- when is true, when is true it appends
                            the given data
        """
        logger.debug("==============")
        logger.debug("add_option")
        logger.debug("option_name %s", option_name)
        logger.debug("wipe %s", wipe)

        option = get_setting(option_name, None)
        ini_path = self.get_ini_path()
        write_file = False

        logger.debug("option %s", option)

        config = ReadConfig()
        config.read(ini_path)

        environment = 'env:{0}'.format(self.board_id)
        if(not config.has_section(environment)):
            return

        current = config.get(environment, option_name)

        if(not current):
            current = []

        # get current value
        if(not wipe and config.has_option(environment, option_name)):
            self.init_option = config.get(environment, option_name)[0]
            logger.debug("init_option %s", self.init_option)

        # add option
        if(not wipe and option and option not in current):
            if(self.init_option and append):
                option = self.init_option + ', ' + option

            config.set(environment, option_name, option)
            write_file = True
            logger.debug("write_file1 %s", write_file)

        # remove in case to be neccesary
        if(wipe or (not option and self.init_option != option)):
            config.remove_option(environment, option_name)
            write_file = True
            logger.debug("write_file2 %s", write_file)

        # save in file
        if(write_file):
            logger.debug("write ini file")
            with open(ini_path, 'w') as configfile:
                config.write(configfile)

    def get_mdns_services(self):
        """mDNS services

        Returns the list of instances found in the multicast dns
        (local network)

        Returns:
            list -- device info
        """
        from .mdns.mdns import MDNSBrowser

        MDNS = MDNSBrowser()
        MDNS.start()

        return MDNS.formated_list()

    def set_status_information(self):
        """Status bar Information

        Show the board and serial port selected by the user
        """
        from .project_check import ProjectCheck
        version = deviot.version()

        show_info = get_setting('status_information', True)

        if(ProjectCheck().is_iot() and show_info):
            board_id = self.get_environment()
            port_id = self.get_serial_port()

            board_id = board_id.upper() if (board_id) else ' - '
            port_id = port_id.upper() if (port_id) else ' - '

            if(board_id or port_id or 'dev' in version):
                info = "{0} | {1}".format(board_id, port_id)
                info += " | Deviot {0}".format(version)

                self.view.set_status('_deviot_extra',  info)
        else:
            self.view.erase_status('_deviot_extra')
