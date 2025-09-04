# s_programming_language.py
# Author: David Niblick
# Date: 20250903

from itertools import count


_call_ids = count()  # unique ids for macro-call namespaces

# --------- Helpers ---------

def _resolve_labels(code, suffix):
    """
    Return (instruction_list, label_map) with labels suffixed by `suffix`.
    label_map returns index of instruction at label.
    instr_list no longer contains the labels.
    """
    labels, instr_list = {}, []
    for instr in code:
        op = instr[0]
        if op.endswith(":"):
            labels[op[:-1] + suffix] = len(instr_list)  
        else:
            instr_list.append(instr)
    return instr_list, labels


def _find_label_in_frame(label, frame):
    """
    Returns program counter (pc) index for given label within given frame.
    Handles exact or suffixed label.
    """
    lbls = frame["labels"]
    if label in lbls:
        return lbls[label]
    # allow unsuffixed label names inside the same frame (e.g., 'A' -> 'A__m7')
    for k in lbls:
        if k.startswith(label + "__"):
            return lbls[k]
    return None


def _jump(stack, target):
    """
    Find `target` starting from the current frame, then outward.
    Mutates stack to position PC at the target frame/index.
    """
    # current frame first
    idx = _find_label_in_frame(target, stack[-1])
    if idx is not None:
        stack[-1]["pc"] = idx
        return

    # walk outward
    for depth in range(len(stack) - 2, -1, -1):
        idx = _find_label_in_frame(target, stack[depth])
        if idx is not None:
            # pop back to that frame and jump
            del stack[depth + 1 :]
            stack[-1]["pc"] = idx
            return

    raise KeyError(f"Label '{target}' not found in any frame")

# --------- Interpreter ---------

def run_program(instructions, inputs=None, macros=None, max_steps=100_000, trace=False):
    """
    S-language interpreter with recursive, parameterized macros and protected namespaces.

    Primitive instructions:
      ("inc", var)        # var = var + 1
      ("dec", var)        # var = max(var - 1, 0)
      ("jnz", var, label) # if var != 0: goto label

    Define labels for convenient control:
        ("label:",)       # label definition, must end in ":"

    Macros dict format:
      macros = {
        "name": ([args...], [code...], [locals...])  # locals optional
      }
    """
    macros = macros or {}
    inputs = inputs or {}

    # Validate inputs: naturals only
    for k, v in inputs.items():
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"Input {k} must be a non-negative integer, got {v}")

    vars = dict(inputs)
    vars["y"] = 0

    flat, labels = _resolve_labels(instructions, "")
    stack = [ {"code": flat, "pc": 0, "labels": labels, "map": {}} ]

    """
    Each frame in the stack is composed of the following:
    frame = {
    "code":   [...],   # list of instructions in this frame
    "pc":     int,     # program counter (next instruction index)
    "labels": {...},   # label → instruction index mapping
    "map":    {...},   # variable/label mapping to account for dynamic namespace suffixes
    }
    """

    steps = 0
    while stack and steps < max_steps:
        frame = stack[-1]
        code, pc, mapping = frame["code"], frame["pc"], frame["map"]

        if pc >= len(code):
            stack.pop()  # return from macro / end of program
            continue

        instr = code[pc]
        op, *args = instr

        if trace:
            print(f"step={steps} depth={len(stack)} pc={pc} instr={instr} vars={vars}\n")

        # --- primitives ---
        if op == "inc":
            v = mapping.get(args[0], args[0])  # get mapping if exists, otherwise return arg
            vars[v] = vars.get(v, 0) + 1  # if var value doesn't exist, assume it is 0
            frame["pc"] += 1

        elif op == "dec":
            v = mapping.get(args[0], args[0])
            vars[v] = max(0, vars.get(v, 0) - 1)  # floors to 0
            frame["pc"] += 1

        elif op == "jnz":
            v = mapping.get(args[0], args[0])
            target_raw = args[1]
            target = mapping.get(target_raw, target_raw)
            if vars.get(v, 0) != 0:
                _jump(stack, target)
            else:
                frame["pc"] += 1

        # --- macro call ---
        elif op in macros:
            formal_args, body, *maybe_locals = macros[op]
            locals_list = maybe_locals[0] if maybe_locals else []
            if len(args) != len(formal_args):
                raise ValueError(f"Macro {op} expects {len(formal_args)} args, got {len(args)}")

            # Build per-call mapping: formal_args -> actuals, locals -> suffixed locals
            call_id = next(_call_ids)
            suffix = f"__m{call_id}"
            new_map = {f: mapping.get(a,a) for f, a in zip(formal_args, args)}
            for loc in locals_list:
                new_map[loc] = f"{loc}{suffix}"

            flat_body, body_labels = _resolve_labels(body, suffix)

            # advance caller, push callee
            frame["pc"] += 1
            stack.append({"code": flat_body, "pc": 0, "labels": body_labels, "map": new_map})

        else:
            raise ValueError(f"Unknown instruction {op}")

        steps += 1

    if steps >= max_steps:
        raise RuntimeError("Maximum step count exceeded; possible undefined condition")

    return vars["y"]


