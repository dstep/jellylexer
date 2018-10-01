from jellylexer.dfa_vis import visualize


class State:
	def __init__(self):
		self.trans = [None] * 256
		self.accepts = None

	def visit(self, visitor):
		visited = set()

		def _visit(state):
			if state is None:
				return
			if state in visited:
				return
			visited.add(state)
			visitor(state)
			for target_state in state.trans:
				_visit(target_state)

		_visit(self)


class SCC:
	def __init__(self):
		self.states = []
		self.closure = None

	def add(self, state):
		self.states.append(state)

	def build_closure(self):
		self.closure = set()
		self.closure.add(self)

		other_closures = set()

		for state in self.states:
			for target_state in state.etrans:
				if target_state.scc == self:
					continue
				other_closures.add(target_state.scc.closure)

		for closure in other_closures:
			self.closure.update(closure)

		self.closure = frozenset(self.closure)


class Builder:
	def __init__(self):
		self.states = set()
		self.powerset = dict()
		self.worklist = []

	def build(self, state):
		def pre_visit(state):
			state.closure = None
			state.scc_index = None
			state.scc_lowlink = None
			state.scc_onstack = False
			state.scc = None
			self.states.add(state)

		state.visit(pre_visit)

		self.find_scc()

		dfa_state = self.get_dfa_for_subset(state.scc.closure)
		self.process()

		return dfa_state

	def process(self):
		i = 0
		while i < len(self.worklist):
			subset, dfa_state = self.worklist[i]
			self.process_dfa_state(subset, dfa_state)
			i += 1

	def process_dfa_state(self, subset, dfa_state):
		transitions = [set() for i in range(256)]
		accepts = set()

		for scc in subset:
			for nfa_state in scc.states:
				if nfa_state.rule:
					accepts.add(nfa_state.rule)
				for chars, target_state in nfa_state.trans:
					for char in chars:
						transitions[char].update(target_state.scc.closure)

		transitions = map(frozenset, transitions)
		for idx, subset in enumerate(transitions):
			if len(subset) == 0:
				dfa_state.trans[idx] = None
			else:
				dfa_state.trans[idx] = self.get_dfa_for_subset(subset)

		if len(accepts) > 0:
			accept = min(accepts, key=lambda rule:rule.order)
			dfa_state.accepts = accept


	def get_dfa_for_subset(self, subset):
		if subset not in self.powerset:
			dfa_state = State()
			self.worklist.append((subset, dfa_state))
			self.powerset[subset] = dfa_state
		return self.powerset[subset]

	def find_scc(self):
		index = 0
		stack = []

		def strongconnect(v):
			nonlocal index
			v.scc_index = index
			v.scc_lowlink = index
			index += 1
			stack.append(v)
			v.scc_onstack = True

			for w in v.etrans:
				if w.scc_index is None:
					strongconnect(w)
					v.scc_lowlink = min(v.scc_lowlink, w.scc_lowlink)
				elif w.scc_onstack:
					v.scc_lowlink = min(v.scc_lowlink, w.scc_index)

			if v.scc_lowlink == v.scc_index:
				scc = SCC()

				while True:
					w = stack.pop()
					w.scc_onstack = False
					scc.add(w)
					w.scc = scc
					if w == v:
						break

				scc.build_closure()

		for state in self.states:
			if state.scc_index is None:
				strongconnect(state)


	def get_transitive_closure(self, state):
		return state.scc.closure



def build_from_nfa(state):
	builder = Builder()
	return builder.build(state)

