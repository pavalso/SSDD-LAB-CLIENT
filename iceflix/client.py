import Ice
import logging
import shlex

try:
    import commands
except ImportError:
    import iceflix.commands as commands


def program_loop():

    commands.login()

    while True:
        command = input('{0}{1}> '.format(commands.current_session.user, f'@{commands.selected_title.info.name}' if commands.selected_title else ''))
        args = shlex.split(command)

        try:
            if not args:
                args = ['']
            try:
                commands.execute_command(*args)
            except (KeyboardInterrupt, EOFError):
                print('')
        except Exception as error:
            print('An unexpected error has occurred, see the logs for a detailed description')
            logging.exception(error)

def client_main():
    main_proxy = 'MainAdapter:tcp -p 9999'#input('Main proxy: '))
    try:
        try:
            commands.initialize_program(main_proxy)
        except Ice.ConnectionRefusedException:
            print('The main server is disconnected, exiting...')
            logging.error(f"Couldn't stablish a connection with the main server")
            exit(111)

        commands.show_logo()

        try:
            program_loop()
        except Ice.ConnectionRefusedException:
            logging.error('Connection to the server lost')
    except (KeyboardInterrupt, EOFError):
        pass

    commands.shutdown()

if __name__ == '__main__':
    client_main()
