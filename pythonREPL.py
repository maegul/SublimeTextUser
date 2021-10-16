"""
Relies on the PythonREPL.sublime-build and interacts with it

See also key bindings

Remove blank lines in multi line selection

Command for running current line only (shift+enter, like with jupyter?)
Will require a new function, adapted from Sendselectiontoterminus

Ability to mark regions with comments and run whole regions at a time


## ToDo ##
* XXX Command to insert cell markers above and below current location
    * command to remove them also
    * command to merge
    * Command to selectively remove also (?)
* XXX Map cell run to another key binding (shift+enter, with ctrl+enter for just selection)
* XXX Change build process to be direct command like:

****
* maybe port all this to the send code package as a pull request???
****

XXX* AutoIndentation issues with iPython
XXX    * On by default (and helpful)
XXX    * BUT ... autoindents pasted code which breaks it!
XXX    * Can turn off with ipython --no-autoindent
XXX        * BUT ... not working when initialising the REPL with terminus ???
XXX        * Can be turned on manually with "%config TerminalInteractiveShell.autoindent=False"

* Include settings and project settings (especially for shell cmd, environment and REPL command)
    * see window.project_data()
    * Also cell marker strings
    * ...
* Make inclusion of cell bottom marker in REPL optional (it depends on whether line break is part of marker)
* Add capacity to run markdown code blocks


* Use gutter icons with view.add_regions()?
    * can add color, highlighting, gutter icon
    * need options for these too ...

* abstract the backwards find functionality ... as a binary search
* make the find functionality better with more inclusive regex patterns?
"""


import sublime  # type: ignore
import sublime_plugin  # type: ignore

import re
from collections import namedtuple
import time



# as inserting on same line as beg_point, new line to not comment code
CELL_TOP = "# ===========\n"
# as insert on row below last of selection, new line needed so that next line of code is uninterrupted
CELL_BOT = "# -----------\n"

# search for where last line of code has indented code
# as requires multiple new lines to run in ipython
CODE_INDENT_PATTERN = r'\n\s+.+$'

CELL_MARKER = namedtuple('cell_marker', ('row', 'type'))


def get_row(view, selection):
    """Return 0-based row for empty, point-like, Region"""

    return view.rowcol(selection.begin())[0]


def _terminus_view(window, tagName):
    window = window or sublime.active_window()
    for view in window.views():
        if view.settings().get("terminus_view.tag") == tagName:
            return view

    return None


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


class OpenPythonReplViewCommand(sublime_plugin.WindowCommand):
    """Open the REPL in a view on the side

    Should pull from settings or project settings

    Only now opens terminus with appropriate tags.
    Ipython and environment need to be done manually
    """

    def run(self):

        # get project settings for environment command
        try:
            # print(self.window.project_file_name())
            # print(self.window.project_data()['settings'])
            env_command = (
                self.window.project_data()
                .get('settings')
                .get('python_repl')
                .get('env_command')
                )
        except:
            print('Could not find settings for env_command')
            print('reverting to "conda activate general"')
            env_command = 'conda activate general'

        view = self.window.active_view()
        if view is None:
            return None

        terminus_opts = {
            "shell_cmd": f"{env_command} && ipython --no-autoindent",
            "auto_close": "false",
            "title": 'iPython REPL',
            "tag": "python-repl",
            "post_window_hooks": [
                ["carry_file_to_pane", {"direction": "right"}]
            ]
        }

        self.window.run_command(
            'terminus_open', terminus_opts
        )

        # time.sleep(1)
        # self.window.run_command("terminus_send_string",
        #     {
        #         "string": "conda activate general && ipython"
        #     }
        # )


