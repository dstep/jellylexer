# Jellylexer - Lexical Analyzer Generator

## Overview

Jellylexer is a lexical analyzer generator for C++, written in Python 3. Its output is intended to be used as a fast, lightweight lexer in the compiler pipeline.

## Features

 - Generates branchless lexer, with about 12 mov/add/bitshift instructions per input byte.
 - Very small lexer core size (does not depend on the grammar complexity).
 - Re-entrant thread safe lexer
 - No memory allocations performed inside the lexer
 - Supports exclusive states (for subgrammars).

## Limitations

Generated lexer intended as a piece of a parsing pipeline, it is designed to do its part of the job as fast as possible. Due to this, it is not very flexible. What you should keep in mind when using jellylexer:

 - It is not possible to attach special actions to grammar rules (*this is more a practical limitation, it might be possible to do in the future*)
 - You must preallocate large enough buffer for the token stream, at least `8 * input size` bytes large.
   If this sounds terrible to you, the required space can be reduced by feeding input stream in chunks, and providing only `8 * chunk size` bytes per chunk as a buffer.
 - Lexer can't backtrack or look ahead.
 - Lexer does not evaluate tokens (so you need to extract numeric values or similar things in a separate step).
 - Lexer does not count lines.

## Input File

### Format Overview

Input file format is pretty simple. Instead of reading this boring description, just go look at some [examples](examples/).

Input file consists of blocks, denoted by `[headers]`:

	[block1]
	...
	[block2]

Each block contains some key-value pairs, written like so:

	[block]

	key1 value1

	key2 value2

	key3
	    multi
	    line
	    value

Comment starts with `#` and ends with the physical line end.

	# this is a comment

Note that blocks, keys and comments must start on the very first character of the line.

Keys consist of characters `a-zA-Z0-9_` and `-`.

Everything else on the same line considered a value for that key. If the line is empty, than jellylexer expects multiline indented value in the following lines. Indentation must match that of the first non-empty line.

### General Block

	[general]
	
	state state-name

  - Key `state` declares an exclusive lexer state.

### Fragments Block

	[fragments]

	fragment-name regexp

Lists fragments (named regular expression) you can reuse in the grammar (or when defining other fragments).

### Grammar Block

	[grammar]

	token-name   (token-states)* (target-state)? regexp 

Lists tokens and corresponding lexing rules.

By default, rule belongs to an implicit `default` state. If `token-states` is non-empty, rule belongs to those states instead. Each state must be in the format `{state-name}`. Special meta-state `{all}` allows you to bind the rule to all states without explicitly naming them. 

Some examples:

	# rule belongs to 'default' state
	integer      0|[1-9][0-9]*
	
	# rule belongs to 'string' state
	esc_seq      {string} \\ [nrt0]

	# rule belongs to all double_quotes_string and single_quotes_string states
	esc_seq      {double_quotes_string} {single_quotes_string} \\ [nrt0]

If `taget-state` is empty, then after successfully parsing a token, lexer resets back to the initial state of the current exclusive state. If `target-state` is non-empty, lexer resets to the initial state of that exclusive state instead. Format for `target-state` is `{-> state-name}`:

	# after parsing ", lexer goes into double_quotes_string state:
	double_quotes   {-> double_quotes_string} \"

### Regular Expressions Grammar

The grammar for regular expressions is pretty standard, except a few things. Quick reference:

 - `a b` matches `a` followed by `b`
 - `a | b` matches `a` or `b`
 - `a ?` matches empty string or `a`
 - `a +` matches any non-zero number of `a`'s
 - `a *` matches any number of `a`'s
 - `a {n}` matches exactly `n` `a`'s
 - `a {n,m}` matches any number of `a`'s between `n` and `m`
 - `( a )` matches `a`
 - `"string"` matches string `string`. Most of the special characters are allowed inside the string. All other characters (including `"` and `\`) must be escaped.
 - `[ group ]` matches any character from the `group`.
   Certain special characters must be escaped inside the `group`, like `[]\-`.
   It is possible to use *ranges* inside the `group`, with the syntax `a-b`. Range matches any byte with codes from `a` to `b` inclusive.
 - `[ ^ group ]` matches any character *except* those in the `group`
 - `\n` matches newline
 - `\r` matches linefeed
 - `\t` matches tab
 - `\#` where `#` - any punctuation character - matches that character
 - `\xXY` where `X` and `Y` - hexadecimal digits - matches byte with code `X * 16 + Y`
 - whitespace characters are ignored when not inside string literal or character group.
 - non-special character matches itself
 - control characters except `tab`, `linefeed` and `newline`, and characters with codes `>127` are not allowed

Non-standard:

 - `~ a` matches *any prefix* of `a`
 - `<fragment-name>` inserts a named fragment into the regexp. Note that as it performs a simple substitution, fragments cannot be recursive.

### Codegen Block
	
	[codegen]

	header header-code

	source source-code

	prefix lexer-prefix

  - Key `header` allows you to insert some code into the generated header.
  - Key `source` allows you to insert some code into the generated implementation file.
  - Key `prefix` changes the lexer prefix (namespace).

## Command Line Arguments


	python3 -m jellylexer.run [--dir dir] [--header file] [--src file] [-vv] input


  * `--dir dir` sets the output directory. Header and source files are relative to the output directory.
  Default: current working directory.

  * `--src file` sets the file path for the generated source file.
  Default: input file name with the extension replaced by `.jlex.cpp`

  * `--header file` sets the file path for the generated header file.
  Default: source path with the extension replaced by `.h`.

  * `-vv` enables progress indication and logging.

  * `input` sets the input file path (relative to the current working directory)

## Generated Parser

Generated header file contains all the required declarations (inside the namespace determined either by the grammar file name or `prefix` key in the `[general]` block) to use the lexer.

## Misc

### How to parse Unicode

For UTF-8, use this BNF: https://tools.ietf.org/html/rfc3629#section-4

Adapted (yet untested) fragments:

	UTF8-char    <UTF8-1> | <UTF8-2> | <UTF8-3> | <UTF8-4>
	UTF8-1       [\x00-\x7F]
	UTF8-2       [\xC2-\xDF] <UTF8-tail>
	UTF8-3
			\xE0 [\xA0-\xBF] <UTF8-tail> |
			[\xE1-\xEC] <UTF8-tail> {2}  |
			\xED [\x80-\x9F] <UTF8-tail> | 
			[\xEE-\xEF] <UTF8-tail> {2}
	UTF8-4
			\xF0 [\x90-\xBF] <UTF8-tail>{2} |
			[\xF1-\xF3] <UTF8-tail> {3}     |
			\xF4 [\x80-\x8F] <UTF8-tail>{2}
	UTF8-tail    [\x80-\xBF]

For other encodings, why do you use other encodings?

### Line Counting

Usually, the only time when you need line information from the source file is when you need to print a warning/error message. Considering there are (usually) no error messages, if you do need the line info, you should obtain it separately, possibly much later in the compiler's pipeline.

### References

Inspired by this paper: http://nothings.org/computer/lexing.html



