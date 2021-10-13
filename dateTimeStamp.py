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
            comps = [
                ['sdt-d\tdate', now.strftime('%Y-%m-%d')],
                ['sdt-tb\ttime basic', now.strftime('%H:%M:%S')],
                ['sdt-dh\thuman date', now.strftime('%a, %d %b %Y')],
                ['sdt-db\tbasic date', now.strftime('%D')],
                ['sdt-f\tfull', now.strftime('%Y-%m-%dT%H:%M:%S')]
            ]
            return comps