class SendSelectionToTerminusCommand(sublime_plugin.WindowCommand):
    """Run code in a terminal session but interface from code like
    Jupyter

    """

    def run(self, whole_buffer=False, tag=None, visible_only=False):
        view = self.window.active_view()
        if view is None:
            return

        if not whole_buffer:
            # don't worry about multiple selections, just one region at a time
            sel = view.sel()[0]
        else:
            # take whole file/buffer
            sel = sublime.Region(0, len(view))

        # return current line if no selection
        if sel.empty():
            code_region = view.full_line(sel)
        else:
            code_region = sel

        code_text = view.substr(code_region)
        code_text = clean_new_lines(code_text)
        # # make sure only one new line at end of line
        # # though ... when a code block, need two blank lines to cause enter
        # code_text = re.sub(r'\s*$', '\n', code_text)
        # # no blank lines, as python REPL doesn't handle well
        # code_text = re.sub(r'\n\n', '\n', code_text)

        self.window.run_command("terminus_send_string", {
            "string": code_text,
            "tag": tag,
            "visible_only": visible_only})


class SendCellToTerminusCommand(sublime_plugin.WindowCommand):
    """Look for demarcated cells, select inner text and send"""

    def run(self, syntax='python', tag=None, visible_only=False):
        """Find current cell and run"""

        view = self.window.active_view()
        if view is None:
            return

        # Get region of code cell that cursor is currently in
        if syntax == 'python':
            code_region = self.find_cell_in_code(view)  # type: ignore
        elif syntax == 'markdown':
            return
            # ...

        if code_region is None:  # type: ignore
            print('No cell detected')
            return

        code_text = view.substr(code_region)  # type: ignore
        code_text = clean_new_lines(code_text)
        # print('\n\n*******')
        # print(code_text.encode())

        # # no internal blank lines, as python REPL doesn't handle well
        # code_text = re.sub(r'\n{2,}', '\n', code_text)
        # # remove all trailing whitespace
        # code_text = code_text.rstrip()
        # print('after strip')
        # print(code_text.encode())

        # # check if single line
        # if re.search(r'^.*\n', code_text):
        #     # check if last line indented and add double \n if necessary
        #     code_text = re.sub(r'(\n\s+.+)$', r'\1\n\n', code_text)
        #     print('after indent last line')
        #     print(code_text.encode())
        #     # else add new line at end if last line is not indented
        #     code_text = re.sub(r'(\n\S+.*)$', r'\1\n', code_text)
        #     print('after general last line')
        #     print(code_text.encode())
        # else: # single line cell
        #     code_text += '\n'

        self.window.run_command("terminus_send_string", {
            "string": code_text,
            "tag": tag,
            "visible_only": visible_only})

    def find_cell_in_code(self, view):
        """Search for all cell demarcations and define code regions for each
        """

        # presume single cursor
        sel = view.sel()[0]
        sel_row = get_row(view, sel)
        # print(sel, sel_row)

        all_cell_top = view.find_all(
            CELL_TOP, 0)
        all_cell_bottom = view.find_all(
            CELL_BOT, 0)

        # get row number (0-based) of each cell_marker
        early_cell_top_lines = []  # before cursor
        late_cell_top_lines = []  # after cursor
        for cell_top in all_cell_top:
            row = get_row(view, cell_top)
            cell_marker = CELL_MARKER(row=row, type='top')
            if row <= sel_row:
                # top before cursor
                early_cell_top_lines.append(cell_marker)
            elif row > sel_row:
                # top after cursor
                late_cell_top_lines.append(cell_marker)

        early_cell_bottom_lines = []  # before cursor
        late_cell_bottom_lines = []  # after cursor
        for cell_bottom in all_cell_bottom:
            row = get_row(view, cell_bottom)
            cell_marker = CELL_MARKER(row=row, type='bottom')
            if row >= sel_row:
                # bottom after cursor
                late_cell_bottom_lines.append(cell_marker)
            elif row < sel_row:
                # bottom before cursor
                early_cell_bottom_lines.append(cell_marker)

        # print(early_cell_top_lines, early_cell_bottom_lines, late_cell_top_lines, late_cell_bottom_lines)
        # cursor cannot be in cell if no top above or no bottom below
        if (len(early_cell_top_lines) == 0) or (len(late_cell_bottom_lines) == 0):
            return None

        if len(early_cell_bottom_lines) == 0:
            prev_marker = early_cell_top_lines[-1]
        else:
            prev_marker = (
                sorted([early_cell_top_lines[-1], early_cell_bottom_lines[-1]])
                [-1]
            )

        if len(late_cell_top_lines) == 0:
            next_marker = late_cell_bottom_lines[-1]
        else:
            next_marker = (
                sorted([late_cell_top_lines[0], late_cell_bottom_lines[0]])
                [0]
            )

        # cursor not in a cell as not between a top and bottom
        if (prev_marker.type == 'bottom') or (next_marker.type == 'top'):
            return None

        # calculate region of cell
        cell_region = sublime.Region(
            view.text_point(
                prev_marker.row + 1,  # take from line after marker
                0
            ),
            view.text_point(
                next_marker.row, # go up to end marker, but up to first character
                0
            )
        )

        return cell_region

    def find_cell_md(self, view):
        """Get code from fenced code block in markdown"""

        # get point of current cursor location
        cursor_point = view.sel()[0].begin()

        # should return region of whole block of text with
        # the same scope as character under cursor
        code_block_region = view.extract_scope(cursor_point)


