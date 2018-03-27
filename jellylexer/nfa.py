class State:
	def __init__(self):
		self.etrans = []
		self.trans = []
		self.rule = None

	def add_etrans(self, state):
		self.etrans.append(state)

	def add_trans(self, chars, state):
		self.trans.append((chars, state))

	def visit(self, visitor):
		visited = set()

		def _visit(state):
			if state in visited:
				return
			visited.add(state)
			visitor(state)
			for target_state in state.etrans:
				_visit(target_state)
			for chars, target_state in state.trans:
				_visit(target_state)

		_visit(self)


def clone(begin, end):
	remap = dict()

	def get_clone(state):
		if state in remap:
			return remap[state]
		new_state = State()
		remap[state] = new_state
		for target_state in state.etrans:
			new_state.etrans.append(get_clone(target_state))
		for chars, target_state in state.trans:
			new_state.trans.append((chars, get_clone(target_state)))
		return new_state

	return get_clone(begin), get_clone(end)