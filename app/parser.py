"""Parser for the Antimony-like model text. Errors carry line numbers."""
import ast
import random
import re

from .model import Model, Reaction, propensity

NAME = r"[A-Za-z_][A-Za-z0-9_]*"
ARROW = re.compile(r"->|=>")
BAD_ARROW = re.compile(r"<->|<=>|<-|<=")
TERM = re.compile(rf"^(\d+)?\s*(\$?{NAME})$")
DECL = re.compile(rf"^(const\s+)?(var\s+)?species\s+(.+)$")
ASSIGN = re.compile(rf"^\$?({NAME})\s*=\s*(.+)$")
LABEL = re.compile(rf"^({NAME})\s*:\s*(.*)$")


class ParseError(ValueError):
    def __init__(self, line, message):
        self.line = line
        self.message = message
        super().__init__(f"Line {line}: {message}")


def _syntax(line, text, reason=None):
    extra = f" ({reason})" if reason else ""
    return ParseError(line, f"syntax error: {text}{extra}")


def _strip_comment(line):
    cut = len(line)
    for marker in ("#", "//"):
        i = line.find(marker)
        if i != -1:
            cut = min(cut, i)
    return line[:cut]


def _parse_side(text, lineno, stmt):
    """'2 A + $X' -> {'A': 2, '$X': 1}; empty -> {}. Returns dict keyed by raw token name (may start with $)."""
    side = {}
    if text.strip() == "":
        return side
    for term in text.split("+"):
        m = TERM.match(term.strip())
        if not m:
            raise _syntax(lineno, stmt, f"cannot read '{term.strip()}'")
        n = int(m.group(1)) if m.group(1) else 1
        if n < 1:
            raise _syntax(lineno, stmt, "stoichiometry must be a positive integer")
        name = m.group(2)
        side[name] = side.get(name, 0) + n
    return side


