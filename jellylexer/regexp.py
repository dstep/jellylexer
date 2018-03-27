import jellylexer.nfa as nfa


class ReChar:
	def __init__(self, chars):
		self.chars = frozenset(chars)

	def build_nfa(self, ctx, begin, end):
		begin.add_trans(self.chars, end)


class ReEmpty:
	def __init__(self):
		pass

	def build_nfa(self, ctx, begin, end):
		begin.add_etrans(end)


class ReRef:
	def __init__(self, loc, id):
		self.loc = loc
		self.id = id

	def build_nfa(self, ctx, begin, end):
		fragment = ctx.get_fragment(self.loc, self.id)
		fragment.build_nfa(ctx, begin, end)


class ReConcat:
	def __init__(self, left, right):
		self.left = left
		self.right = right

	def build_nfa(self, ctx, begin, end):
		mid = nfa.State()
		self.left.build_nfa(ctx, begin, mid)
		self.right.build_nfa(ctx, mid, end)


class ReStar:
	def __init__(self, re):
		self.re = re

	def build_nfa(self, ctx, begin, end):
		mid_begin = nfa.State()
		mid_end = nfa.State()

		begin.add_etrans(mid_begin)
		begin.add_etrans(end)
		mid_end.add_etrans(mid_begin)
		mid_end.add_etrans(end)

		self.re.build_nfa(ctx, mid_begin, mid_end)


class ReChoice:
	def __init__(self, left, right):
		self.left = left
		self.right = right

	def build_nfa(self, ctx, begin, end):
		left_begin = nfa.State()
		left_end = nfa.State()
		right_begin = nfa.State()
		right_end = nfa.State()

		begin.add_etrans(left_begin)
		begin.add_etrans(right_begin)
		left_end.add_etrans(end)
		right_end.add_etrans(end)

		self.left.build_nfa(ctx, left_begin, left_end)
		self.right.build_nfa(ctx, right_begin, right_end)


class RePrefix:
	def __init__(self, re):
		self.re = re

	def build_nfa(self, ctx, begin, end):
		mid_begin = nfa.State()
		mid_end = nfa.State()
		self.re.build_nfa(ctx, mid_begin, mid_end)

		def visitor(state):
			state.add_etrans(end)

		mid_begin.visit(visitor)

		begin.add_etrans(mid_begin)