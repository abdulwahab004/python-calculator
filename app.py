import ast
import math
import re

import streamlit as st

st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="centered")

# ---------------------------------------------------------------
# 1. Session state (Streamlit reruns the script on every click,
#    so anything we want to remember must live here)
# ---------------------------------------------------------------
defaults = {"expr": "", "ans": 0, "history": [], "error": "", "result": ""}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------------
# 2. Math helpers
# ---------------------------------------------------------------
def factorial(n):
    if n != int(n) or n < 0 or n > 170:
        raise ValueError("bad factorial")
    return math.factorial(int(n))


def build_namespace(degrees: bool):
    """Functions and constants the user is allowed to use."""
    if degrees:
        to_rad = math.radians
        from_rad = math.degrees
    else:
        to_rad = lambda x: x
        from_rad = lambda x: x

    return {
        # trig
        "sin": lambda x: math.sin(to_rad(x)),
        "cos": lambda x: math.cos(to_rad(x)),
        "tan": lambda x: math.tan(to_rad(x)),
        "asin": lambda x: from_rad(math.asin(x)),
        "acos": lambda x: from_rad(math.acos(x)),
        "atan": lambda x: from_rad(math.atan(x)),
        # other functions
        "sqrt": math.sqrt,
        "log": math.log10,
        "ln": math.log,
        "exp": math.exp,
        "abs": abs,
        "factorial": factorial,
        # constants
        "pi": math.pi,
        "e": math.e,
        "ans": st.session_state.ans,
    }


ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant,
    ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.FloorDiv, ast.USub, ast.UAdd,
)


def safe_eval(expression: str, namespace: dict):
    """Evaluate a math expression without allowing arbitrary Python code."""
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError("not allowed")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in namespace:
                raise ValueError("not allowed")
            if node.keywords:
                raise ValueError("not allowed")
        if isinstance(node, ast.Name) and node.id not in namespace:
            raise ValueError("unknown name")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("not allowed")
    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, namespace)


def prepare(expression: str) -> str:
    """Turn what the user sees into valid Python."""
    e = expression.replace("^", "**").replace("×", "*").replace("÷", "/")
    e = e.replace("π", "pi").replace("√", "sqrt")
    e = re.sub(r"(\d+)!", r"factorial(\1)", e)  # 5!  ->  factorial(5)
    return e


def fmt(value) -> str:
    if isinstance(value, complex):
        raise ValueError("complex")
    if isinstance(value, int):
        return str(value)
    value = round(value, 12)  # cleans up things like sin(180) = 1.2e-16
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.10g}"


# ---------------------------------------------------------------
# 3. Button / calculation callbacks
# ---------------------------------------------------------------
def calculate():
    expr = st.session_state.expr.strip()
    st.session_state.error = ""
    st.session_state.result = ""
    if not expr:
        return
    degrees = st.session_state.angle == "Degrees"
    try:
        value = safe_eval(prepare(expr), build_namespace(degrees))
        text = fmt(value)
        st.session_state.history.append(f"{expr} = {text}")
        st.session_state.ans = float(value) if not isinstance(value, int) else value
        st.session_state.result = text
        st.session_state.expr = text  # so you can keep calculating
    except ZeroDivisionError:
        st.session_state.error = "Cannot divide by zero"
    except (ValueError, OverflowError):
        st.session_state.error = "Math error (check the input)"
    except SyntaxError:
        st.session_state.error = "Invalid expression"
    except Exception:
        st.session_state.error = "Something went wrong"


def press(token: str):
    if token == "CLEAR":
        st.session_state.expr = ""
        st.session_state.error = ""
        st.session_state.result = ""
    elif token == "BACK":
        st.session_state.expr = st.session_state.expr[:-1]
    elif token == "EQ":
        calculate()
    else:
        st.session_state.expr += token


# ---------------------------------------------------------------
# 4. User interface
# ---------------------------------------------------------------
st.title("🧮 Scientific Calculator")

st.radio("Angle mode", ["Degrees", "Radians"], horizontal=True, key="angle")

st.text_input(
    "Expression (type here or use the buttons, press Enter to calculate)",
    key="expr",
    on_change=calculate,
    placeholder="e.g. sin(30) + 2^3 * sqrt(16)",
)

if st.session_state.error:
    st.error(st.session_state.error)
elif st.session_state.result:
    st.success(f"Result: **{st.session_state.result}**")

# (label shown on button, text inserted / action)
ROWS = [
    [("sin", "sin("), ("cos", "cos("), ("tan", "tan("), ("(", "("), (")", ")")],
    [("sin⁻¹", "asin("), ("cos⁻¹", "acos("), ("tan⁻¹", "atan("), ("xʸ", "^"), ("√", "sqrt(")],
    [("log", "log("), ("ln", "ln("), ("π", "pi"), ("e", "e"), ("n!", "!")],
    [("abs", "abs("), ("mod", "%"), ("eˣ", "exp("), ("10ˣ", "10^"), ("1/x", "1/(")],
    [("7", "7"), ("8", "8"), ("9", "9"), ("÷", "/"), ("⌫", "BACK")],
    [("4", "4"), ("5", "5"), ("6", "6"), ("×", "*"), ("C", "CLEAR")],
    [("1", "1"), ("2", "2"), ("3", "3"), ("−", "-"), ("Ans", "ans")],
    [("0", "0"), (".", "."), ("x²", "^2"), ("+", "+"), ("=", "EQ")],
]

for r, row in enumerate(ROWS):
    cols = st.columns(5)
    for c, (label, token) in enumerate(row):
        cols[c].button(
            label,
            key=f"btn_{r}_{c}",
            on_click=press,
            args=(token,),
            width="stretch",
            type="primary" if token == "EQ" else "secondary",
        )

# History in the sidebar
with st.sidebar:
    st.header("History")
    if st.session_state.history:
        for item in reversed(st.session_state.history[-15:]):
            st.write(item)
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("No calculations yet.")