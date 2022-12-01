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

cat_tags = cat_get_sub.add_parser('tags')
cat_tags.add_argument('tags', nargs='+')
cat_tags.add_argument('--include', action='store_true')

cat_use = cat_sub.add_parser('use')
cat_use.add_argument('id', type=str)

cat_show = cat_sub.add_parser('show')

selected_parser_base = cmd2.Cmd2ArgumentParser()
selected_parser_sub = selected_parser_base.add_subparsers(title='subcommands')

tags_parser_base = selected_parser_sub.add_parser('tags')
tags_parser_sub = tags_parser_base.add_subparsers(title='actions')

add_tags = tags_parser_sub.add_parser('add')
add_tags.add_argument('tags', nargs='+')

remove_tags = tags_parser_sub.add_parser('remove')
remove_tags.add_argument('tags', nargs='+')

download_parser = selected_parser_sub.add_parser('download')

rename_parser = selected_parser_sub.add_parser('rename')
rename_parser.add_argument('name', type=str)

remove_parser = selected_parser_sub.add_parser('remove')

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

upload_parser = cmd2.Cmd2ArgumentParser()
upload_parser.add_argument('file', type=str)