class AddCellMarkersCommand(sublime_plugin.TextCommand):
    """Add cell top and bottom markers around current selection"""

    def run(self, edit):

        view = self.view

        # presume single cursor/selection
        sel = view.sel()[0]
        cell_beg_point = view.text_point(
            view.rowcol(sel.begin())[0], 
            0
            )
        cell_end_point = view.text_point(
            view.rowcol(sel.end())[0] + 1,  # insert on line below last line of selection
            0
            )
        # print('\n***')
        # print('sel', sel)
        # print('sel begin rc', view.rowcol(sel.begin()))
        # print('sel end rc', view.rowcol(sel.end()))

        new_char = view.insert(
            edit,
            cell_beg_point,
            CELL_TOP
        )

        # print('end row', sel, view.rowcol(sel.end()))
        view.insert(
            edit,
            cell_end_point + new_char,
            CELL_BOT  
        )

class RemoveAllCellMarkersCommand(sublime_plugin.TextCommand):
    """Remove all CELL_TOP and CELL_BOT markers from file/buffer"""

    def run(self, edit):
        view = self.view

        # reverse so that region offsets remain accurate (bottom to top)
        all_top_regions = reversed(view.find_all(CELL_TOP))

        for reg in all_top_regions:
            view.replace(edit, reg, "")

        all_bot_regions = reversed(view.find_all(CELL_BOT))

        for reg in all_bot_regions:
            view.replace(edit, reg, "")


class GoToNextCellCommand(sublime_plugin.TextCommand):
    """Find and goto next cell top marker from cursor"""

    def run(self, edit, direction='down'):
        view = self.view

        sel = view.sel()[0]

        next_cell = None
        if direction == 'down':
            # add one so that easily find next while at beginning of a cell
            next_cell = view.find(CELL_TOP, sel.b + 1)
        elif direction == 'up':

            sel_row = get_row(view, sel)
            all_cells = view.find_all(CELL_TOP, 0)

            if all_cells is None:
                return

            # This would be better as a complete binary search
            # Only have partial here ... still ... seems fast enough
            n_lines, _ = view.rowcol(view.size())

            if sel_row < (n_lines / 2):
                search_dir = 'down'
            else:
                search_dir = 'up'

            # print('\n***', search_dir)
            if search_dir == 'down':
                candidate_cell = None
                for cell in all_cells:
                    cell_row = get_row(view, cell)
                    # print(cell_row, cell, sel_row, 'candidate', candidate_cell, next_cell)
                    if cell_row >= sel_row:
                        next_cell = candidate_cell
                        # print('found!', next_cell)
                        break
                    else:
                        candidate_cell = cell
            elif search_dir == 'up':
                candidate_cell = None
                for cell in reversed(all_cells):
                    cell_row = get_row(view, cell)
                    # print(cell_row, cell, sel_row, 'candidate', candidate_cell, next_cell)
                    if cell_row < sel_row:
                        next_cell = cell
                        # print('found!', next_cell)
                        break

        # print('found!', next_cell)
        if next_cell is None:
            return None

        # Move cursor to next cell
        view.sel().clear()
        view.sel().add(next_cell.begin())
        view.show(next_cell.begin())


class SampleREPLListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "terminus_tag.exists" or key == "terminus_tag.notexists":
            view = _terminus_view(view.window(), operand)
            return view is not None if key == "terminus_tag.exists" else view is None

        return None
