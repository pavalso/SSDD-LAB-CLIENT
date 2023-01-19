'''
    Iceflix client.
    Developed by Pablo Valverde Soriano
'''

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

def client_main():
    '''Entry point of the program'''

    cmd = commands.CliHandler()

    cmd.poutput(LOGO)

    try:
        with cmd.terminal_lock:
            cmd.onecmd('reconnect')
            if not cmd.active_conn.reachable.is_set() or cmd.onecmd('logout'):
                return

        cmd.prompt = cmd.get_prompt()

        cmd.cmdloop()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        cmd.shutdown()

if __name__ == '__main__':
    client_main()
