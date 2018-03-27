#pragma once
#include <cstdint>
#include <cstddef>

#line 23 "examples/cpp/cpp.jlex"
	/*
	This code goes into the header file
	*/
#line 10 "cpp.jlex.h"

namespace cpp{

/**
* Hold lexer instance state
*/
struct Lexer{
	// base_ptr + offset points to the next input byte
    uintptr_t base_ptr;
    size_t offset;
    // end_offset is one past the last allowed offset
    size_t end_offset;

	// current internal lexer state
	uint32_t state;

	// scratch space for tokens
    uint32_t* tokens;
    // offset from the begin to the each token's end
    uint32_t* offsets;
    // how many tokens are parsed
    size_t index;



};

/**
* A list of all exclusive states.
* Allows you to switch exclusive state externally.
*/
enum class State{

Default

};

/**
* A list of all tokens
*/
namespace Token{
	enum ID : uint16_t{

Error,
Space,
OpNe,
OpHash,
OpMod,
OpModEq,
OpAnd,
OpAndEq,
Char,
OpenParen,
CloseParen,
OpMul,
OpMulEq,
OpAdd,
OpIncr,
OpAddEq,
OpComma,
OpSub,
OpDecr,
OpSubEq,
OpArrow,
OpPeriod,
OpDiv,
MlComment,
Comment,
OpDivEq,
Decimal,
Float,
Bin,
Hex,
OpColon,
OpSemi,
OpLt,
OpShl,
OpShlEq,
OpLe,
OpAssign,
OpEq,
OpGt,
OpGe,
OpShr,
OpShrEq,
OpQuestion,
Identifier,
String,
OpenBracket,
CloseBracket,
OpXor,
OpXorEq,
KAlignas,
KAlignof,
KAnd,
KAndEq,
KAsm,
KAtomicCancel,
KAtomicCommit,
KAtomicNoexcept,
KAuto,
KBitand,
KBitor,
KBool,
KBreak,
KCase,
KCatch,
KChar,
KChar16T,
KChar32T,
KClass,
KCoAwait,
KCoReturn,
KCoYield,
KCompl,
KConcept,
KConst,
KConstCast,
KConstexpr,
KContinue,
KDecltype,
KDefault,
KDelete,
KDo,
KDouble,
KDynamicCast,
KElse,
KEnum,
KExplicit,
KExport,
KExtern,
KFalse,
KFloat,
KFor,
KFriend,
KGoto,
KIf,
KImport,
KInline,
KInt,
KLong,
KModule,
KMutable,
KNamespace,
KNew,
KNoexcept,
KNot,
KNotEq,
KNullptr,
KOperator,
KOr,
KOrEq,
KPrivate,
KProtected,
KPublic,
KRegister,
KReinterpretCast,
KRequires,
KReturn,
KShort,
KSigned,
KSizeof,
KStatic,
KStaticAssert,
KStaticCast,
KStruct,
KSwitch,
KSynchronized,
KTemplate,
KThis,
KThreadLocal,
KThrow,
KTrue,
KTry,
KTypedef,
KTypeid,
KTypename,
KUnion,
KUnsigned,
KUsing,
KVirtual,
KVoid,
KVolatile,
KWcharT,
KWhile,
KXor,
KXorEq,
OpenBrace,
OpOr,
OpOrEq,
CloseBrace,
OpTild

	};
}

/// Returns a new of a given token
const char* token_name    ( Token::ID token );
/// Initializes a lexer
/// This function is not required, but may be a good idea to use nonetheless
void init                 ( Lexer* jlex_lexer );
/// Provides a space for the lexer to put the results into
/// Both tokens and offsets must have at least that many elements as the size of the input
void set_buffers          ( Lexer* jlex_lexer, uint32_t* tokens, uint32_t* offsets );
/// Provides an input for the lexer
/// 'End of stream' signal must be provided explicitly with finalize
void feed                 ( Lexer* jlex_lexer, const uint8_t* data, size_t len, size_t data_offset );
/// Sets exclusive state for the lexer
void set_state            ( Lexer* jlex_lexer, State state );
/// Runs the lexer (consumes the whole input stream)
void run                  ( Lexer* jlex_lexer );
/// Tells the lexer that no more input is expected (maybe accepts one more token)
void finalize             ( Lexer* jlex_lexer );
/// Returns a pointer to the token stream generated by the lexer
/// This always starts at the start of jlex_lexer->tokens, and has jlex_lexer->index tokens
Token::ID* convert_tokens_ids ( Lexer* jlex_lexer );
/// Returns a pointer to the array of token ends
/// Always returns 'offsets' argument of the most recent set_buffers function
uint32_t* get_tokens_ends     ( Lexer* jlex_lexer );
/// Returns the total number of tokens parsed
size_t get_tokens_count       ( Lexer* jlex_lexer );



}