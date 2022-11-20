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

        prx = 'MainAdapter -t -e 1.1:tcp -h 192.168.1.204 -p 9999 -t 60000'#self.read_input('Connection proxy: ')
        
        cmd.onecmd(f'reconnect -p "{prx}"')

        if cmd.active_conn.main and cmd.onecmd('logout'):
            return
        
        cmd.prompt = cmd._generate_prompt()

        sys.exit(cmd.cmdloop())
    finally:
        cmd.shutdown()


if __name__ == '__main__':
    client_main()
