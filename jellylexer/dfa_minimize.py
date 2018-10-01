from jellylexer.dfa import *
import jellylib.log as log


class MinimizeDFA:
	def __init__(self):
		self.states = []
		self.disjoint = set()

	def run(self, state):
		log.log(1, "Running DFA minimization")

		def pre_visit(state):
			self.states.append(state)
			state.repr = None

		state.visit(pre_visit)

		equivalences = [self.states]
		states_num = len(self.states)
		states_processed = 0

		def assign_repr():
			for sublist in equivalences:
				for state in sublist:
					state.repr = sublist[0]

		def refine_list(states, refiner):
			nonlocal states_processed
			out = []

			for state in states:
				for out_list in out:
					if refiner(out_list[0], state):
						out_list.append(state)
						break
				else:
					out.append([state])
				states_processed += 1

				if log.Verbosity >= 1:
					log.print_progress(states_processed, states_num)

			return out, len(out) > 1

		def refine_all(refiner):
			nonlocal equivalences, states_processed
			states_processed = 0
			new_equivalences = []
			any_progress = False
			for sublist in equivalences:
				if len(sublist) > 1:
					out, progress = refine_list(sublist, refiner)
					new_equivalences.extend(out)
					if progress:
						any_progress = True
				else:
					states_processed += 1
					new_equivalences.append(sublist)

			if log.Verbosity >= 1:
				log.print_progress(states_processed, states_num)

			equivalences = new_equivalences
			assign_repr()
			return any_progress

		def compare_accepts(accept1, accept2):
			if accept1 == accept2:
				return True
			if (accept1 is None) != (accept2 is None):
				return False
			return accept1.token == accept2.token and accept1.target_state == accept2.target_state

		def refiner_accept(state1, state2):
			return compare_accepts(state1.accepts, state2.accepts)

		def is_same_class(state1, state2):
			if state1 == state2:
				return True
			if (state1 is None) != (state2 is None):
				return False
			if state1.repr is state2.repr:
				return True
			return False

		def refiner_trans(state1, state2):
			for i in range(256):
				if not is_same_class(state1.trans[i], state2.trans[i]):
					return False
			return True


		log.log(2, "Total states: {states}", states=states_num)

		assign_repr()
		refine_all(refiner_accept)
		while refine_all(refiner_trans):
			pass


		new_states = dict()
		new_states_num = 0

		def remap_state(state):
			nonlocal new_states_num
			if state is None:
				return None
			state = state.repr
			if state in new_states:
				return new_states[state]
			new_state = State()
			new_states_num += 1
			new_state.accepts = state.accepts
			new_states[state] = new_state
			for i in range(256):
				new_state.trans[i] = remap_state(state.trans[i])
			return new_state

		out_state = remap_state(state)
		log.log(2, "Total states after minimization: {states}", states=new_states_num)

		return out_state




def minimize(state):
	m = MinimizeDFA()
	return m.run(state)