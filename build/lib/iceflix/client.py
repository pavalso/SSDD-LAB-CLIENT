'''
    Iceflix client.
    Developed by Pablo Valverde Soriano
'''

# If not disable, pylint will raise a warning on Ice exceptions.
# pylint: disable=no-name-in-module
# pylint: disable=broad-except

import sys

try:
    import commands
except ImportError:
    from iceflix import commands


def client_main():
    '''Entry point of the program'''
    try:
        commands.show_logo()
        cmd = commands.cli_handler()

        if cmd.active_conn.main and cmd.do_logout(None):
            return

        sys.exit(cmd.cmdloop())
    finally:
        if cmd.active_conn.communicator is not None:
            cmd.active_conn.communicator.destroy()


if __name__ == '__main__':
    client_main()
