import sublime_plugin
from datetime import datetime


class TimestampCommand(sublime_plugin.EventListener):
    """Complete text with current date time data
    """

    def on_query_completions(self, view, prefix, locations):

        if prefix == 'sdt':
            now = datetime.now()
            formats = [
                ('sdt-d',   now.strftime('%Y-%m-%d')),
                ('sdt-tb',  now.strftime('%H:%M:%S')),
                ('sdt-db',  now.strftime('%d/%m/%Y')),
                ('sdt-dh',  now.strftime('%d %b %Y')),
                ('sdt-dhf', now.strftime('%a, %d %b %Y')),
                ('sdt-f',   now.strftime('%Y-%m-%dT%H:%M:%S')),
                ('sdt-ftz', now.astimezone().strftime('%Y-%m-%dT%H:%M:%S %Z')),
                ('sdt-wkyr', f'wk {now.isocalendar()[1]}, {now.year}')  # mainly to get week number
            ]
            comps = [
                [f'{comp}\t{now_format}', now_format]
                for comp, now_format
                in formats
            ]
            return comps
