import sublime
import sublime_plugin
import re

DOT_POINT_TASK = re.compile(r'(^[ \t]*[\*\-\+] )(.*)$')


class MdStrikePointCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		line = self.view.line(self.view.sel()[0])
		match = DOT_POINT_TASK.match(self.view.substr(line))

		if match:
			new_substr = f"{match[1]}~~{match[2]}~~"
			# print(new_substr)
			self.view.replace(edit, line, new_substr)

