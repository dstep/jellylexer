import os
import re
from jellylib.parsing import Whitespaces, Parser, Newlines, EOF, Spaces
from jellylib.error import Error
import string
import json
import jellylib.log as log


SubstRegexp = re.compile("\$\(([a-zA-Z0-9_\-]+)\)")


class FormattedWriter:
	def __init__(self, stream):
		self.stream = stream

	def __del__(self):
		self.flush()

	def flush(self):
		pass


class SubstValue:
	def __init__(self, value = None):
		self.lines = []
		self.changes_line_info = False
		if value is not None:
			self.lines.append(value)

	def add_line(self, line, sep = None):
		if sep is not None and len(self.lines) > 0:
			self.lines[-1] += sep
		self.lines.append(line)

	def __str__(self):
		if len(self.lines) > 1:
			raise RuntimeError("value is not inline")
		return ''.join(self.lines)


class SubstCodeParser(Parser):
	def __init__(self):
		super().__init__()

	def parse_inline(self):
		self.skip_spaces()
		s = []
		suff = []
		raise_on_nonspace = False
		while True:
			ch = self.peek()
			if ch in Whitespaces:
				if len(s) > 0:
					suff.append(ch)
				self.advance()
			elif ch in Newlines:
				if len(s) > 0:
					raise_on_nonspace = True
				self.advance()
			elif ch is EOF:
				break
			else:
				if raise_on_nonspace:
					self.report("expected inline value, not multiline value")
				s.extend(suff)
				suff = []
				s.append(ch)
				self.advance()
		val = SubstValue()
		val.lines.append(''.join(s))
		return val

	def skip_spaces(self):
		while True:
			ch = self.peek()
			if ch in Spaces:
				self.advance()
			else:
				break

	def parse(self):
		val = SubstValue()
		cur_line = None
		preprocessor_line = None
		preprocessor_file = None
		next_line = None
		next_file = None

		def commit_line():
			nonlocal cur_line, preprocessor_line, preprocessor_file
			if cur_line:
				if next_line != preprocessor_line or next_file != preprocessor_file:
					val.lines.append("#line {line} {file}".format(line=next_line, file=json.dumps(next_file)))
					preprocessor_line = next_line
					preprocessor_file = next_file
					val.changes_line_info = True

				val.lines.append(''.join(cur_line))
				cur_line = None
				preprocessor_line += 1

		def add_line():
			nonlocal cur_line, next_file, next_line
			commit_line()
			next_line = self.loc().line()
			next_file = self.loc().filename()
			cur_line = []

		add_line()

		while True:
			ch = self.peek()
			if ch is EOF:
				break
			elif ch == '\n':
				self.advance()
				if self.peek() == '\r':
					self.advance()
				add_line()
			else:
				cur_line.append(ch)
				self.advance()

		commit_line()
		return val


def capitalize(id):
	return string.capwords(id, sep="_").replace("_", "")


def chunks(l, n):
	for i in range(0, len(l), n):
		yield l[i:i + n]


class CodegenState:
	def __init__(self, dfa_state, index):
		self.dfa_state = dfa_state
		self.index = index
		self.offset = 4 * index
		self.reset_state = None


