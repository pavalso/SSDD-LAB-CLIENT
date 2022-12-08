'''
    Iceflix client.
    Developed by Pablo Valverde Soriano
'''

# If not disable, pylint will raise a warning on Ice exceptions.
# pylint: disable=no-name-in-module
# pylint: disable=broad-except

import sys
import os
import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))

try:
    import commands
except ImportError:
    from iceflix import commands


def client_main():
    '''Entry point of the program'''
    commands.show_logo()
    cmd = commands.cli_handler()
        
    try:
        while not cmd.active_conn.reachable:
            prx = cmd.read('Connection proxy: ')
            cmd.onecmd(f'reconnect -p "{prx}"')

        if cmd.active_conn.main and cmd.onecmd('logout'):
            return
        
        cmd.prompt = cmd._generate_prompt()

        sys.exit(cmd.cmdloop())
    finally:
        cmd.shutdown()


if __name__ == '__main__':
    client_main()
