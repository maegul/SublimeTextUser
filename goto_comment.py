import re
from functools import partial

import sublime
import sublime_plugin

# > Globals

# at some point allow trailing characters of comment characters
# insert just based on specified comment chars or from a list of generics
# that are joined together in an OR regex pattern
# COMMENT_CHARS = {
#     'source.python': r'#'
# }


# > Comment start

# most important setting ... need one for each syntax
COMMENT_START_PATTERNS = {
    # insert comment char     V----- here
    'source.python': [r'^[ \t]*\#+', r'\#'],
    'source.json.sublime.keymap': [r'^[ \t]*\/+']
}

# > Level Characters

DEFAULT_LEVEL_CHAR = r'>'
LEVEL_CHARS = {
    'source.python': r'>'
}

# LEVEL_CHAR_FORMAT_SUB = r'-'

LEVEL_CHAR_FORMAT_SUB = {
    1: '',
    2: r'  - ',
    3: r'   -- ',
    4: r'    --',
    5: r'     --'
}

LEVEL_CHAR_FORMAT_SUB_PATTERNS = {
    scope: {
        # default back to default lvl char, so long as comment_start_pattern is set
        (n*LEVEL_CHARS.get(scope, DEFAULT_LEVEL_CHAR)): sub
        for n, sub in LEVEL_CHAR_FORMAT_SUB.items()
    }
    for scope in COMMENT_START_PATTERNS
}


# > Compiling into complete patterns
# ===========
COMMENT_PATTERNS = {
    scope: r'|'.join([p for p in patterns ])
    for scope, patterns
    in COMMENT_START_PATTERNS.items()
}
COMMENT_PATTERNS
# -----------
# ===========
LEVEL_PATTERNS = {
    scope: (
        # parentheses around pattern important, breaks | off from rest of pattern
        # ie, OR is not greedy
        rf'({pattern})[ ]*({re.escape(LEVEL_CHARS.get(scope, DEFAULT_LEVEL_CHAR))}+)\s*(.+)'
        )
    for scope, pattern
    in COMMENT_PATTERNS.items()
}
LEVEL_PATTERNS
# -----------
EXTRACTION_SEP = r'|:!:|'


# re.findall(COMMENT_PATTERNS['source.python'], '  #')

# present in panel

class GotoCommentCommand(sublime_plugin.TextCommand):

    def run(self, edit):

        self._current_cursor_loc = self.view.sel()[0]
        print('goto comment')

        sections = self.get_section_regions_matches()
        if sections:
            sections = self.update_with_formatted_matches(sections)
            print(sections)
            self.panel(sections)

    def get_section_regions_matches(self):

        pattern = None
        syntax = self.view.syntax()
        if syntax:
            pattern = LEVEL_PATTERNS.get(syntax.scope)

        # should only happen when no comment_start_patterns
        if not (syntax and pattern):
            print(f'No comment patterns configured for current scope')
            return
        print(pattern)

        section_matches = []
        section_regions = self.view.find_all(
            pattern,
            fmt=rf'\2{EXTRACTION_SEP}\3',
            extractions=section_matches)

        sections = {
            'scope': syntax.scope,
            # why note just concretise here!?
            # use python3 they said ... everything's a generator they said!
            'sections': list(zip(section_regions, section_matches))
        }

        return sections

    def update_with_formatted_matches(self, sections):

        if LEVEL_CHAR_FORMAT_SUB:  # if none, don't do this
            scope = sections['scope']
            # should be available by this point,
            # as it means that scope is available in level_chars
            format_sub_patterns = LEVEL_CHAR_FORMAT_SUB_PATTERNS[scope]

            formatted_matches = []
            for section in sections['sections']:
                match = section[1]
                lvl, section_text = match.split(EXTRACTION_SEP)
                # print(match, lvl, section_text)
                formatted_match = f'{format_sub_patterns.get(lvl, lvl)}{section_text}'
                formatted_matches.append(formatted_match)
        else:  # just concretise the generator and extract the matches
            formatted_matches = [
                section[1]
                for section in sections['sections']
            ]

        updated_sections = {
            'formatted_matches': formatted_matches
        }
        updated_sections.update(sections)

        return updated_sections

    # >> Goto function
    def goto_section(self, sections, index):

        # print(sections, index)
        if index == -1:
            region = self._current_cursor_loc
        else:
            region = sections['sections'][index][0]

        self.view.sel().clear()
        self.view.sel().add(region.begin())
        self.view.show(
            region.begin(), show_surrounds=True, keep_to_left=True, animate=False)
        # self.view.run_command('goto_line', {'line': self.view.line(region.begin())})

    def panel(self, sections):

        goto_callback = partial(self.goto_section, sections)
        window = sublime.active_window()
        window.show_quick_panel(
            sections['formatted_matches'],
            on_select=goto_callback, on_highlight=goto_callback
            )

    # def goto_comment_section(self, )


# goto from panel

# get comments

## make table
