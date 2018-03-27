class Error(RuntimeError):
	def __init__(self, loc, message):
		super().__init__()
		self.loc = loc
		self.message = message

	def __str__(self):
		return "{loc}: {message}".format(loc=self.loc, message=self.message)
