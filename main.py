import argparse
import json
import sys
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedInput


GRAMMAR = r"""
    start: program

    program: const_decl* value

    const_decl: NAME "is" value          -> const_decl

    ?value: number
          | array
          | dict
          | const_ref

    number: NUMBER                       -> number

    array: "[" value+ "]"                -> array

    dict: "struct" "{" [pair ("," pair)*] "}" -> dict
    pair: NAME "=" value                 -> pair

    const_ref: "!(" NAME ")"             -> const_ref

    NAME: /[_a-zA-Z]+/
    NUMBER: /\d*\.\d+/

    %import common.WS_INLINE
    %import common.NEWLINE
    %ignore WS_INLINE
    %ignore NEWLINE
"""

class ASTBuilder(Transformer):
    def number(self, items):
        (token,) = items
        return ("number", float(token))

    def array(self, items):
        return ("array", list(items))

    def pair(self, items):
        name_token, value = items
        return ("pair", str(name_token), value)

    def dict(self, items):
        return ("dict", items)

    def const_decl(self, items):
        name_token, value = items
        return ("const_decl", str(name_token), value)

    def const_ref(self, items):
        (name_token,) = items
        return ("const_ref", str(name_token))

    def program(self, items):
        return ("program", items)

def build_ast(tree):
    builder = ASTBuilder()
    return builder.transform(tree)

class ConstEvalError(Exception):
    pass

def eval_value(node, consts):
    tag = node[0]

    if tag == "number":
        return node[1]

    if tag == "array":
        _, items = node
        return [eval_value(item, consts) for item in items]

    if tag == "dict":
        _, pairs = node
        result = {}
        for _, name, value_node in pairs:
            value = eval_value(value_node, consts)
            result[name] = value
        return result

    if tag == "const_ref":
        _, name = node
        if name not in consts:
            raise ConstEvalError(f"Use of undefined constant '{name}'")
        return consts[name]

    raise ConstEvalError(f"Unknown AST node: {node}")

def eval_program(ast_root):
    consts = {}
    if not isinstance(ast_root, list):
        raise ConstEvalError("Internal error: program AST must be a list")

    if not ast_root:
        raise ConstEvalError("Empty program: no value defined")

    *decls, main_value = ast_root

    for node in decls:
        tag = node[0]
        if tag != "const_decl":
            raise ConstEvalError("Internal error: unexpected node before main value")
        _, name, value_node = node
        value = eval_value(value_node, consts)
        consts[name] = value

    result_value = eval_value(main_value, consts)
    return result_value, consts


def parse_program(text):
    parser = Lark(GRAMMAR, start="program", parser="lalr")
    try:
        tree = parser.parse(text)
    except UnexpectedInput as e:

        sys.stderr.write("Syntax error:\n")
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)


    builder = ASTBuilder()
    ast_nodes = [builder.transform(child) for child in tree.children]
    return ast_nodes


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-i", "--input", required=True,
    )
    argp.add_argument(
        "-o", "--output", required=True,
    )
    args = argp.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        sys.stderr.write(f"Cannot read input file: {e}\n")
        sys.exit(1)

    ast_nodes = parse_program(text)

    try:
        result_value, consts = eval_program(ast_nodes)
    except ConstEvalError as e:
        sys.stderr.write(f"Semantic error: {e}\n")
        sys.exit(1)

    # Записываем JSON в файл
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result_value, f, ensure_ascii=False, indent=2)
    except OSError as e:
        sys.stderr.write(f"Cannot write output file: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
