"""Quick navigation to the next symbol above or below


"""
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
		"""Produce new indices that narrow the search down

		Main approach is check if wrong direction, and then use the current candidate
		index as a new min or max index (depending on the direction and whether
		the candidate is or is not in the wrong direction).

		Also, given that new candidate indices are produces by using (min+max)//2, which
		truncates downard (ie 1.9//1 = 1 and not 2), there are "+1" for when moving downward.
		Hopefully this makes the "algorithm" correct?

		Ideally, this function can be relied on to actually find the final target
		when the range of indices is narrowed down to 1 (max-min = 1), which means there
		are only two candidates ... and HOPEFULLY that means the candidate returned
		by this function is the right one?!
		"""

		wrong_direction = (
			True
				if
					(new_distance == 0) or
					(direction == 'down' and new_distance < 0) or
					(direction == 'up' and new_distance > 0)
				else
				False
			)

		# closer = (
		# 	True
		# 		if (abs(new_distance) - abs(current_distance)) <= 0
		# 		else
		# 		False
		# 	)

		# print(
		# 	f'  ->Dir: {direction}, Dists: {current_distance, new_distance} ... WD: {wrong_direction}'
		# 	)

		if wrong_direction:
			if direction == 'down':
				#       	new min      new max    new current
				#  +1 for new current index so that downward motion errs on going down
				#      while the truncated rounding here errs on going up ... so use for "up"
				new_vals = (current_idx, max_idx, ((current_idx+max_idx)//2))
				# new_vals = (current_idx, max_idx, ((current_idx+max_idx)//2))
			elif direction == 'up':
				new_vals = (min_idx, current_idx, ((min_idx+current_idx)//2))
		else:
			if direction == 'down':
				#       new min      new max    new current
				new_vals = (min_idx, current_idx, ((min_idx+current_idx)//2))
			elif direction == 'up':
				new_vals = (current_idx, max_idx, ((current_idx+max_idx)//2))

		return new_vals


	def find_next_symbol(self, symbols, direction):

		current_row = get_row(self.view, self.view.sel()[0])  # 0 indexed
		symbols_len = len(symbols)

		min_idx = 0
		max_idx = symbols_len - 1
		current_idx = int((current_row / self.total_lines ) * (symbols_len-1))
		# print(f'\nCurrent Row: {current_row}')
		# print(
		# 	min_idx, max_idx, current_idx, f'"{symbols[current_idx].name}"',
		# 	' ... MIN, MAX, CURR_IDX, SYM',
		# 	)
		current_distance = self.symbol_distance(current_row, symbols[current_idx])
		# hack to get first comparison
		# should get appropriate split
		new_distance = current_distance

		# best_candidate = {
		# 	'symbol': symbols[current_idx],
		# 	'distance': self.symbol_distance(current_row, symbols[current_idx])}
		for _ in symbols:  # bottom out at going through each symbol!
			new_min_idx, new_max_idx, new_current_idx = self.new_idxs(
				direction, min_idx, max_idx, current_idx, current_distance, new_distance)

			# print(
			# 	new_min_idx, new_max_idx, new_current_idx, f'"{symbols[new_current_idx].name}"',
			# 	' ... NEW_VALS: MIN, MAX, CURR, SYM',
			# 	)
			# if min and max range has narrowed as far as possible
			# we've got our best candidates
			# where the reaching the end of binary search is the criterion
			# if we can only look for the closest
			# now ... be lazy and just for loop through?  or just trust the algorithm
			if (new_max_idx - new_min_idx) <= 1:  # or <=2?

				# final_symbol = symbols[new_current_idx]
				# print('FINAL', new_min_idx, new_max_idx, new_current_idx, final_symbol)
				# return symbols[new_current_idx]

				# looping approach for when narrow window
				# print(list(range(new_min_idx, new_max_idx+1)))
				candidates = [
					(idx, self.symbol_distance(current_row, symbols[idx]))
						for idx
						in range(new_min_idx, new_max_idx+1)
					]
				# print('candidates', candidates)
				final_symbol = None
				if direction == 'down':
					for idx, dist in candidates:
						if dist > 0:
							final_symbol = symbols[idx]
							break
				elif direction == 'up':
					for idx, dist in reversed(candidates):
						if dist < 0:
							final_symbol = symbols[idx]
							break

				# print('FINAL', new_min_idx, new_max_idx, idx, final_symbol)
				return final_symbol

			min_idx = new_min_idx
			max_idx = new_max_idx
			current_idx = new_current_idx
			current_distance = new_distance
			new_distance = self.symbol_distance(current_row, symbols[current_idx])
		else:
			return None





