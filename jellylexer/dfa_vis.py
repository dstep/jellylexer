from jellylexer.dfa import *
from graphviz import Digraph


def visualize(state):
	G = Digraph()

	states = set()

	def compress(s):
		ranges = []
		range = None
		lst = list(sorted(s))
		for ch in lst:
			if (not range) or (range[1] + 1 != ord(ch)):
				range = [ord(ch), ord(ch)]
				ranges.append(range)
			else:
				range[1] += 1
		out = []
		for begin,end in ranges:
			if begin == end:
				out.append(chr(begin))
			else:
				out.append(chr(begin))
				out.append('-')
				out.append(chr(end))
		return ''.join(out)

	def process_state(state):
		if state in states:
			return
		states.add(state)
		state.id = str(len(states))

		if state.accepts:
			state.name = state.accepts.token.id
		else:
			state.name = state.id

		G.node(state.id, state.name)

		target_states = dict()

		for ch, target_state in enumerate(state.trans):
			if target_state is None:
				continue
			if target_state not in target_states:
				target_states[target_state] = []
			target_states[target_state].append(ch)

		for target_state, chars in target_states.items():
			process_state(target_state)
			label = repr(compress(''.join(map(chr, chars))))
			G.edge(state.id, target_state.id, label)

	process_state(state)

	G.render(directory="vis/", view=True, cleanup=True)