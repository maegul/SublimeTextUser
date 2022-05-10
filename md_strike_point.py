import sublime
import sublime_plugin
import re
import datetime as dt

STRIKE_TASK = re.compile(r'~~')  # for already struck through
DOT_POINT_TASK = re.compile(r'(^[ \t]*[\*\-\+] )(.*)$')
# 1: date in YYYY-MM-DD format
# 2: optional increment in +wk.days format
# 3: optional separator bn date and remaining time
# 4: remaining time can be enclosed by either 1 or 2 of "*" or "_"
# 5: anything as the remaining time for flexible formats here
# 6: same as 5 for closing
# 6: end of line, so strikethrough won't get matched ... must be last thing on line
# |-->         1                       2           3    4        5  6          7
DD_PAT = r'\(`(\d{2,4}-\d{1,2}-\d{1,2})( ?\+?[\d.]*)`,? ?[\*_]{0,2}.*[\*_]{0,2}\)$'
DD_THRESHOLD = dt.timedelta(days=7)

class MdStrikePointCommand(sublime_plugin.TextCommand):
	"""Strikethrough bullet points, but only the text, not whole line
	"""
	def run(self, edit):
		line = self.view.line(self.view.sel()[0])
		text = self.view.substr(line)

		struck = STRIKE_TASK.search(text)
		if struck:
			new_text = STRIKE_TASK.sub(repl="", string=text)
			self.view.replace(edit, line, new_text)
		elif (match := DOT_POINT_TASK.match(text)):
			new_substr = f"{match[1]}~~{match[2]}~~"
			self.view.replace(edit, line, new_substr)

class MdDeadLineFindCommand(sublime_plugin.TextCommand):
	'''Find deadlines and add remaining time
	'''
	def run(self, edit):
		today=dt.datetime.now()

		# Get deadlines
		# captures first two gorups and puts into dds_text_grps
		dds_text_grps = []
		dds = self.view.find_all(DD_PAT, fmt=r'\1:\2', extractions=dds_text_grps)
		# split two groups for convenience
		dds_text = [
			d.split(':')
			for d in dds_text_grps
			]

		# Process data to create new replacement text
		new_texts = []
		for text in dds_text:

			# process the date increment and create a datetime object
			# of the deadline with the increment added
			date, delta = text
			# check if 4 digit year or 2 digit:
			date_year = date.split('-')[0]
			if len(date_year) == 4:
				strptime_fmt = "%Y-%m-%d"
			elif len(date_year) == 2:
				strptime_fmt = "%y-%m-%d"
			else:
				return

			if delta:
				increment_text=delta.split('+')[1]
				inc_wks, inc_days = increment_text.split('.')
				inc_days = float(inc_days) + (float(inc_wks) * 7)
				inc_td = dt.timedelta(days=inc_days)
				dl = dt.datetime.strptime(date, strptime_fmt) + inc_td
			else:
				dl = dt.datetime.strptime(date, strptime_fmt)

			# calculate time remaining and render the text
			remaining = dl - today
			# formating for the text (italic or bold in md)
			remaining_dec = "*" if remaining >= DD_THRESHOLD else "**"

			# greater than 1 wk, break down to weeks and days (as remainder)
			if abs(remaining.days) > 7:
				n_weeks = remaining.days//7
				week_text = 'wks' if abs(n_weeks) > 1 else 'wk'
				n_days = remaining.days%7
				day_text = 'days' if abs(n_days) > 1 else 'day'
				remaining_text = f"{n_weeks} {week_text} {n_days} {day_text}"
			# less than a week
			else:
				n_days = remaining.days
				day_text = 'days' if abs(n_days) > 1 else 'day'
				remaining_text = f"{n_days} {day_text}"
			# OVERDUE!!
			if remaining.days < 0:
				remaining_text = f"LATE: {remaining_text}"

			# compile new text together
			new_text = f'(`{text[0]}{text[1]}`,{remaining_dec}{remaining_text}{remaining_dec})'
			new_texts.append(new_text)

		# re-write regions in backwards order so that each change doesn't affect the accuracy of the next
		for region, new_text in zip(reversed(dds), reversed(new_texts)):
			self.view.replace(edit, region, new_text)
