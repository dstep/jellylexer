$(source)

namespace $(prefix){

// Equivalence class for each input byte value.
// Lexer does not distinguish most of the input characters, like '4' and '5'
// Generator puts such characters into the same class to compress transition tables.
// Values in this table are offsets (in bytes) in the jlex_transitions table.
static const uint32_t jlex_eq_class[256] = {
$(eq_classes)
};

// Transition tables for the lexer. Each value describes how to act in a certain state,
// when certain character (equivalence class) is encountered.
//
// Upper half is ACCEPT ACTION. In bit representation:
//   XXX..... YYYYYYYY YYYYYYYY YYYYYYYY
// XXX are 100 for ACCEPT, and 000 for CONTINUE
// For ACCEPT, YYYs are Token::ID for the token
//
// Lower half is the next dfa state.
 static const uint32_t jlex_transitions[] = {
$(transitions)
};

// Transition table for end of file pseudo character class
static const uint32_t jlex_eof_transitions[] = {
$(eof_transitions)
};

// Raw token names for debug purposes
static const char* jlex_token_names[] = {
$(token_names)
};

const char* token_name( Token::ID token ){
	return jlex_token_names[token];
}

void init      ( Lexer* jlex_lexer ){
	jlex_lexer->offset = 0;
	jlex_lexer->end_offset = 0;
	jlex_lexer->base_ptr = 0;

	jlex_lexer->state = 0;
	jlex_lexer->tokens = nullptr;
	jlex_lexer->offsets = nullptr;
	jlex_lexer->index = 0;
}

void set_buffers ( Lexer* jlex_lexer, uint32_t* tokens, uint32_t* offsets ){
	jlex_lexer->tokens = tokens;
	jlex_lexer->offsets = offsets;
	jlex_lexer->index = 0;
}

void feed       ( Lexer* jlex_lexer, const uint8_t* data, size_t len, size_t data_offset ){
	jlex_lexer->offset = data_offset;
	jlex_lexer->base_ptr = ((uintptr_t)data) - data_offset;
	jlex_lexer->end_offset = data_offset + len;
}

void set_state ( Lexer* jlex_lexer, State state ){
	switch ( state ){
	$(set_state_switch)
	}
}

#if defined(__GNUC__)
#	define jlex_unlikely(e) __builtin_expect((e), 0)
#else
#	define jlex_unlikely(e) (e)
#endif

void run       ( Lexer* jlex_lexer ){
	// Copy stuff from jlex_lexer intro local variables
	// so wed dont confuse optimizer with false aliasing

	uintptr_t jlex_input_base = jlex_lexer->base_ptr;

	uint32_t jlex_state = jlex_lexer->state;
	uint32_t* __restrict jlex_tokens = jlex_lexer->tokens;
	uint32_t* __restrict jlex_offsets = jlex_lexer->offsets;

	size_t jlex_offset = jlex_lexer->offset;
	size_t jlex_max = jlex_lexer->end_offset;

	// Current output token offset in bytes
	size_t jlex_token_idx = jlex_lexer->index * 4;

	// This will only mispredict at the end of input
	while ( jlex_offset < jlex_max ){
		// Decode equivalence class of the next input byte
		uint32_t jlex_eq =  jlex_eq_class[*(const uint8_t*)(jlex_input_base + jlex_offset)];
		// Decode the nex action
		uint32_t jlex_state_next = *(const uint32_t*)(((const char*)jlex_transitions) + (jlex_state + jlex_eq));
		// Write to the current output token
		// The whole action is written, it will be converted to a token id later
		*(uint32_t*)((const char*)jlex_offsets + jlex_token_idx) = (uint32_t)(jlex_offset);
		*(uint32_t*)((const char*)jlex_tokens + jlex_token_idx) = jlex_state_next;

		// Extract lower part of the action (next dfa state)
		jlex_state = jlex_state_next & 0xffff;

		// Advance jlex_token_idx by 4 if the action is ACCEPT
		jlex_token_idx += (jlex_state_next >> 29u);

		// Go to the next byte
		jlex_offset++;
	}

$(lexer_trap)

	// Fixup lexer fields
	jlex_lexer->state = jlex_state;
	jlex_lexer->offset = jlex_offset;
	jlex_lexer->index = jlex_token_idx / 4;
}

void finalize  ( Lexer* jlex_lexer ){
	// Parse the 'end of stream' pseudo character
	// Repeats run function, but uses jlex_eof_transitions instead

	uint32_t jlex_state = jlex_lexer->state;
	uint32_t* __restrict jlex_tokens = jlex_lexer->tokens;
	uint32_t* __restrict jlex_offsets = jlex_lexer->offsets;
	size_t jlex_token_idx = jlex_lexer->index * 4;
	size_t jlex_offset = jlex_lexer->offset;

	uint32_t jlex_state_next = *(const uint32_t*)(((const char*)jlex_eof_transitions) + (jlex_state));
	*(uint32_t*)((const char*)jlex_tokens + jlex_token_idx) = jlex_state_next;
	*(uint32_t*)((const char*)jlex_offsets + jlex_token_idx) = (uint32_t)(jlex_offset);
	jlex_state = jlex_state_next & 0xffff;
	jlex_token_idx += (jlex_state_next >> 29u);

	jlex_lexer->state = jlex_state;
	jlex_lexer->index = jlex_token_idx / 4;
}

Token::ID* convert_tokens_ids ( Lexer* jlex_lexer ){
	Token::ID* output = (Token::ID*)jlex_lexer->tokens;
	uint32_t* input = jlex_lexer->tokens;

	// Reads from, and writes to the same buffer.
	// Converts dfa actions into token ids
	for ( size_t i = 0; i < jlex_lexer->index; i++ ){
		uint32_t token = input[i];
		output[i] = (Token::ID) ((token >> 16) & 0xfffu);
	}

	return (Token::ID*)jlex_lexer->tokens;
}

size_t get_tokens_count   ( Lexer* jlex_lexer ){
	return jlex_lexer->index;
}

uint32_t* get_tokens_ends ( Lexer* jlex_lexer ){
	return jlex_lexer->offsets;
}

}