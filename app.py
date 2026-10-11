import ast
import html
import math
import re

import streamlit as st

st.set_page_config(page_title="Abdul Wahab's", page_icon="🧮", layout="centered")

# ---------------------------------------------------------------
# 1. STYLE  (all the look-and-feel lives here)
# ---------------------------------------------------------------
# Key colours: (background, text colour)
KEY_STYLES = {
    "num": ("#FFFFFF", "#1B2236"),   # digits
    "fn": ("#E3E9F4", "#3E4A66"),    # scientific functions
    "op": ("#D9DDFB", "#3638B5"),    # + - × ÷
    "util": ("#F8E3E0", "#B5413A"),  # C and backspace
    "eq": ("#4A49CB", "#FFFFFF"),    # equals
}

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root { --ink:#1B2236; --muted:#8791A5; --panel:#F6F8FB; --screen:#EBEFF6; }

/* page */
.stApp { background: linear-gradient(165deg, #EAEFF6 0%, #D9E1EC 100%); }
.stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp summary {
    font-family: 'Manrope', sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], footer { visibility: hidden; }
.block-container, [data-testid="stMainBlockContainer"] {
    max-width: 440px; padding-top: 2.2rem; padding-bottom: 2rem;
}

/* calculator body */
.st-key-calc {
    background: var(--panel); border-radius: 32px; padding: 20px; gap: .55rem;
    box-shadow: 0 40px 70px -30px rgba(44,60,100,.45), 0 2px 0 rgba(255,255,255,.9) inset;
}
/* keep the 5 columns side by side, even on phones */
.st-key-calc [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .5rem; }
.st-key-calc [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }

/* top bar */
.brand { font-weight: 700; font-size: 1rem; color: var(--ink); padding-top: .4rem; letter-spacing: -.01em; }
.st-key-topbar [data-testid="stColumn"]:last-child { align-items: flex-end; }

/* screen */
.st-key-screen {
    background: var(--screen); border-radius: 22px; padding: 14px 18px 10px; gap: .1rem;
    box-shadow: inset 0 2px 8px rgba(44,60,100,.12);
}
.prev { text-align: right; color: var(--muted); font-size: .85rem; min-height: 1.3rem;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.err { text-align: right; color: #C0453D; font-size: .8rem; font-weight: 600; min-height: 1.1rem; }
.st-key-screen [data-baseweb="input"], .st-key-screen [data-baseweb="base-input"] {
    background: transparent !important; border: none !important; box-shadow: none !important;
}
.st-key-screen input {
    background: transparent !important; color: var(--ink) !important; text-align: right;
    font-size: 2.1rem; font-weight: 700; height: 3rem; padding: 0 !important;
    letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.st-key-screen input::placeholder { color: #B4BDCD; }
.st-key-screen [data-testid="InputInstructions"] { display: none; }

/* history */
[data-testid="stExpander"] { background: rgba(255,255,255,.55); border: none; border-radius: 20px; margin-top: 1rem; }
[data-testid="stExpander"] summary p { color: var(--ink); font-weight: 600; }
.hist { color: #3E4A66; font-size: .92rem; padding: .25rem 0; border-bottom: 1px solid rgba(44,60,100,.08); }
.hist-empty { color: var(--muted); font-size: .9rem; }

@media (max-width: 480px) {
    .st-key-calc { padding: 14px; border-radius: 26px; }
}
"""


def build_key_css() -> str:
    """Generate the CSS for each kind of key from KEY_STYLES."""
    kinds = list(KEY_STYLES)

    def sel(kind, suffix="", tail="button"):
        return f'.st-key-calc [class*="st-key-{kind}_"] {tail}{suffix}'

    every_key = ",".join(sel(k) for k in kinds)
    every_label = ",".join(sel(k, tail="button p") for k in kinds)
    every_hover = ",".join(sel(k, ":hover") for k in kinds)
    every_active = ",".join(sel(k, ":active") for k in kinds)
    every_focus = ",".join(sel(k, ":focus-visible") for k in kinds)

    css = every_key + (
        "{height:48px;min-height:48px;width:100%;border:none !important;border-radius:16px;"
        "box-shadow:0 1px 0 rgba(255,255,255,.9) inset,0 2px 5px rgba(44,60,100,.10);"
        "transition:transform .08s ease,filter .15s ease;}"
    )
    css += every_label + "{font-size:1.02rem;font-weight:600;margin:0;color:inherit !important;}"
    css += every_hover + "{filter:brightness(.96);}"
    css += every_active + "{transform:scale(.96);}"
    css += every_focus + "{outline:2px solid #4A49CB;outline-offset:2px;}"

    for kind, (bg, fg) in KEY_STYLES.items():
        states = ",".join(sel(kind, s) for s in ["", ":hover", ":active", ":focus"])
        css += states + f"{{background:{bg} !important;color:{fg} !important;}}"

    # the equals key gets a soft glow, the one "loud" thing in the design
    css += sel("eq") + "{box-shadow:0 10px 20px -8px rgba(74,73,203,.65);}"
    return css


st.markdown(f"<style>{BASE_CSS}{build_key_css()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# 2. SESSION STATE (Streamlit reruns the script on every click)
# ---------------------------------------------------------------
defaults = {"expr": "", "ans": 0, "history": [], "error": ""}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------------
# 3. MATH HELPERS
# ---------------------------------------------------------------
def factorial(n):
    if n != int(n) or n < 0 or n > 170:
        raise ValueError("bad factorial")
    return math.factorial(int(n))


def build_namespace(degrees: bool):
    """Functions and constants the user is allowed to use."""
    if degrees:
        to_rad, from_rad = math.radians, math.degrees
    else:
        to_rad = from_rad = lambda x: x

    return {
        "sin": lambda x: math.sin(to_rad(x)),
        "cos": lambda x: math.cos(to_rad(x)),
        "tan": lambda x: math.tan(to_rad(x)),
        "asin": lambda x: from_rad(math.asin(x)),
        "acos": lambda x: from_rad(math.acos(x)),
        "atan": lambda x: from_rad(math.atan(x)),
        "sqrt": math.sqrt,
        "log": math.log10,
        "ln": math.log,
        "exp": math.exp,
        "abs": abs,
        "factorial": factorial,
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
    e = e.replace("π", "pi").replace("√", "sqrt").replace("−", "-")
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
# 4. CALLBACKS
# ---------------------------------------------------------------
def calculate():
    expr = st.session_state.expr.strip()
    st.session_state.error = ""
    if not expr:
        return
    degrees = st.session_state.get("angle") != "RAD"
    try:
        value = safe_eval(prepare(expr), build_namespace(degrees))
        text = fmt(value)
        st.session_state.history.append(f"{expr} = {text}")
        st.session_state.ans = value
        st.session_state.expr = text  # so you can keep calculating
    except ZeroDivisionError:
        st.session_state.error = "Cannot divide by zero"
    except (ValueError, OverflowError):
        st.session_state.error = "Math error. Check the input."
    except SyntaxError:
        st.session_state.error = "Invalid expression. Check brackets."
    except Exception:
        st.session_state.error = "Something went wrong."


def press(token: str):
    if token == "CLEAR":
        st.session_state.expr = ""
        st.session_state.error = ""
    elif token == "BACK":
        st.session_state.expr = st.session_state.expr[:-1]
    elif token == "EQ":
        calculate()
    else:
        st.session_state.expr += token


# ---------------------------------------------------------------
# 5. LAYOUT
# ---------------------------------------------------------------
# (label on key, text inserted / action, kind of key)
ROWS = [
    [("sin", "sin(", "fn"), ("cos", "cos(", "fn"), ("tan", "tan(", "fn"), ("(", "(", "fn"), (")", ")", "fn")],
    [("sin⁻¹", "asin(", "fn"), ("cos⁻¹", "acos(", "fn"), ("tan⁻¹", "atan(", "fn"), ("xʸ", "^", "fn"), ("√", "sqrt(", "fn")],
    [("log", "log(", "fn"), ("ln", "ln(", "fn"), ("π", "pi", "fn"), ("e", "e", "fn"), ("n!", "!", "fn")],
    [("abs", "abs(", "fn"), ("mod", "%", "fn"), ("eˣ", "exp(", "fn"), ("10ˣ", "10^", "fn"), ("1/x", "1/(", "fn")],
    [("7", "7", "num"), ("8", "8", "num"), ("9", "9", "num"), ("÷", "/", "op"), ("⌫", "BACK", "util")],
    [("4", "4", "num"), ("5", "5", "num"), ("6", "6", "num"), ("×", "*", "op"), ("C", "CLEAR", "util")],
    [("1", "1", "num"), ("2", "2", "num"), ("3", "3", "num"), ("−", "-", "op"), ("Ans", "ans", "fn")],
    [("0", "0", "num"), (".", ".", "num"), ("x²", "^2", "fn"), ("+", "+", "op"), ("=", "EQ", "eq")],
]

with st.container(key="calc"):
    # top bar: name on the left, angle mode on the right
    with st.container(key="topbar"):
        left, right = st.columns(2)
        left.markdown('<div class="brand">Scientific</div>', unsafe_allow_html=True)
        with right:
            st.segmented_control(
                "Angle mode", ["DEG", "RAD"], default="DEG",
                key="angle", label_visibility="collapsed",
            )

    # screen
    with st.container(key="screen"):
        last = html.escape(st.session_state.history[-1]) if st.session_state.history else "&nbsp;"
        st.markdown(f'<div class="prev">{last}</div>', unsafe_allow_html=True)
        st.text_input(
            "Expression", key="expr", on_change=calculate,
            placeholder="0", label_visibility="collapsed",
        )
        err = html.escape(st.session_state.error) if st.session_state.error else "&nbsp;"
        st.markdown(f'<div class="err">{err}</div>', unsafe_allow_html=True)

    # keys
    for r, row in enumerate(ROWS):
        cols = st.columns(5)
        for c, (label, token, kind) in enumerate(row):
            cols[c].button(
                label, key=f"{kind}_{r}_{c}", on_click=press, args=(token,), width="stretch",
            )

# history
with st.expander("History"):
    if st.session_state.history:
        for item in reversed(st.session_state.history[-15:]):
            st.markdown(f'<div class="hist">{html.escape(item)}</div>', unsafe_allow_html=True)
        if st.button("Clear history", key="clear_history"):
            st.session_state.history = []
            st.rerun()
    else:
        st.markdown('<div class="hist-empty">Your calculations will show up here.</div>', unsafe_allow_html=True)