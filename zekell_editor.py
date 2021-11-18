import sublime
import sublime_plugin

import subprocess as sp
import re
from pathlib import Path
import time

## Need to use the actuall zekell python package instead of the CLI!!!
# find a way to include and import in this plugin

ZKL_COM = '/Users/errollloyd/Developer/zekell/zekell_sqlite/zekell.py'

LINK = '[{title}](/{note_id})'.format
FILE_NAME = '{note_id} {note_title}.md'.format

def insert_at_cursor(edit, view, text):
        sel = view.sel()[0].begin()
        view.insert(edit, sel, text)


class ZekellOpenNoteCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        if not kwargs['note_select']:
            return
        note_id, title = kwargs['note_select']
        file_name = FILE_NAME(note_id=note_id, note_title=title)

        self.view.window().open_file(file_name)

    def input(self, args):
        return NoteSearchInputHandler()


class ZekellInsertLinkCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        # self.view.insert(edit, 0, "Hello, World!")

        selected_note = kwargs['note_select']
        new_link = LINK(title=selected_note[1], note_id=selected_note[0])

        insert_at_cursor(edit, self.view, new_link)

    def input(self, args):
        return NoteSearchInputHandler()


class ZekellInsertTagCommand(sublime_plugin.TextCommand):

    TAG_FRONT_MATTER = '''---\ntags: {}\n---\n'''.format

    def run(self, edit, **kwargs):
        view = self.view
        tag = kwargs['tag_select']


        any_tags = view.find(r'^---\n.*?\n---', 0)
        if any_tags.begin() == -1:
            self.view.insert(edit, 0, self.TAG_FRONT_MATTER(tag))
        else:
            insert_at_cursor(edit, self.view, tag)

    def input(self, args):
        return TagSelectInputHandler()


# > Input Handlers

class TagSelectInputHandler(sublime_plugin.ListInputHandler):

    def list_items(self):
        results = sp.check_output([ZKL_COM, 'sql', '* from full_tag_paths'])

        values = []
        for result in results.decode().splitlines()[1:]:
            cols = result.split(' | ')
            values.append(cols[-1])

        return values

class NoteSearchInputHandler(sublime_plugin.TextInputHandler):

    def placeholder(self) -> str:
        return 'Search query'

    def next_input(self, args):
        return NoteSelectInputHandler(query = args['note_search'])


class NoteSelectInputHandler(sublime_plugin.ListInputHandler):

    def __init__(self, query):

        # presume title search
        if ':' not in query:
            query = f'title: {query}'
        self.results = sp.check_output([
            ZKL_COM, 'q', query])

    def list_items(self):

        values = []
        for result in self.results.decode().splitlines()[1:]:
            note_id, title = result.split(' | ')
            values.append((title, (note_id, title)))

        return values

class NewNoteTitleInputHandler(sublime_plugin.TextInputHandler):

    def placeholder(self):
        return 'New Note Title'


class UpdateNote(sublime_plugin.EventListener):

    def on_post_save(self, view):

        # only update note if in project designated as zekell
        proj_data = view.window().project_data()
        if not (
            proj_data and
            (proj_settings := proj_data.get('settings')) and
            proj_settings.get('is_zekell')
            ):

            return

        note_path = Path(view.file_name())
        note_id = note_path.name.split(' ')[0]

        try:
            _ = sp.check_output([
                ZKL_COM, 'update', note_id
                ])
        except sp.CalledProcessError as e:
            sublime.error_message(f'Updating error: {e}')
        print('AFTER save', view)


class ZekellOpenLinkCommand(sublime_plugin.TextCommand):

    def run(self, edit):

        view = self.view
        window = view.window()

        links = [
            view.substr(r)
            for r in view.find_by_selector('meta.link.inline')
            if r and r.contains(view.sel()[0])
            ]

        if links:
            parsed_link = re.match(r'\[.*?\]\(/(\d*?)\)', links[0])
            if parsed_link:
                note_id = parsed_link.group(1)

                try:
                    output = sp.check_output([
                        ZKL_COM, 'sql',
                        f'title from notes where id = {note_id}'])
                    note_title = output.decode().splitlines()[1:][0]
                    file_name = FILE_NAME(note_id=note_id, note_title=note_title)
                    # print(links)
                    # print(note_id, note_title)
                    print(file_name)
                    window.open_file(file_name)  #type: ignore
                except Exception as e:
                    print('could not get note')
                    print(e)

class ZekellNewNoteCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):

        # window = self.view.window()
        new_title = kwargs['new_note_title']

        output = sp.check_output([
            ZKL_COM, 'add', '-t', new_title])
        new_path = Path(output.decode().strip())

        self.view.window().open_file(new_path.name)

    def input(self, args):
        return NewNoteTitleInputHandler()


class ZekellLinkNewNoteCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):

        # window = self.view.window()
        new_title = kwargs['new_note_title']

        output = sp.check_output([
            ZKL_COM, 'add', '-t', new_title])
        new_path = Path(output.decode().strip())
        new_note_id = new_path.name.split()[0]

        new_link = LINK(title=new_title, note_id=new_note_id)
        insert_at_cursor(edit, self.view, new_link)

        self.view.window().open_file(new_path.name)

    def input(self, args):
        return NewNoteTitleInputHandler()


