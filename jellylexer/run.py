from jellylib.parsing import *
from jellylexer.project import parse_project
from jellylexer.codegen import Codegen
from jellylib.log import log, set_verbosity
import argparse
import sys
import os

parser = argparse.ArgumentParser(description="Lexer generator")
parser.add_argument('--dir', metavar='dir', type=str, help="output directory")
parser.add_argument('--src', metavar='file', type=str, help="source file (output)")
parser.add_argument('--header', metavar='file', type=str, help="header file (output)")
parser.add_argument('input', metavar='input_file', type=str, help="grammar file")
parser.add_argument("-v", "--verbosity", action="count", default=0, help="increase output verbosity")

args = parser.parse_args()

set_verbosity(args.verbosity)

try:
	dir = args.dir
	if not dir:
		dir = os.getcwd()

	input_file = args.input

	log(2, "Working directory {dir}", dir=repr(dir))
	log(2, "Reading {input}...", input=repr(input_file))

	with open(input_file, "r") as f:
		source = SourceFile(input_file, SourceOpts(4))
		source.feed(f.read())

	project_name, _ = os.path.splitext(os.path.basename(input_file))

	log(2, "Parsing project...")
	project = parse_project(source, project_name)
	codegen = Codegen()
	project.parse()
	codegen.parse(project)
	project.check_used()

	log(2, "Building grammar...")
	project.build()

	log(2, "Running codegen...")
	codegen.build(project)

	src = args.src
	if not src:
		src = project_name + ".jlex.cpp"

	header = args.header
	if not header:
		src_base, _ = os.path.splitext(src)
		header = src_base + ".h"

	header_file = os.path.join(dir, header)
	source_file = os.path.join(dir, src)

	log(2, "Source file {source}", source=repr(source_file))
	log(2, "Header file {header}", header=repr(header_file))

	log(2, "Writing header file...")
	os.makedirs(os.path.dirname(header_file), exist_ok=True)
	with open(header_file, "w") as f:
		codegen.write_header(f, os.path.relpath(header_file, dir))

	log(2, "Writing source file...")	
	os.makedirs(os.path.dirname(source_file), exist_ok=True)
	with open(source_file, "w") as f:
		codegen.write_source(f, os.path.relpath(source_file, dir))

	log(2, "Completed.")

except Error as e:
	print(e, file=sys.stderr)
	sys.exit(1)