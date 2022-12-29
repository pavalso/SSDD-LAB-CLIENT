'''
    Iceflix client.
    Developed by Pablo Valverde Soriano
'''

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
    cmd = commands.CliHandler()

    try:
        cmd.terminal_lock.acquire()
        while not cmd.active_conn.reachable.is_set():
            prx = 'IceStorm/TopicManager -t:tcp -h localhost -p 10000'#cmd.read_input('Connection proxy: ').replace('\"', '') # IceStorm/TopicManager -t:tcp -h localhost -p 10000
            cmd.onecmd(f'reconnect -p "{prx}"')
        cmd.terminal_lock.release()

        if cmd.active_conn.main and cmd.onecmd('logout'):
            return

        cmd.prompt = cmd.get_prompt()

        sys.exit(cmd.cmdloop())
    except (KeyboardInterrupt, EOFError):
        cmd.poutput()
    finally:
        cmd.shutdown()


if __name__ == '__main__':
    client_main()
