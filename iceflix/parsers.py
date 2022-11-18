import sys
import cmd2

reconnect_parser = cmd2.Cmd2ArgumentParser()
reconnect_parser.add_argument('-p', '--proxy', type=str, default=None)

cat_base = cmd2.Cmd2ArgumentParser()
cat_sub = cat_base.add_subparsers(title='actions')
cat_get_base = cat_sub.add_parser('get')
cat_get_sub = cat_get_base.add_subparsers(title='types', help='Search type')

cat_name = cat_get_sub.add_parser('name')
cat_name.add_argument('name', type=str, default=None)
cat_name.add_argument('--exact', required='-name' in sys.argv, action='store_true')

cat_tags = cat_get_sub.add_parser('tags', aliases=['tag'])
cat_tags.add_argument('tags', nargs='+')
cat_tags.add_argument('--include', action='store_true')

cat_use = cat_sub.add_parser('use')
cat_use.add_argument('id', type=str)

cat_show = cat_sub.add_parser('show')

tags_parser = cmd2.Cmd2ArgumentParser()
tags_parser.add_argument('tags', nargs='+', type=str)
tags_parser.add_argument('--add', action='store_true')
tags_parser.add_argument('--remove', action='store_true')

download_parser = cmd2.Cmd2ArgumentParser()

admin_parser = cmd2.Cmd2ArgumentParser()
admin_parser.add_argument('command', nargs='?')
admin_parser.add_argument('arguments', nargs='*')

users_parser_base = cmd2.Cmd2ArgumentParser()
users_parser_sub = users_parser_base.add_subparsers(title='action')

users_add = users_parser_sub.add_parser('add')
users_add.add_argument('user', type=str)
users_add.add_argument('password', type=str)

users_remove = users_parser_sub.add_parser('remove')
users_remove.add_argument('user', type=str)