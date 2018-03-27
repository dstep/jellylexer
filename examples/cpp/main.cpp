#include <cstdio>
#include <algorithm>
#include "cpp.jlex.h"

using namespace cpp;

int main(int argc, char* argv[]){
	FILE* fp = fopen(argv[1], "rb");
	fseek(fp, 0, SEEK_END);
	int size = ftell(fp);
	fseek(fp, 0, SEEK_SET);
	
	uint8_t* buf = (uint8_t*)malloc(size);
	fread(buf, size, 1, fp);
	
	uint32_t* output = (uint32_t*)malloc(size * 8 + 4);
	
	Lexer lexer;
	init(&lexer);
	set_buffers(&lexer, output, output + size + 1);
	set_state(&lexer, State::Default);
	feed(&lexer, buf, size, 0);
	
	uint32_t* offsets = output + size;
	offsets[0] = 0;
		
	run(&lexer);
	finalize(&lexer);
	
	printf("Parsing %d bytes done, parsed %d tokens.\n", size, lexer.index);
	printf("Some tokens are: \n");
	Token::ID* tokens = convert_tokens_ids(&lexer);
	size_t tokens_num = get_tokens_count(&lexer);
	
	uint32_t token_begin = 0;
	
	for ( size_t i = 0; i < 5; i++ ){
		if ( i >= tokens_num ){
			break;
		}
		uint32_t token_end = offsets[i];
		printf("%s (%.*s)\n", token_name(tokens[i]), (token_end - token_begin), token_begin + buf);
		token_begin = token_end;
	}
	
	printf(" ... \n");
	
	for ( size_t i = tokens_num - 5; i < tokens_num; i++ ){
		if ( i < 5 ){
			continue;
		}
		uint32_t token_begin = offsets[i - 1];
		uint32_t token_end = offsets[i];
		printf("%s (%.*s)\n", token_name(tokens[i]), (token_end - token_begin), token_begin + buf);
	}
}