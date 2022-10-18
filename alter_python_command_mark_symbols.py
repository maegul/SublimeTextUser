import sublime
import sublime_plugin
import re


class AlterCommentMarkSymbolsCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		view = self.view
		# self.view.insert(edit, 0, "Hello, World!")
		comment_mark_pat = fr'(^\s*# )({args["current_symbol"]}+)(.*)$'
		# matches will be the text of the comment_marks
		matches = []
		comment_marks_regions = view.find_all(
			comment_mark_pat,
			fmt=r'\1\2\3',  # all three groups of the pattern
			extractions=matches)
		# reverse as points start from beginning and won't be affected by alterations if start
		# from the bottom
		reversed_regions = sorted(comment_marks_regions, key=lambda r: r.begin(), reverse=True)
		reversed_matches = list(reversed(matches))
		# print(reversed_regions)
		# print(reversed_matches)
		for region, match in zip(reversed_regions, reversed_matches):
			# just full match again to get the separate groups
			re_match = re.fullmatch(comment_mark_pat, match)
			# full match requires a complete match for the whole string
			# if not a full match, something is wrong ... raise error
			if not re_match:
				raise ValueError(f'Pattern {comment_mark_pat} does not match {match}')
			# new symbol times the number of old symbols were used
			new_symbols = f'{args["new_symbol"]}' * len(re_match.group(2))
			new_text = f'{re_match.group(1)}{new_symbols}{re_match.group(3)}'
			# get region for the full line just in case there is a length difference (necessary?)
			region_line = view.line(region)
			# replace
			view.replace(edit, region_line, new_text)

	def input(self, args):
		return CurrentSymbolInputHandler()

class CurrentSymbolInputHandler(sublime_plugin.TextInputHandler):
	def placeholder(self):
		return "CURRENT"

	def next_input(self, args):
		return NewSymbolInputHandler()

class NewSymbolInputHandler(sublime_plugin.TextInputHandler):
	def placeholder(self):
		return 'NEW'
