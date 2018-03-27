from jellylexer.regexp import *
from jellylib.error import Error
from jellylexer.regexp_parser import RegexpParser
from jellylib.parsing import EOF
import jellylexer.nfa as nfa
import jellylexer.dfa as dfa
from jellylexer.dfa_minimize import minimize
import sys
import jellylib.log as log

class Fragment:
	def __init__(self, id, loc, re):
		self.id = id
		self.re = re
		self.loc = loc
		self.nfa = None

	def build(self, ctx):
		if not self.nfa:
			self.nfa = (nfa.State(), nfa.State())
			self.re.build_nfa(ctx, *self.nfa)

	def build_nfa(self, ctx, begin, end):
		self.build(ctx)
		frag_begin, frag_end = nfa.clone(*self.nfa)
		begin.add_etrans(frag_begin)
		frag_end.add_etrans(end)


class GrammarContext:
	def __init__(self):
		self.fragments = dict()
		self.tokens = dict()
		self.xstates = dict()
		self.add_xstate(XState("default"))

	def add_xstate(self, xstate):
		log.log(2, "Added state {state}", state=xstate.id)
		self.xstates[xstate.id] = xstate

	def get_xstate(self, loc, id):
		if id not in self.xstates:
			raise Error(loc, "no such state '{state}'".format(state=id))
		return self.xstates[id]

	def add_token(self, id):
		if id not in self.tokens:
			self.tokens[id] = Token(id)
		return self.tokens[id]

	def get_token(self, loc, id):
		if id not in self.tokens:
			raise Error(loc, "no such token '{token}'".format(token=id))
		return self.tokens[id]

	def add_fragment(self, fragment):
		if fragment.id in self.fragments:
			raise Error(
				fragment.loc,
				"duplicate fragment '{fragment}', first declaration at\n\t{first}"
					.format(
						fragment=fragment.id,
						first=self.fragments[fragment.id].loc
					)
			)
		self.fragments[fragment.id] = fragment

	def get_fragment(self, loc, id):
		if id not in self.fragments:
			raise Error(loc, "no such fragment '{fragment}'".format(fragment=id))
		return self.fragments[id]

	def build(self):
		for fragment in self.fragments.values():
			fragment.build(self)

		for xstate in self.xstates.values():
			xstate.build(self)


class Token:
	def __init__(self, id):
		self.id = id


class Rule:
	def __init__(self, xstate, loc, token, re, target_state=None):
		self.xstate = xstate
		self.loc = loc
		self.token = token
		self.re = re
		if target_state is None:
			target_state = xstate
		self.target_state = target_state
		self.xstate.rules.append(self)
		self.order = len(self.xstate.rules)


class XState:
	def __init__(self, id):
		self.id = id
		self.rules = []
		self.state_begin = nfa.State()
		self.dfa_state = None

	def build(self, ctx):
		compound_re = ReEmpty()

		for rule in self.rules:
			compound_re = ReChoice(rule.re, compound_re)

		log.log(2, "State {state} has {num} rules", state=self.id, num=len(self.rules))

		def build_rule(rule):
			state = nfa.State()
			state.rule = rule
			rule.re.build_nfa(ctx, self.state_begin, state)

		for rule in self.rules:
			build_rule(rule)

		nonstart_chars = set(list(range(256)))

		visited = set()
		def visit(state):
			if state in visited:
				return
			visited.add(state)
			for chars, _ in state.trans:
				nonstart_chars.difference_update(chars)
			for target_state in state.etrans:
				visit(target_state)

		visit(self.state_begin)

		# add implicit error rule
		re_nonstart = ReStar(ReChar(frozenset(nonstart_chars)))
		error_rule = Rule(self, None, ctx.add_token("error"), ReChoice(re_nonstart, RePrefix(compound_re)))
		build_rule(error_rule)

		full_dfa_state = dfa.build_from_nfa(self.state_begin)
		full_dfa_state.accepts = None

		marked_rules = set()
		non_eof_rules = set()

		def mark_rule(state):
			if state.accepts:
				marked_rules.add(state.accepts)

				for target_state in state.trans:
					if target_state is None:
						non_eof_rules.add(state.accepts)
						break


		full_dfa_state.visit(mark_rule)
		for rule in self.rules:
			if rule not in marked_rules:
				print("{loc}: rule unused in state {state}".format(loc=rule.loc, state=self.id), file=sys.stderr)
			elif rule not in non_eof_rules:
				print("{loc}: in state {state}, this rule is only usable at the end of file".format(loc=rule.loc, state=self.id), file=sys.stderr)

		self.dfa_state = minimize(full_dfa_state)
		#vis.visualize(self.dfa_state)

class RuleParser(RegexpParser):
	def __init__(self):
		super().__init__()

	def run(self):
		xstates = []
		target_state = None

		while True:
			self.skip_spaces()
			begin = self.loc()
			ch = self.peek()
			is_target = False
			if ch == '{':
				self.advance()
				self.skip_spaces()
				ch = self.peek()
				if ch == '-':
					self.advance()
					self.expect('>')
					self.skip_spaces()
					is_target = True
				id = self.parse_ref_id()
				self.skip_spaces()
				self.expect('}')
				if is_target:
					if target_state:
						self.report(begin.to(self.loc()), "only one target state allowed")
					target_state = (begin.to(self.loc()), id)
				else:
					xstates.append((begin.to(self.loc()), id))
			else:
				break

		re = self.parse_re(10)
		self.skip_spaces()
		self.expect(EOF)

		return (xstates, re, target_state)


def parse_rule(source):
	parser = RuleParser()
	parser.set_source(source)
	return parser.run()
