from jellylib.error import Error

EOF = object()

Newlines = frozenset("\n\r")
LineEnd = frozenset(['\n', '\r', EOF])
Whitespaces = frozenset(" \t")
Spaces = frozenset("\n\r\t ")
LowerLetter = frozenset("abcdefghijklmnopqrstuvwxyz")
UpperLetter = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
Digit = frozenset("0123456789")
Printables = frozenset(map(chr, range(32, 127)))
Graphicals = frozenset(map(chr, range(33, 127)))
Punctuation = Graphicals.difference(LowerLetter | UpperLetter | Digit)

class SourceOpts:
	def __init__(self, tab_size):
		self.tab_size = tab_size


class SourceFile:
	def __init__(self, filename, opts):
		self.filename = filename
		self.data = []
		self.lines = None
		self.opts = opts

	def feed(self, chr_seq):
		self.data.extend(chr_seq)

	def compare_pos(self, pos1, pos2):
		return pos1 == pos2

	def loc(self, pos):
		return SourceLoc(self, pos, pos)

	def advance_pos(self, pos):
		return pos + 1

	def at_pos(self, idx):
		return self.data[idx]

	def get_span(self):
		return (self, 0, len(self.data))

	def get_line_col_info(self, pos):
		if not self.lines:
			self._fill_line_info()
		line = self._bin_search_line(pos)
		p = self.lines[line]
		col = 0
		while p < pos:
			ch = self.data[p]
			if ch == '\t':
				col = (col + self.opts.tab_size) // self.opts.tab_size * self.opts.tab_size
			elif ch in '\n\r':
				pass
			else:
				col += 1
			p += 1
		return line + 1, col + 1

	def _bin_search_line(self, pos):
		begin = 0
		end = len(self.lines)
		while end - begin > 1:
			mid = (end + begin) // 2
			if self.lines[mid] > pos:
				end = mid
			else:
				begin = mid
		return begin

	def _fill_line_info(self):
		self.lines = [0]
		state = 0
		for i, ch in enumerate(self.data):
			if (state == 1) or (state == 2 and ch != '\n'):
				self.lines.append(i)
				state = 0
			if ch == '\n':
				state = 1
			elif ch == '\r':
				state = 2


class SourceLoc:
	def __init__(self, file, begin:int, end:int):
		self.file = file
		self.begin = begin
		self.end = end

	def to(self, end):
		return SourceLoc(self.file, self.begin, end.end)

	def line(self):
		line, col = self.file.get_line_col_info(self.begin)
		return line

	def filename(self):
		return self.file.filename

	def __str__(self):
		cl_info = None

		if self.begin == self.end:
			line, col = self.file.get_line_col_info(self.begin)
			cl_info = "line {line}, col {col}".format(line=line, col=col)
		else:
			line1, col1 = self.file.get_line_col_info(self.begin)
			line2, col2 = self.file.get_line_col_info(self.end)
			cl_info = "{line1},{col1}:{line2},{col2}".format(line1=line1, col1=col1, line2=line2, col2=col2)

		if self.file.filename:
			return "{file}({loc})".format(file=self.file.filename, loc=cl_info)
		else:
			return cl_info


class ArtificialSource:
	def __init__(self, loc):
		self.myloc = loc
		self.data = []

	def feed(self, chr_seq):
		self.data.extend(chr_seq)

	def compare_pos(self, pos1, pos2):
		return pos1 == pos2

	def loc(self, pos):
		return self.myloc

	def advance_pos(self, pos):
		return pos + 1

	def at_pos(self, idx):
		return self.data[idx]

	def get_span(self):
		return (self, 0, len(self.data))


class SourceSpans:
	def __init__(self):
		self.spans = []

	def add_span(self, provider, begin, end):
		self.spans.append((provider, begin, end))

	def add_seq(self, loc, seq):
		src = ArtificialSource(loc)
		src.feed(seq)
		self.spans.append(src.get_span())

	def loc(self, pos):
		return self.spans[pos[0]][0].loc(pos[1])

	def compare_pos(self, pos1, pos2):
		pos1 = self.skip_empty(pos1)
		pos2 = self.skip_empty(pos2)
		return pos1 == pos2

	def at_pos(self, pos):
		pos = self.skip_empty(pos)
		return self.spans[pos[0]][0].at_pos(pos[1])

	def advance_pos(self, pos):
		span = self.spans[pos[0]]
		if span[0].compare_pos(pos[1], span[2]):
			pos = (pos[0] + 1, self.spans[pos[0] + 1][1])
		else:
			pos = (pos[0], span[0].advance_pos(pos[1]))
		return self.skip_empty(pos)

	def skip_empty(self, pos):
		while True:
			span = self.spans[pos[0]]
			if span[0].compare_pos(pos[1], span[2]) and pos[0] < len(self.spans) - 1:
				pos = (pos[0] + 1, self.spans[pos[0] + 1][1])
			else:
				return pos

	def begin_pos(self):
		return (0, self.spans[0][1])

	def end_pos(self):
		return (len(self.spans) - 1, self.spans[-1][2])

	def get_span(self):
		return self, self.begin_pos(), self.end_pos()


class InputStream:
	def __init__(self, provider, begin:int, end:int):
		self.provider = provider
		self.begin = begin
		self.end = end
		self.cur = begin

	def get_span(self, begin, end):
		return (self.provider, begin, end)

	def tell(self):
		return self.cur

	def rewind(self, pos):
		self.cur = pos

	def reset(self):
		self.cur = self.begin

	def loc(self):
		return self.provider.loc(self.cur)

	def peek(self):
		if self.provider.compare_pos(self.cur, self.end):
			return EOF
		return self.provider.at_pos(self.cur)

	def advance(self):
		if self.is_eof():
			return
		self.cur = self.provider.advance_pos(self.cur)

	def is_eof(self):
		return self.peek() is EOF


class ParseError(Error):
	def __init__(self, *args):
		super().__init__(*args)

class Parser:
	def __init__(self):
		self.stream = None

	def set_source(self, source):
		self.stream = InputStream(*source.get_span())

	def set_stream(self, stream):
		self.stream = stream

	def peek(self):
		return self.stream.peek()

	def is_eof(self):
		return self.stream.is_eof()

	def loc(self):
		return self.stream.loc()

	def advance(self):
		self.stream.advance()

	def take(self):
		ch = self.stream.peek()
		if ch is EOF:
			return EOF
		self.stream.advance()
		return ch

	def tell(self):
		return self.stream.tell()

	def rewind(self, pos):
		self.stream.rewind(pos)

	def get_span(self, begin, end):
		return self.stream.get_span(begin, end)

	def expect(self, ch):
		if self.peek() != ch:
			if ch == EOF:
				self.report("unexpected character")
			else:
				self.report("expected '{char}'".format(char=ch))
		self.take()

	def report(self, message, loc=None):
		if not loc:
			loc = self.loc()
		raise ParseError(loc, message)


def parse_string(source):
	p = Parser()
	p.set_source(source)
	s = []
	while not p.is_eof():
		s.append(p.take())
	return ''.join(s)