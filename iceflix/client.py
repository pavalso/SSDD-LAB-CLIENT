'''
    Iceflix client.
    Developed by Pablo Valverde Soriano
'''

# If not disable, pylint will raise a warning on Ice exceptions.
# pylint: disable=no-name-in-module
# pylint: disable=broad-except

import sys
import logging
import shlex

try:
    import commands
except ImportError:
    from iceflix import commands

from Ice import ConnectionRefusedException


def program_loop():
    '''Lets the user authenticate and starts the mini-shell'''

    commands.login()

    while True:
        current_title = f'@{commands.selected_title.info.name}' if commands.selected_title else ''
        command = input(f'{commands.current_session.user}{current_title}> ')
        args = shlex.split(command)

        try:
            if not args:
                args = ['']
            try:
                commands.execute_command(*args)
            except (KeyboardInterrupt, EOFError):
                print('')
        except Exception as error:
            print(
                'An unexpected error has occurred, see the logs for a detailed description')
            logging.exception(error)


def client_main():
    '''Entry point of the program'''
    main_proxy = 'MainAdapter:tcp -p 9999'  # input('Main proxy: '))
    try:
        try:
            commands.initialize_program(main_proxy)
        except ConnectionRefusedException:
            print('The main server is disconnected, exiting...')
            logging.error(
                "Couldn't stablish a connection with the main server")
            sys.exit(111)

        commands.show_logo()

        try:
            program_loop()
        except ConnectionRefusedException:
            logging.error('Connection to the server lost')
    except (KeyboardInterrupt, EOFError):
        pass

    commands.shutdown()


if __name__ == '__main__':
    client_main()
