"""
Relies on the PythonREPL.sublime-build and interacts with it

See also key bindings

Remove blank lines in multi line selection

Command for running current line only (shift+enter, like with jupyter?)
Will require a new function, adapted from Sendselectiontoterminus

Ability to mark regions with comments and run whole regions at a time

"""
# # Imports

import sublime  # type: ignore
import sublime_plugin  # type: ignore

from typing import cast, Optional, List, Tuple

import re
from collections import namedtuple
import socket
import time

# # Constants

ERROR_MSG_PREFIX = "MD Repl ERROR: "

# # Cell markers

CELL_TOP = r"^```\w+$"
CELL_BOT = r"^```$"


# >> Remove escape sequences
CELL_TOP_TEXT = CELL_TOP.replace('\\', '')
CELL_BOT_TEXT = CELL_BOT.replace('\\', '')

# search for where last line of code has indented code
# as requires multiple new lines to run in ipython
CODE_INDENT_PATTERN = r'\n\s+.+$'


# # Settings Management

SETTINGS_NAME = 'md_repl.sublime-settings'

# default empty, should be filled by config retrieval
MD_REPL_SOCKET_PATHS: dict = {}


def get_config():
    settings = sublime.load_settings(SETTINGS_NAME)

    socket_paths = settings.get('md_repl_socket_paths')
    socket_paths = cast(dict, socket_paths)

    if not socket_paths:
        print(f'{ERROR_MSG_PREFIX}Socket paths not found in settings')
        return

    global MD_REPL_SOCKET_PATHS
    MD_REPL_SOCKET_PATHS = socket_paths
    print(f'MD Repl Socket Paths: {socket_paths}')

def get_socket_path(syntax) -> Optional[str]:
    return MD_REPL_SOCKET_PATHS.get(syntax)



# # Utilities


class MarkdownNotebookReloadSettingsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        get_config()


def get_row(view: sublime.View, selection: sublime.Region):
    """Return 0-based row for empty, point-like, Region"""

    return view.rowcol(selection.begin())[0]


def clean_new_lines(code_text):
    """Removes blank lines and adds new lines at end for running code"""

    # print('\n\n*******')
    # print(code_text.encode())

    # no internal blank lines, as python REPL doesn't handle well
    code_text = re.sub(r'\n{2,}', '\n', code_text)
    # remove all trailing whitespace
    code_text = code_text.rstrip()
    # print('after strip')
    # print(code_text.encode())

    # check if single line
    if re.search(r'^.*\n', code_text):
        # check if last line indented and add double \n if necessary
        code_text = re.sub(r'(\n\s+.+)$', r'\1\n\n', code_text)
        # print('after indent last line')
        # print(code_text.encode())
        # else add new line at end if last line is not indented
        code_text = re.sub(r'(\n\S+.*)$', r'\1\n', code_text)
        # print('after general last line')
        # print(code_text.encode())
    else:  # single line cell
        code_text += '\n'

    return code_text


# # Socket Objext

def mk_socket_connection(socket_path: str) -> socket.socket:

    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client_socket.connect(socket_path)
    except socket.error as e:
        print(f"Socket error: {e}")
        raise e
        # client_socket = None

    return client_socket

def send_recv_socket_data(
        client_socket: socket.socket, input_data: str,
        timeout: float = 0.15, buff_size: int = 4096
        ) -> Optional[str]:

    try:
        # Set a timeout to prevent indefinite blocking
        client_socket.settimeout(timeout)

        # Send data with a newline to trigger processing on the server side
        client_socket.sendall((input_data + "\n").encode('utf-8'))

        # Read the response, handling the socket's blocking nature properly

        data = []

        try:
            while True:
                chunk = client_socket.recv(buff_size)
                if not chunk:
                    break
                data.append(chunk)
        except socket.timeout:
            pass  # Timeout indicates no more data is available

        return b''.join(data).decode('utf-8')

    except socket.error as e:
        print(f"Socket communication error: {e}")
        return None



# # Load config when plugin loaded
def plugin_loaded():
    get_config()


# # Plugin Proto

# can run in console with `view.run_command('set_repl...', {'socket_path', '...'})`
class MarkdownNotebookSetReplSocketPathCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwd: str):
        socket_path = kwd['socket_path']

        try:
            c = mk_socket_connection(socket_path)
        except Exception as e:
            print(f'{ERROR_MSG_PREFIX}socket path invalid')
            sublime.error_message(
                f"{ERROR_MSG_PREFIX}Failed to connect to new socket path: {socket_path}")
            return
        else:
            c.close()

        settings = self.view.settings()
        settings.set('md_repl_socket_path', socket_path)

        new_path = settings.get('md_repl_socket_path')
        print(f'new path set to {new_path}')



class MarkdownNotebookSendCellToReplCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):

        insert_output: Optional[bool] = kwargs.get('insert_output')

        view = self.view
        current_cursor = view.sel()[0]

        # ## Check markdown code cell
        current_scope = view.scope_name(current_cursor.b).rstrip().split(" ")
        # print("md repl, current scope: ", current_scope)
        is_md_code_cell = all((
                'markdown' in current_scope[0],  # first scope should have markdown (?)
                any((
                    'code-fence' in s
                    for s in current_scope[1:]
                    ))
            ))

        if not is_md_code_cell:
            print("MD Repl ERROR: Not a code cell/block!")
            return

        # ## Extract Code
        cell_region_data = self.extract_code_cell_region(view)
        if cell_region_data is None:  # failed to get
            return

        cell_region, cell_top_line = cell_region_data

        cell_text = view.substr(cell_region)
        # get cell syntax
        cell_top_syntax_region = view.line(view.text_point(cell_top_line, 0))
        cell_top_text = view.substr(cell_top_syntax_region)
        cell_syntax_match = re.fullmatch(r'^```(\w+)$', cell_top_text)
        if not cell_syntax_match:
            print(f'{ERROR_MSG_PREFIX}Failed to extract syntax from {cell_top_text} at line {cell_top_line+1}')
            return
        cell_syntax = cell_syntax_match.group(1)

        # print(repr(cell_text))
        # cleaned_cell_text = clean_new_lines(cell_text)
        # print(repr(cleaned_cell_text))

        # ## Connect to Socket

        socket_path_data = MD_REPL_SOCKET_PATHS.get(cell_syntax)
        socket_path = socket_path_data.get('path')  # type: ignore

        # have a default I guess
        if not socket_path:
            socket_path = '/tmp/soc'

        try:
            c = mk_socket_connection(socket_path)
        except Exception as e:
            print(f"{ERROR_MSG_PREFIX}socket error connecting to {socket_path}:\n{e}")
            return

        # ## Send code to socket

        try:
            # print('trying to send command?')
            output_text = send_recv_socket_data(c, cell_text)
            # print(f"output:\n{output_text}")
            c.close()

            if output_text:
                # perhaps bad idea to strip whitespace before and after
                # rstrip or perhaps just removing blank lines at beginning or end??
                output_text = output_text.strip()
                # output_text = output_text.rstrip()
                self.insert_output(view, edit, cell_region, output_text, insert_output)

        except Exception as e:
            print(f"{ERROR_MSG_PREFIX}socket error:{e}")
        finally:
            # ??
            c.close()



    def extract_code_cell_region(
            self, view: sublime.View
            ) -> Optional[Tuple[sublime.Region, int]]:

        sel = view.sel()[0]
        sel_row = get_row(view, sel)

        # get all cell markers
        try:
            all_cell_top = view.find_all(CELL_TOP, 0)
            all_cell_bottom = view.find_all(CELL_BOT, 0)
        except:
            ff = sublime.FindFlags(0)
            all_cell_top = view.find_all(CELL_TOP, ff)
            all_cell_bottom = view.find_all(CELL_BOT, ff)


        # sort into top-cell-markers before and bottom-cell-markers after cursor

        early_cell_top_lines: List[int]  = []
        for cell_top in all_cell_top:
            row = get_row(view, cell_top)
            # if past cursor, stop
            if row > sel_row:
                break
            # before or at cursor ... append
            else:
                early_cell_top_lines.append(row)

        late_cell_bottom_lines: List[int] = []
        # going in reversed direction (should be bottom of file upward)
        for cell_bottom in reversed(all_cell_bottom):
            row = get_row(view, cell_bottom)
            # if earlier than cursor, stop
            if row < sel_row:
                break
            else:
                late_cell_bottom_lines.append(row)

        if (len(early_cell_top_lines) == 0) or (len(late_cell_bottom_lines) == 0):
            print(f"{ERROR_MSG_PREFIX}Cursor not in cell. Failed to find top & bottom")
            return None

        cell_top = early_cell_top_lines[-1]
        cell_bottom = late_cell_bottom_lines[-1]  # as done in reverse, last is closest
        cell_region = sublime.Region(
                view.text_point(cell_top + 1, 0),  # add 1 to take code inside
                view.text_point(cell_bottom, 0),
            )

        return cell_region, cell_top

    def insert_output(
            self, view: sublime.View, edit,
            cell_region: sublime.Region, output_text: str,
            insert_output: Optional[bool]
            ):

        # print('inserting output')
        # current_cursor = view.sel()[0]

        # bottom of current code cell
        cell_bottom_line = view.rowcol(cell_region.end())[0]

        # output cell exists?
        line_after_cell = view.text_point(cell_bottom_line+1, 0)
        output_region = view.find(r'(?sm)^>\n```\n.*?\n```\n', line_after_cell)

        # is output_region directly below current cell?
        # necessary, as find will get the next output region in the document
        # ... which can belong to the next code cell or any other below
        output_region_is_for_this_cell = output_region.begin() == line_after_cell

        # if so erase
        if output_region and output_region_is_for_this_cell:
            view.erase(edit, output_region)

        # add a new one
        if insert_output:
            new_output_text = f">\n```\n{output_text}\n```\n"
            view.insert(edit, line_after_cell, new_output_text)
