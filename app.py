import ast
import html
import json
import math
import re

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Abdul Wahab's Calculator", page_icon="🧮", layout="centered",
    initial_sidebar_state="expanded",
)

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

/* hidden holder for the keyboard script */
.st-key-kbd { position: absolute; width: 0; height: 0; overflow: hidden; margin: 0; padding: 0; }

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
.prev { display: flex; justify-content: space-between; gap: .6rem; color: var(--muted);
        font-size: .85rem; min-height: 1.3rem; }
.prev span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mem { font-weight: 800; color: #4A49CB; }
.err { text-align: right; color: #C0453D; font-size: .8rem; font-weight: 600; min-height: 1.1rem; }
.st-key-screen [data-baseweb="input"], .st-key-screen [data-baseweb="base-input"] {
    background: transparent !important; border: none !important; box-shadow: none !important;
}
.st-key-screen input {
    background: transparent !important; color: var(--ink) !important; text-align: right;
    font-size: 2.1rem; font-weight: 700; height: 3rem; padding: 0 !important;
    letter-spacing: -.02em; font-variant-numeric: tabular-nums;
    caret-color: transparent; cursor: default;
}
.st-key-screen input::placeholder { color: #B4BDCD; }
.st-key-screen [data-testid="InputInstructions"] { display: none; }

/* history entries */
.hist { color: #3E4A66; font-size: .92rem; padding: .25rem 0; border-bottom: 1px solid rgba(44,60,100,.08); }
.hist-empty { color: var(--muted); font-size: .9rem; }

/* left panel (history + keyboard shortcuts) */
[data-testid="stSidebar"] { background: #F3F6FB; border-right: 1px solid rgba(44,60,100,.08); }
.side-title { font-weight: 700; font-size: 1.05rem; color: var(--ink); margin: .2rem 0 .4rem; }
[data-testid="stSidebar"] table { font-size: .82rem; }
[data-testid="stSidebar"] th, [data-testid="stSidebar"] td { color: #3E4A66; padding: .35rem .5rem; }
[data-testid="stSidebar"] code { background: #E3E9F4; color: #3E4A66; border-radius: 6px; padding: .1rem .35rem; font-size: .78rem; }
.side-note { color: var(--muted); font-size: .8rem; line-height: 1.5; }

/* a key flashes when you press it on the keyboard */
.st-key-calc button.kbd-press { transform: scale(.93) !important; filter: brightness(.9) !important; }

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
defaults = {
    "expr": "",       # what is on the display
    "ans": 0,         # last answer (Ans key)
    "memory": 0,      # memory (M+ M- MR MC)
    "history": [],    # past calculations
    "error": "",      # error message under the display
    "fresh": False,   # True right after "=": typing a number starts a new calculation
}
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
    # 5!  or  (2+3)!   ->  factorial(5)
    e = re.sub(r"(\d+(?:\.\d+)?|\([^()]*\))!", r"factorial(\1)", e)
    # implicit multiplication: 2pi, 3(4+5), 2sin(30), (1+2)(3+4)
    e = re.sub(r"(\d|\))\s*(?=[a-zA-Z(])", r"\1*", e)
    e = re.sub(r"\b(pi|ans|e)\b\s*(?=[\d(a-zA-Z])", r"\1*", e)
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


def close_brackets(expr: str) -> str:
    """Add any missing ")" so that sin(30 works like sin(30)."""
    return expr + ")" * max(0, expr.count("(") - expr.count(")"))


def is_degrees() -> bool:
    return st.session_state.get("angle") != "RAD"


# ---------------------------------------------------------------
# 4. CALLBACKS (run when a key is pressed)
# ---------------------------------------------------------------
def calculate():
    s = st.session_state
    expr = s.expr.strip()
    s.error = ""
    if not expr:
        return
    expr = close_brackets(expr)
    try:
        value = safe_eval(prepare(expr), build_namespace(is_degrees()))
        text = fmt(value)
        s.history.append(f"{expr} = {text}")
        s.ans = value
        s.expr = text      # so you can keep calculating
        s.fresh = True     # next number starts a new calculation
    except ZeroDivisionError:
        s.error = "Cannot divide by zero"
    except (ValueError, OverflowError):
        s.error = "Math error. Check the input."
    except SyntaxError:
        s.error = "Invalid expression."
    except Exception:
        s.error = "Something went wrong."


def memory_action(token: str):
    s = st.session_state
    s.error = ""
    if token == "MC":
        s.memory = 0
    elif token == "MR":
        if s.fresh:
            s.expr = ""
        s.expr += fmt(s.memory)
        s.fresh = False
    else:  # M+ or M-
        try:
            value = safe_eval(prepare(close_brackets(s.expr.strip())), build_namespace(is_degrees()))
            if isinstance(value, complex):
                raise ValueError("complex")
        except Exception:
            s.error = "Enter a valid number first"
            return
        s.memory = s.memory + value if token == "M+" else s.memory - value
        s.fresh = True


# keys that continue from the previous result instead of starting over
CONTINUE_TOKENS = {"+", "-", "*", "/", "^", "%", "!", "^2"}


def press(token: str):
    s = st.session_state
    if token == "CLEAR":
        s.expr, s.error, s.fresh = "", "", False
    elif token == "BACK":
        s.expr, s.error, s.fresh = s.expr[:-1], "", False
    elif token == "EQ":
        calculate()
    elif token == "NEG":
        e = s.expr
        if e:
            s.expr = e[2:-1] if (e.startswith("-(") and e.endswith(")")) else f"-({e})"
    elif token in ("MC", "MR", "M+", "M-"):
        memory_action(token)
    else:
        if s.fresh and token not in CONTINUE_TOKENS:
            s.expr = ""   # a number or function after "=" starts a new calculation
        s.fresh = False
        s.error = ""
        s.expr += token


# ---------------------------------------------------------------
# 5. KEYBOARD SUPPORT
# ---------------------------------------------------------------
# Streamlit cannot read the keyboard itself, so this small script listens for
# key presses and clicks the matching on-screen button.
KEYBOARD_JS = r"""
(function () {
  const KEYMAP = __KEYMAP__;
  let win, doc;
  try { win = window.parent; doc = win.document; } catch (err) { return; }

  const SIMPLE = {
    "0":"0","1":"1","2":"2","3":"3","4":"4","5":"5","6":"6","7":"7","8":"8","9":"9",
    ".":".", "+":"+", "-":"-", "*":"*", "/":"/", "^":"^", "(":"(", ")":")",
    "!":"!", "%":"%", "=":"EQ"
  };
  const SPECIAL = { Enter:"EQ", Backspace:"BACK", Delete:"CLEAR", Escape:"CLEAR" };
  const LETTERS = {
    s:"sin(", c:"cos(", t:"tan(", r:"sqrt(", l:"log(", n:"ln(", p:"pi", e:"e",
    a:"ans", q:"^2", f:"!", b:"abs(", m:"%", x:"exp(",