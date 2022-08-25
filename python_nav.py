import sublime  # type: ignore
import sublime_plugin  # type: ignore

import re

def get_row(view, selection):
    """Return 0-based row for empty, point-like, Region"""

    return view.rowcol(selection.begin())[0]

def get_total_lines(view):
	return get_row(view, view.line(view.size()))

class GotoNextSymbol(sublime_plugin.TextCommand):
	"""Navigate to a class or function, upward or downward"""

	def run(
			self, edit,
			direction='down',
			# target
			):

		view = self.view
		self.total_lines = get_total_lines(view)

		symbols = view.symbol_regions()

		next_symbol = self.find_next_symbol(symbols, direction)

		if next_symbol:
			view.sel().clear()
			view.sel().add(next_symbol.region.begin())
			view.show(next_symbol.region.begin())

	def symbol_distance(self, current_row, candidate):
		# how many lines to candidate (positive is downward)
		return get_row(self.view, candidate.region) - current_row

	@staticmethod
	def new_idxs(direction, min_idx, max_idx, current_idx, current_distance, new_distance):


		wrong_direction = (
			True
				if
					(direction == 'down' and new_distance < 0) or
					(direction == 'up' and new_distance > 0)
				else
				False
			)

		closer = (
			True
				if (abs(new_distance) - abs(current_distance)) <= 0
				else
				False
			)

		print(
			'DIR', direction, 'CURR DIST, NEW DIST', current_distance, new_distance,
			'WRONG DIR, CLOSER', wrong_direction, closer)

		if wrong_direction:
			if direction == 'down':
				#       new min      new max    new current
				new_vals = (current_idx, max_idx, ((current_idx+max_idx)//2))
			elif direction == 'up':
				new_vals = (min_idx, current_idx, ((min_idx+current_idx)//2))
		# closer + down == wrong_direction + up and vice versa
		# elif closer:
		else:
			if direction == 'down':
				#       new min      new max    new current
				new_vals = (min_idx, current_idx, ((min_idx+current_idx)//2))
			elif direction == 'up':
				new_vals = (current_idx, max_idx, ((current_idx+max_idx)//2))
		# else:
		# 	new_vals = None


		return new_vals


	def find_next_symbol(self, symbols, direction):

		current_row = get_row(self.view, self.view.sel()[0])  # 0 indexed
		symbols_len = len(symbols)

		min_idx = 0
		max_idx = symbols_len
		current_idx = int((current_row / self.total_lines ) * (symbols_len-1))
		print('MIN, MAX, CURR_ROW, CURR_IDX, SYM',
			min_idx, max_idx, current_row, current_idx, symbols[current_idx].name)
		current_distance = self.symbol_distance(current_row, symbols[current_idx])
		# hack to get first comparison
		# should get appropriate split
		new_distance = current_distance - 1

		# best_candidate = {
		# 	'symbol': symbols[current_idx],
		# 	'distance': self.symbol_distance(current_row, symbols[current_idx])}
		for _ in symbols:  # bottom out at going through each symbol!
			new_min_idx, new_max_idx, new_current_idx = self.new_idxs(
				direction, min_idx, max_idx, current_idx, current_distance, new_distance)

			print('NEW_VALS: MIN, MAX, CURR, SYM',
				new_min_idx, new_max_idx, new_current_idx, symbols[new_current_idx].name)
			# if min and max range has narrowed as far as possible
			# we've got our best candidate
			# where the reaching the end of binary search is the criterion
			# if we can only look for the closest
			if (new_max_idx - new_min_idx) <= 2:
				candidates = [
					(idx, self.symbol_distance(current_row, symbols[idx]))
						for idx
						in range(new_min_idx, new_max_idx+1)
					]
				print('candidates', candidates)
				final_symbol = None
				if direction == 'down':
					for idx, dist in candidates:
						if dist >= 0:
							final_symbol = symbols[idx]
							break
				elif direction == 'up':
					for idx, dist in reversed(candidates):
						if dist <= 0:
							final_symbol = symbols[idx]
							break

				print('FINAL', new_min_idx, new_max_idx, idx, final_symbol)
				# _, _
				return final_symbol

			min_idx = new_min_idx
			max_idx = new_max_idx
			current_idx = new_current_idx
			current_distance = new_distance
			new_distance = self.symbol_distance(current_row, symbols[current_idx])
		else:
			return None