class Codegen:
	def __init__(self):
		self.writer = None
		self.substs = dict()

	def parse(self, project):
		for section in project.get_sections("codegen"):
			section.mark_used()

			for value in section.values:
				if value.key == "header":
					if "header" in self.substs:
						raise Error(value.loc, "duplicate key")
					self.substs["header"] = self.parse_subst_code(value.span)
				elif value.key == "source":
					if "source" in self.substs:
						raise Error(value.loc, "duplicate key")
					self.substs["source"] = self.parse_subst_code(value.span)
				elif value.key == "prefix":
					if "prefix" in self.substs:
						raise Error(value.loc, "duplicate key")
					self.substs["prefix"] = self.parse_inline_value(value.span)
				else:
					raise Error(value.loc, "unknown key")

		if "header" not in self.substs:
			self.substs["header"] = SubstValue()
		if "source" not in self.substs:
			self.substs["header"] = SubstValue()
		if "prefix" not in self.substs:
			self.substs["prefix"] = SubstValue(project.name)
		self.substs["extra_fields"] = SubstValue()

	def build(self, project):
		grammar = project.grammar

		self.build_tables(grammar)

		self.substs["lexer_trap"] = SubstValue()

	def build_tables(self, grammar):
		classes = [set(range(256))]

		unique_refines = set()

		def refine(partition):
			if partition in unique_refines:
				return
			unique_refines.add(partition)
			n = len(classes)
			for idx in range(n):
				clss = classes[idx]
				inter = clss.intersection(partition)
				if len(inter) == len(clss):
					continue
				if len(inter) == 0:
					continue
				clss.difference_update(inter)
				classes.append(inter)

		for xstate in grammar.xstates.values():
			def state_visitor(state):
				state_classes = dict()
				for idx, target_state in enumerate(state.trans):
					if target_state not in state_classes:
						state_classes[target_state] = set()
					state_classes[target_state].add(idx)
				for target_state, chars in state_classes.items():
					refine(tuple(chars))

			xstate.dfa_state.visit(state_visitor)

		eq_classes = [None] * 256
		for idx, chars in enumerate(classes):
			for ch in chars:
				eq_classes[ch] = idx

		states = dict()
		states_list = []

		enum_states = SubstValue()
		set_state_switch = SubstValue()

		tokens = dict()
		tokens_list = []

		for xstate in grammar.xstates.values():
			def state_visitor(state):
				codegen_state = CodegenState(state, len(states))
				states_list.append(codegen_state)
				states[state] = codegen_state
				if state.accepts:
					codegen_state.reset_state = state.accepts.target_state.dfa_state
					token = state.accepts.token
					if token not in tokens:
						tokens[token] = len(tokens)
						tokens_list.append(token)
				else:
					codegen_state.reset_state = xstate.dfa_state

			xstate.dfa_state.visit(state_visitor)

			state_name = capitalize(xstate.id)
			enum_states.add_line(state_name, ",")
			set_state_switch.add_line(
				"case State::{state}: jlex_lexer->state = {state_id}; break;".format(
					prefix=self.substs["prefix"],
					state=state_name,
					state_id=states[xstate.dfa_state].offset
				)
			)

		self.substs["enum_states"] = enum_states
		self.substs["set_state_switch"] = set_state_switch

		states_num = len(states)

		transitions = dict()
		eof_transitions = dict()

		for state in states_list:
			dfa_state = state.dfa_state

			if dfa_state.accepts:
				# accept...
				accept_value = 0x80000000
				accept_name = dfa_state.accepts.token.id
			else:
				# does not accept
				accept_value = 0
				accept_name = None

			reset_dfa_state = state.reset_state
			reset_state = states[reset_dfa_state]

			for clss, chars in enumerate(classes):
				ch = list(chars)[0]
				target_state = dfa_state.trans[ch]
				if target_state is None:
					# current state does not accept the following character
					reset_target_state = reset_dfa_state.trans[ch]
					if reset_target_state is None:
						# next state cannot parse character, trap
						target_value = 0
					else:
						target_value = accept_value | states[reset_target_state].offset
				else:
					target_value = states[target_state].offset

				if accept_name:
					target_value = f"{hex(target_value)}|((TOKEN({accept_name}))<<16)"
				else:
					target_value = hex(target_value)

				transitions[clss * states_num + state.index] = target_value

			if accept_name:
				accept_value = f"{hex(accept_value)}|((TOKEN({accept_name}))<<16)"
			else:
				accept_value = hex(accept_value)

			eof_transitions[state.index] = accept_value

		eq_classes_val = SubstValue()
		for chunk in chunks(eq_classes, 16):
			line = ', '.join(map(lambda n: str(n * states_num * 4), chunk))
			eq_classes_val.add_line(line, ",")

		eof_transitions_val = SubstValue()
		out = []
		for state in states_list:
			out.append(eof_transitions[state.index])
		self.substs["eof_transitions"] = SubstValue(",".join(out))

		transitions_val = SubstValue()
		for clss, _ in enumerate(classes):
			items = []
			for state in states_list:
				#if clss == 0:
					# trap on zero byte
				#	items.append(0)
				#else:
				items.append(transitions[clss * states_num + state.index])
			line = ', '.join(items)
			transitions_val.add_line(line, ",")

		tokens_value = SubstValue()
		enum_tokens_val = SubstValue()

		for token in tokens_list:
			tokens_value.add_line(json.dumps(token.id), ",")
			enum_tokens_val.add_line(capitalize(token.id), ",")

		log.log(2, "Equivalence classes: {num}", num=len(classes))
		log.log(2, "Transition table size: {num} KB", num= (states_num * len(classes) * 4) / 1024)

		self.substs["token_names"] = tokens_value
		self.substs["enum_tokens"] = enum_tokens_val

		self.substs["transitions"] = transitions_val
		self.substs["eq_classes"] = eq_classes_val


	def parse_subst_code(self, span):
		parser = SubstCodeParser()
		parser.set_source(span)
		return parser.parse()

	def parse_inline_value(self, span):
		parser = SubstCodeParser()
		parser.set_source(span)
		return parser.parse_inline()

	def write_header(self, out, filename):
		self.line_num = 1
		self.process_template("lexer-header-prefix.h", out, filename)
		self.process_template("lexer-header.h", out, filename)

	def write_source(self, out, filename):
		self.line_num = 1
		self.process_template("lexer-source-prefix.cpp", out, filename)
		self.process_template("lexer-header.h", out, filename)
		self.process_template("lexer-source.cpp", out, filename)

	def process_template(self, templatename, out, filename):
		with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), templatename), 'r') as file:
			for line in file:
				indent = self.find_indent(line)
				should_reset_line = False

				def subst(match):
					nonlocal should_reset_line
					id = match.group(1)
					if id not in self.substs:
						raise RuntimeError("substitution for {id} not found".format(id=id))
					val = self.substs[id]

					if val.changes_line_info:
						should_reset_line = True
					self.line_num += max(0, len(val.lines) - 1)

					if len(val.lines) == 0:
						return ""
					elif len(val.lines) == 1:
						return val.lines[0]
					else:
						return val.lines[0] + ''.join(map(lambda s: "\n" + s + indent, val.lines[1:]))

				line = SubstRegexp.sub(subst, line)
				out.write(line)
				if line.endswith("\n") or line.endswith("\r"):
					self.line_num += 1
				if should_reset_line:
					self.line_num += 1
					out.write("#line {line} {file}\n".format(line=self.line_num, file=json.dumps(filename)))

	def find_indent(self, s):
		indent = []
		for ch in s:
			if ch in Whitespaces:
				indent.append(ch)
			else:
				break
		return ''.join(indent)