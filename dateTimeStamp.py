import sublime_plugin
from datetime import datetime


class TimestampCommand(sublime_plugin.EventListener):
    """Complete text with current date time data
    """

    def on_query_completions(self, view, prefix, locations):
        # if prefix in ('isoD', 'now', 'datetime'):
        #     val = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        # elif prefix in ('utcnow', 'utcdatetime'):
        #     val = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

        # elif prefix == 'date':
        #     val = datetime.now().strftime('%Y-%m-%d')

        # elif prefix == 'date_basic':
        #     val = datetime.now().strftime('%d-%b-%y')

        # elif prefix == 'time_basic':
        #     val = datetime.now().strftime('%H:%M:%S')

        # elif prefix == 'timestamp':
        #     val = str(int(time.time()))

        # else:
        #     val = None

        # return [(prefix, prefix, val)] if val else []

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
            ]
            comps = [
                [f'{comp}\t{now_format}', now_format]
                for comp, now_format
                in formats
            ]
            # comps = [
            #     ['sdt-d\tdate', now.strftime('%Y-%m-%d')],
            #     ['sdt-tb\ttime basic', now.strftime('%H:%M:%S')],
            #     ['sdt-db\tbasic date', now.strftime('%d/%m/%Y')],
            #     ['sdt-dh\thuman date', now.strftime('%a, %d %b %Y')],
            #     ['sdt-f\tfull', now.strftime('%Y-%m-%dT%H:%M:%S')]
            # ]
            return comps
