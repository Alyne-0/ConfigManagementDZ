from main import parse_program, eval_program


def eval_text(text):
    ast_nodes = parse_program(text)
    value, consts = eval_program(ast_nodes)
    return value, consts

def test_plain_number():
    value, consts = eval_text("1.5")
    assert value == 1.5
    assert consts == {}

def test_array():
    value, _ = eval_text("[ 1.0 2.0 3.0 ]")
    assert value == [1.0, 2.0, 3.0]

def test_struct():
    text = """
    struct {
      x = 1.0,
      y = 2.0
    }
    """
    value, _ = eval_text(text)
    assert value == {"x": 1.0, "y": 2.0}

def test_const_basic():
    text = """
    pi is 3.14

    !(pi)
    """
    value, consts = eval_text(text)
    assert consts["pi"] == 3.14
    assert value == 3.14

def test_const_in_struct_and_array():
    text = """
    base is 1.0

    struct {
      v = [ !(base) 2.0 3.0 ],
      nested = struct { k = !(base) }
    }
    """
    value, consts = eval_text(text)
    assert consts["base"] == 1.0
    assert value["v"] == [1.0, 2.0, 3.0]
    assert value["nested"]["k"] == 1.0