def _allowed_rate_ast(node):
    if isinstance(node, ast.Expression):
        return _allowed_rate_ast(node.body)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        return _allowed_rate_ast(node.left) and _allowed_rate_ast(node.right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _allowed_rate_ast(node.operand)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return True
    return isinstance(node, ast.Name)


def _names_in(tree):
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def _check_rate(rx, rate_text, species_set, stmt):
    """Return the rate constant's name. Accepts a bare constant or an explicit mass-action expression."""
    rate_text = rate_text.replace("$", "").strip()
    if re.fullmatch(NAME, rate_text) and rate_text not in species_set:
        return rate_text
    try:
        tree = ast.parse(rate_text, mode="eval")
    except SyntaxError:
        raise _syntax(rx.line, stmt, "cannot read the rate")
    if not _allowed_rate_ast(tree):
        raise _syntax(rx.line, stmt, "rate must be a constant or a mass-action expression")
    consts = _names_in(tree) - species_set
    if len(consts) != 1:
        raise _syntax(rx.line, stmt, "rate must use exactly one rate constant")
    (k,) = consts
    # Compare the expression with the true mass-action propensity at random counts.
    idx = {s: i for i, s in enumerate(sorted(species_set))}
    pairs = [(idx[s], n) for s, n in rx.reactants.items()]
    rng = random.Random(1)
    for _ in range(8):
        counts = [rng.randint(0, 9) for _ in idx]
        env = {s: counts[i] for s, i in idx.items()}
        env[k] = 1.7
        try:
            value = eval(compile(tree, "<rate>", "eval"), {"__builtins__": {}}, env)
        except ZeroDivisionError:
            raise _syntax(rx.line, stmt, "division by zero in rate")
        expected = propensity(1.7, pairs, counts)
        if abs(value - expected) > 1e-9 * max(1.0, abs(expected)):
            raise _syntax(rx.line, stmt, "rate is not the mass-action expression for this reaction")
    return k


def parse_model(text):
    species = []          # order of first appearance
    first_line = {}       # species/constant name -> first line it appears
    boundary = set()
    reactions = []        # (Reaction with raw dict names resolved later, rate_text, stmt)
    assignments = {}      # name -> (value_text, line)
    used_names = set()
    auto = 0

    def add_species(name, lineno):
        if name.startswith("$"):
            name = name[1:]
            boundary.add(name)
        if name not in species:
            species.append(name)
            first_line[name] = lineno
        return name

    for lineno, raw in enumerate(text.splitlines(), start=1):
        pieces = [p.strip() for p in _strip_comment(raw).split(";")]
        pieces = [p for p in pieces if p]
        i = 0
        while i < len(pieces):
            stmt = pieces[i]
            i += 1
            if BAD_ARROW.search(stmt):
                raise _syntax(lineno, stmt, "reversible arrows are not supported")
            if ARROW.search(stmt):
                if i >= len(pieces):
                    raise _syntax(lineno, stmt, "reaction has no rate")
                rate_text = pieces[i]
                i += 1
                m = LABEL.match(stmt)
                name = None
                body = stmt
                if m:
                    name, body = m.group(1), m.group(2)
                parts = ARROW.split(body)
                if len(parts) != 2:
                    raise _syntax(lineno, stmt, "one arrow per reaction")
                left = _parse_side(parts[0], lineno, stmt)
                right = _parse_side(parts[1], lineno, stmt)
                auto += 1
                if name is None:
                    name = f"J{auto}"
                if any(r[0].name == name for r in reactions):
                    raise _syntax(lineno, stmt, f"duplicate reaction name '{name}'")
                reactants, products = {}, {}
                for d, out in ((left, reactants), (right, products)):
                    for sp, n in d.items():
                        clean = add_species(sp, lineno)
                        out[clean] = out.get(clean, 0) + n
                reactions.append((Reaction(name, reactants, products, "", lineno), rate_text, stmt))
                continue
            m = DECL.match(stmt)
            if m:
                const = bool(m.group(1))
                for item in m.group(3).split(","):
                    item = item.strip()
                    if not re.fullmatch(rf"\$?{NAME}", item):
                        raise _syntax(lineno, stmt, f"cannot read '{item}'")
                    clean = add_species(item, lineno)
                    if const:
                        boundary.add(clean)
                continue
            m = ASSIGN.match(stmt)
            if m:
                assignments[m.group(1)] = (m.group(2).strip(), lineno)
                if stmt.startswith("$"):
                    boundary.add(m.group(1))
                continue
            raise _syntax(lineno, stmt)

    if not reactions:
        raise ParseError(1, "syntax error: the model has no reactions")

    species_set = set(species)
    final_reactions = []
    for rx, rate_text, stmt in reactions:
        rx.rate_name = _check_rate(rx, rate_text, species_set, stmt)
        used_names.add(rx.rate_name)
        first_line.setdefault(rx.rate_name, rx.line)
        final_reactions.append(rx)
    # A `$X` assignment for a name that is a species marks it boundary only if it exists.
    boundary &= species_set

    initial = {}
    for s in species:
        if s not in assignments:
            raise ParseError(first_line[s], f"no value given for '{s}'")
        vtext, vline = assignments[s]
        try:
            v = float(vtext)
        except ValueError:
            raise _syntax(vline, f"{s} = {vtext}", f"'{s}' needs a non-negative integer")
        if v < 0 or v != int(v):
            raise _syntax(vline, f"{s} = {vtext}", f"'{s}' needs a non-negative integer")
        initial[s] = int(v)

    constants = {}
    for k in sorted(used_names, key=lambda n: first_line[n]):
        if k not in assignments:
            raise ParseError(first_line[k], f"no value given for '{k}'")
        vtext, vline = assignments[k]
        try:
            v = float(vtext)
        except ValueError:
            raise _syntax(vline, f"{k} = {vtext}", f"'{k}' needs a number >= 0")
        if not (v >= 0) or v == float("inf"):
            raise _syntax(vline, f"{k} = {vtext}", f"'{k}' needs a number >= 0")
        constants[k] = v

    return Model(species, initial, boundary, final_reactions, constants)
