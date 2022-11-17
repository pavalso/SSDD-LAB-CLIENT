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

selected_base = cmd2.Cmd2ArgumentParser()
selected_base.add_argument('tags', nargs='+', type=str)
selected_base.add_argument('--add', action='store_true')
selected_base.add_argument('--remove', action='store_true')