# Macros for the S-language interpreter.
# These macros implement common operations like addition, subtraction, and equality checks.
example_macros = {

    # Unconditional jump using local dummy _z
    "goto": (
        ["label",],
        [
            ('inc', '_z'),
            ('jnz', '_z', 'label'),
        ],
        ["_z"]  # locals to suffix at runtime, prefixed with '_' for convention
    ),

    # Macro to set a variable to 0
    # as implemented in EC664 lec 3 
    'zeros': (
        ['y',],
        [
            ('A:',),
            ('dec', 'y'),
            ('jnz', 'y', 'A'),
        ],
    ),

    # equals(y, x): copy x into y without destroying x, using LOCAL _z
    # as implemented in EC664 lec 3 with one exception
    'equals': (
        ['y', 'x'],
        [
            # initializes y to 0 to avoid cross-macro issues
            # this is exception to EC664 lec 3 due to python implementation constraints on namespaces
            ('zeros', 'y'),

            # Checks that x is already 0
            ('A:',),
            ('jnz', 'x', 'B'),
            ('goto', 'C'),

            # Remove from x and add to y and z; z will fill x back up later
            ('B:',),
            ('dec', 'x'),
            ('inc', 'y'),
            ('inc', '_z'),
            ('goto', 'A'),

            # If z is 0, exit macro
            ('C:',),
            ('jnz', '_z', 'D'),
            ('goto', 'E'),

            # Fill x back up from z to avoid destroying x
            ('D:',),
            ('dec', '_z'),
            ('inc', 'x'),
            ('goto', 'C'),

            # E is always the exit label and must be at end
            ('E:',),
        ],
        ['_z'], # locals to suffix at runtime 
    ),


    # Macro to add two numbers x1 and x2, storing result in y
    # as implemented in EC664 lec 3
    'add': (
        ['y', 'x1', 'x2'],
        [
            ('equals', '_y', 'x1'),
            ('equals', '_z', 'x2'),

            ('B:',),
            ('jnz', '_z', 'A'),
            ('goto', 'E'),

            ('A:',),
            ('dec', '_z'),
            ('inc', '_y'),
            ('goto', 'B'),

            ('E:',),
            ('equals', 'y', '_y'),  # copy result back to y
        ],
        ['_z', '_y'],  # locals to suffix at runtime
    ),

    # Macro to subtract x2 from x1, storing result in y
    # as implemented in EC664 lec 3
    # This is a non-standard subtraction that does not handle negative results
    # It will loop up to step count maximum if x2 > x1 and throw an exception
    'subtract': (
        ['y', 'x1', 'x2'], # argument vars
        [
            # introduce dummy z to retain original x2
            ('equals', '_y', 'x1'),
            ('equals', '_z', 'x2'),

            # check exit condition (z == 0)
            ('C:',),
            ('jnz', '_z', 'A'),
            ('goto', 'E'),

            # if y hits 0 (ie x2 > x1), enters infinite loop to avoid returning wrong value
            # we treat infinite loop as an undefined state or exception
            ('A:',),
            ('jnz', '_y', 'B'),
            ('goto', 'A'),

            ('B:',),
            ('dec', '_y'),
            ('dec', '_z'),
            ('goto', 'C'),

            ('E:',),
            ('equals', 'y', '_y'),  # copy result back to y
        ],
        ['_z', '_y'],  
    ),

    # Macro to multiply x1 and x2, storing result in y
    # as implemented in EC664 lec 3
    'mul': (
        ['y', 'x1', 'x2'],
        [
            # initiates dummy var
            ('equals', '_z2', 'x2'),

            # checks for exit condition (z2 == 0)
            ('B:',),
            ('jnz', '_z2', 'A'),
            ('goto', 'E'),

            # add x1 to y for every x2 (with z2 as interim var)
            ('A:',),
            ('dec', '_z2'),
            ('add', '_z1', 'x1', '_y'),
            ('equals', '_y', '_z1'), 
            # not necessary in implementaion, but meets strict rigor per EC664
            ('goto', 'B'),

            ('E:',),
            ('equals', 'y', '_y'),  # copy result back to y
        ],
        ['_z1', '_z2', '_y'], 
    ),

    # Recursive macro to compute factorial of x, storing result in y
    'fact': (
        ['y', 'x'],
        [
            ('zeros', '_y'),
            ('equals', '_z1', 'x'),

            ('A:',),
            ('jnz', '_z1', 'B'),
            ('inc', '_y'),  # base case: fact(0) = 1, so y = 1 
            ('goto', 'E'),

            ('B:',),
            ('dec', '_z1'),
            ('fact', '_z2', '_z1'),  # recursive call
            ('mul', '_y', '_z2', 'x'),  # multiplies result of recursive call by x

            ('E:',),
            ('equals', 'y', '_y'),
        ],
        ['_z1', '_z2', '_y'],
    ),
}

