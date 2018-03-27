from jellylib.parsing import *
from jellylexer.regexp import *

RegularReChar = Graphicals.difference("~{}[]+*.?<>()\\\"|")
RefIDChars = LowerLetter | UpperLetter | Digit | frozenset("-_")
GroupChars = Printables.difference("^-\\[]")

Escapes = {
	'n' : ord('\n'),
	'r' : ord('\r'),
	't' : ord('\t')
}

HexMapping = {
	'0': 0,
	'1': 1,
	'2': 2,
	'3': 3,
	'4': 4,
	'5': 5,
	'6': 6,
	'7': 7,
	'8': 8,
	'9': 9,
	'a': 10,
	'b': 11,
	'c': 12,
	'd': 13,
	'e': 14,
	'f': 15,
	'A': 10,
	'B': 11,
	'C': 12,
	'D': 13,
	'E': 14,
	'F': 15
}

class RegexpParser(Parser):
	def __init__(self):
		super().__init__()

	def run(self):
		re = self.parse_re(10)
		return re

	def parse_re(self, prec):
		re = self.try_parse_re(prec)
		if not re:
			self.report("expected expression")
		return re

	def try_parse_re(self, prec):
		re = None
		self.skip_spaces()
		ch = self.peek()
		if ch == '.':
			self.advance()
			re = ReChar(range(256))
		elif ch == '~':
			self.advance()
			re = self.parse_re(10)
			re = RePrefix(re)
		elif ch == '(':
			self.advance()
			re = self.try_parse_re(10)
			if not re:
				re = ReEmpty()
			self.skip_spaces()
			self.expect(')')
		elif ch == '[':
			self.advance()
			re = self.parse_group_content()
			self.expect(']')
		elif ch == '<':
			begin = self.loc()
			self.advance()
			self.skip_spaces()
			id = self.parse_ref_id()
			self.skip_spaces()
			self.expect('>')
			re = ReRef(begin.to(self.loc()), id)
		elif ch == '"':
			self.advance()
			re = self.parse_string_content()
			self.expect('"')
		elif ch == '\\':
			self.advance()
			esc = self.parse_esc()
			re = ReChar([esc])
		elif ch in RegularReChar:
			self.advance()
			re = ReChar([ord(ch)])
		else:
			return None

		if re is None:
			return re

		while True:
			self.skip_spaces()
			ch = self.peek()
			if ch == '+':
				self.advance()
				re = ReConcat(re, ReStar(re))
			elif ch == '?':
				self.advance()
				re = ReChoice(ReEmpty(), re)
			elif ch == '*':
				self.advance()
				re = ReStar(re)
			elif ch == '{':
				begin = self.loc()
				self.advance()
				self.skip_spaces()
				num1 = self.parse_num()
				num2 = num1
				self.skip_spaces()
				ch = self.peek()
				if ch == ',':
					self.advance()
					self.skip_spaces()
					num2 = self.parse_num()
					self.skip_spaces()
				self.expect('}')
				if num2 < num1:
					self.report("second range number must be greater than the first", loc=begin.to(self.loc()))
				tail = ReEmpty()
				while num2 > num1:
					tail = ReChoice(ReConcat(re, tail), ReEmpty())
					num2 -= 1
				while num1 > 0:
					tail = ReConcat(re, tail)
					num1 -= 1
				re = tail
			elif ch == '|' and prec >= 10:
				self.advance()
				rhs = self.parse_re(9)
				re = ReChoice(re, rhs)
			elif prec >= 9:
				rhs = self.try_parse_re(8)
				if not rhs:
					return re
				re = ReConcat(re, rhs)
			else:
				return re

	def parse_num(self):
		self.skip_spaces()
		ch = self.peek()
		if ch == '0':
			self.advance()
			return 0
		elif ch in Digit:
			self.advance()
			acc = ord(ch) - ord('0')
			while True:
				ch = self.peek()
				if ch in Digit:
					self.advance()
					acc = acc * 10 + (ord(ch) - ord('0'))
				else:
					break
			return acc
		else:
			self.report("expected number")

	def parse_group_content(self):
		invert = False

		if self.peek() == '^':
			self.advance()
			invert = True

		group = set()

		while True:
			begin = self.loc()
			char = self.parse_group_char()
			if char is None:
				break
			if self.peek() == '-':
				self.advance()
				char2 = self.parse_group_char()
				if char2 is None:
					self.report("expected second range character", begin.to(self.loc()))
				if char2 < char:
					self.report("invalid range", begin.to(self.loc()))
				group.update(range(char, char2 + 1))
			else:
				group.add(char)

		if invert:
			group.symmetric_difference_update(range(256))

		return ReChar(group)

	def parse_group_char(self):
		ch = self.peek()
		if ch == '\\':
			self.advance()
			return self.parse_esc()
		elif ch == ']':
			return None
		elif ch in GroupChars:
			self.advance()
			return ord(ch)
		else:
			self.report("invalid group character")

	def parse_string_content(self):
		re = ReEmpty()
		while True:
			ch = self.peek()
			if ch == '"':
				break
			elif ch == '\\':
				self.advance()
				re = ReConcat(re, ReChar([self.parse_esc()]))
			elif ch in Printables:
				self.advance()
				re = ReConcat(re, ReChar([ord(ch)]))
			else:
				self.report("invalid character inside string literal")
		return re

	def parse_esc(self):
		ch = self.peek()
		if ch in Escapes:
			self.advance()
			return Escapes[ch]
		elif ch == 'x':
			self.advance()
			dig1 = self.parse_hex_dig()
			dig2 = self.parse_hex_dig()
			return (dig1 * 16 + dig2)
		elif ch in Punctuation:
			self.advance()
			return ord(ch)
		else:
			self.report("invalid escape sequence")

	def parse_hex_dig(self):
		ch = self.peek()
		self.advance()
		if ch not in HexMapping:
			self.report("expected hexadecimal digit")
		return HexMapping[ch]

	def parse_ref_id(self):
		s = []
		while True:
			ch = self.peek()
			if ch in RefIDChars:
				self.advance()
				s.append(ch)
			else:
				break
		if len(s) == 0:
			self.report("expected identifier")
		return ''.join(s)

	def skip_spaces(self):
		while True:
			ch = self.peek()
			if ch in Spaces:
				self.advance()
			else:
				return

def parse_span(span):
	parser = RegexpParser()
	parser.set_source(span)
	re = parser.run()
	parser.expect(EOF)
	return re