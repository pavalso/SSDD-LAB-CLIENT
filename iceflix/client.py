'''
    Iceflix client.
    Developed by Pablo Valverde Soriano
'''

import sys
import os
import Ice
import cmd2

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))

try:
    import commands
except ImportError:
    from iceflix import commands


RAW_LOGO = r"""
 ██▓ ▄████▄  ▓█████   █████▒██▓     ██▓▒██   ██▒
▓██▒▒██▀ ▀█  ▓█   ▀ ▓██   ▒▓██▒    ▓██▒▒▒ █ █ ▒░
▒██▒▒▓█    ▄ ▒███   ▒████ ░▒██░    ▒██▒░░  █   ░
░██░▒▓▓▄ ▄██▒▒▓█  ▄ ░▓█▒  ░▒██░    ░██░ ░ █ █ ▒
░██░▒ ▓███▀ ░░▒████▒░▒█░   ░██████▒░██░▒██▒ ▒██▒
░▓  ░ ░▒ ▒  ░░░ ▒░ ░ ▒ ░   ░ ▒░▓  ░░▓  ▒▒ ░ ░▓ ░
 ▒ ░  ░  ▒    ░ ░  ░ ░     ░ ░ ▒  ░ ▒ ░░░   ░▒ ░
 ▒ ░░           ░    ░ ░     ░ ░    ▒ ░ ░    ░
 ░  ░ ░         ░  ░           ░  ░ ░   ░    ░
    ░
"""

LOGO = cmd2.ansi.style(RAW_LOGO, fg=cmd2.ansi.RgbFg(175,200,255))

# IceStorm/TopicManager -t:tcp -h localhost -p 10000
def client_main():
    '''Entry point of the program'''

    sys.argv = [__file__] # Avoid executing program arguments once the cmdloop is reached
    cmd = commands.CliHandler()

    cmd.poutput(LOGO)

    try:
        with cmd.terminal_lock:
            prx = cmd.read_input('Connection proxy: ').replace('\"', '')
            cmd.onecmd(f'reconnect -p "{prx}"')
            if not cmd.active_conn.reachable.is_set():
                sys.exit(1)

            if cmd.active_conn.main and cmd.onecmd('logout'):
                return

        cmd.prompt = cmd.get_prompt()

        cmd.cmdloop()
    finally:
        cmd.shutdown()

if __name__ == '__main__':
    client_main()
