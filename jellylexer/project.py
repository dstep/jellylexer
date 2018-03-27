from jellylib.parsing import *
from jellylexer.grammar import *
from jellylexer.regexp_parser import parse_span

class Section:
	def __init__(self, project, loc, name, params):
		self.project = project
		self.name = name
		self.loc = loc
		self.params = params
		self.values = []
		self.project.sections.append(self)
		self.used = False

	def mark_used(self):
		self.used = True

class Value:
	def __init__(self, section, loc, key, span):
		self.section = section
		self.loc = loc
		self.key = key
		self.span = span
		self.section.values.append(self)


class Project:
	def __init__(self, name):
		self.name = name
		self.sections = []
		self.grammar = GrammarContext()

	def check_used(self):
		for section in self.sections:
			if not section.used:
				raise Error(section.loc, "unused section")

	def parse(self):
		for section in self.get_sections("general"):
			section.mark_used()

			for value in section.values:
				if value.key == "state":
					name = parse_string(value.span).strip()
					self.grammar.add_xstate(XState(name))
				else:
					raise Error(value.loc, "unknown key")

		for section in self.get_sections("fragments"):
			section.mark_used()

			for value in section.values:
				re = parse_span(value.span)
				self.grammar.add_fragment(Fragment(value.key, value.loc, re))

		for section in self.get_sections("grammar"):
			section.mark_used()

			for value in section.values:
				xstates, re, target_state_name = parse_rule(value.span)
				rule_xstates = set()
				for loc, xstate_name in xstates:
					if xstate_name == "all":
						for xstate in self.grammar.xstates:
							rule_xstates.add(xstate)
					else:
						xstate = self.grammar.get_xstate(loc, xstate_name)
						rule_xstates.add(xstate)
				target_state = None
				if target_state_name:
					target_state = self.grammar.get_xstate(target_state_name[0], target_state_name[1])
				if len(rule_xstates) == 0:
					rule_xstates.add(self.grammar.get_xstate(None, "default"))
				token = self.grammar.add_token(value.key)
				for xstate in rule_xstates:
					Rule(xstate, value.loc, token, re, target_state)

	def build(self):
		self.grammar.build()

	def get_sections(self, name, params=None):
		for section in self.sections:
			if section.name != name:
				continue
			if params is not None:
				if section.params.length != params.length:
					continue
				flag = False
				for i in range(params.length):
					if section.params[i] != params[i]:
						flag = True
						break
				if flag:
					continue
			yield section


WordChar = LowerLetter | UpperLetter | Digit | frozenset("_-+")


class ProjectParser(Parser):
	def __init__(self, project, source):
		super().__init__()
		self.project = project
		self.active_section = None
		self.active_value_key = None
		self.active_value_span = None
		self.active_value_loc = None
		self.active_value_span_empty = False
		self.active_indent = None
		self.active_newline_loc = None
		self.set_source(source)

	def run(self):
		while not self.is_eof():
			self.parse_line()

	def parse_line(self):
		ch = self.peek()
		begin = self.loc()
		if ch == "[":
			self.close_last_value()
			self.take()
			self.skip_ws()
			name, _ = self.parse_word()
			self.skip_ws()
			params = []
			if self.peek() == '(':
				self.take()
				self.skip_ws()
				if self.peek() in WordChar:
					param, _ = self.parse_word()
					params.append(param)
					while True:
						self.skip_ws()
						if self.peek() == ',':
							self.take()
							self.skip_ws()
						else:
							break
						param, _ = self.parse_word()
						params.append(param)
					self.expect(')')
			self.expect(']')
			end = self.loc()
			self.active_section = Section(self.project, begin.to(end), name, params)
			self.consume_empty_line()
		elif ch == "#":
			self.close_last_value()
			self.take()
			self.consume_comment_line()
		else:
			if ch in WordChar:
				self.parse_new_key()
			else:
				self.parse_value()

	def parse_value(self):
		if self.active_indent is None:
			self.parse_indent_and_value()
		else:
			pos = self.tell()
			i = 0
			while True:
				ch = self.peek()
				if i >= len(self.active_indent):
					break
				if ch != self.active_indent[i]:
					if self.active_value_span and (not self.active_value_span_empty):
						self.add_newline()
					self.active_newline_loc = self.loc()
					self.consume_empty_line()
					return
				i += 1
				self.take()
			self.parse_span_from(pos)

	def add_newline(self):
		newline = ArtificialSource(self.active_newline_loc)
		newline.feed("\n")
		self.active_value_span.add_span(*newline.get_span())

	def parse_indent_and_value(self):
		if not self.active_value_span:
			self.consume_empty_line()
			return

		pos = self.tell()
		indent = []
		while True:
			ch = self.peek()
			if ch in Whitespaces:
				self.take()
				indent.append(ch)
			elif ch in LineEnd:
				self.consume_newline()
				break
			else:
				if len(indent) == 0:
					self.report("unexpected character")
				else:
					self.active_indent = indent
					self.parse_span_from(pos)
				break

	def parse_new_key(self):
		self.close_last_value()
		if not self.active_section:
			self.report("no open section")

		key, loc = self.parse_word()

		self.active_value_key = key
		self.active_value_loc = loc
		self.active_value_span = SourceSpans()
		self.active_value_span_empty = True
		self.active_indent = None

		self.skip_ws()
		if self.peek() in LineEnd:
			self.consume_newline()
		else:
			self.parse_span_from(self.tell())
			self.close_last_value()

	def parse_span_from(self, pos):
		if not self.active_value_span:
			self.report("unexpected indented value")
		pos_begin = pos
		pos_end = pos_begin
		while True:
			ch = self.peek()
			if ch in LineEnd:
				break
			else:
				self.take()
				if ch not in Whitespaces:
					pos_end = self.tell()
		self.consume_newline()
		if not self.active_value_span_empty:
			self.add_newline()
		self.active_value_span.add_span(*self.get_span(pos_begin, pos_end))
		self.active_newline_loc = self.loc()
		self.active_value_span_empty = False

	def close_last_value(self):
		if self.active_value_span:
			if self.active_value_span_empty:
				self.report("key {key} does not have associated value".format(key=self.active_value_key), loc=self.active_value_loc)
			Value(self.active_section, self.active_value_loc, self.active_value_key, self.active_value_span)
			self.active_value_key = None
			self.active_value_span = None
			self.active_value_loc = None
			self.active_value_span_empty = False
			self.active_indent = None

	def consume_comment_line(self):
		while True:
			ch = self.peek()
			if ch in Newlines:
				self.consume_newline()
				return
			elif ch == EOF:
				return
			else:
				self.take()

	def consume_empty_line(self):
		while True:
			ch = self.peek()
			if ch in Newlines:
				self.consume_newline()
				return
			elif ch == EOF:
				return
			elif ch in Whitespaces:
				self.take()
			else:
				self.report("unexpected character, expected empty line")

	def consume_newline(self):
		ch = self.peek()
		if ch == '\n':
			self.take()
		elif ch == '\r':
			self.take()
			if self.peek() == '\n':
				self.take()

	def parse_word(self):
		chars = []
		begin = self.loc()
		while True:
			ch = self.peek()
			if ch not in WordChar:
				break
			self.take()
			chars.append(ch)
		if len(chars) == 0:
			self.report("expected word")
		return ''.join(chars), begin.to(self.loc())

	def skip_ws(self):
		while True:
			ch = self.peek()
			if ch in Whitespaces:
				self.advance()
			else:
				return


def parse_project(source, name):
	project = Project(name)
	pp = ProjectParser(project, source)
	pp.run()
	return project
