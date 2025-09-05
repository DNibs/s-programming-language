# s_programming_language.py
# Author: David Niblick
# Date: 20250903

from itertools import count
from copy import deepcopy

class SMachine:
    """
    S-language VM with recursive, parameterized macros and per-call namespaces.
    Supports step-by-step execution, full state history, and program/macros editing.
    """

    # ---------- construction ----------

    def __init__(self, macros=None):
        self.macros = {}               # name -> (params, code, locals[])
        if macros:
            for k, v in macros.items():
                self.add_macro(k, *v)

        self.inputs = {}
        self.program_src = []          # raw program with labels
        self.program_flat = []         # flattened program (no labels)
        self.program_labels = {}       # label -> index in program_flat
        self.vars = {}                 # global variable store
        self.stack = []                # call stack of frames (dicts)
        self._call_ids = count()       # unique suffix ids
        self.step_count = 0
        self.history = []              # list of snapshots

    # ---------- user API: editing ----------

    def set_inputs(self, inputs: dict | None):
        self.inputs = inputs or {}

    def set_program(self, instructions: list[tuple]):
        self.program_src = list(instructions)

    def add_instruction(self, instr: tuple):
        self.program_src.append(instr)


    # ---------- macros API ----------

    def list_macros(self) -> list[str]:
        """Return macro names sorted."""
        return sorted(self.macros.keys())

    def get_macro(self, name: str):
        """Return (params, code, locals) or raise KeyError."""
        if name not in self.macros:
            raise KeyError(f"Unknown macro '{name}'")
        params, code, locals_ = self.macros[name]
        return list(params), list(code), list(locals_)

    def add_macro(self, name: str, params: list, code: list, locals_: list | None = None, overwrite: bool = True):
        """
        Add or replace a macro.
        - params: list of formal parameter names
        - code: list of instruction tuples
        - locals_: list of local names (optional)
        - overwrite=False will error if the macro exists
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Macro name must be a non-empty string")
        if not isinstance(params, list) or not all(isinstance(p, str) for p in params):
            raise ValueError("params must be a list[str]")
        if not isinstance(code, list) or not all(isinstance(t, tuple) and t for t in code):
            raise ValueError("code must be a list[non-empty tuple]")
        if locals_ is None:
            locals_ = []
        if not isinstance(locals_, list) or not all(isinstance(z, str) for z in locals_):
            raise ValueError("locals must be a list[str]")

        if not overwrite and name in self.macros:
            raise ValueError(f"Macro '{name}' already exists")
        self.macros[name] = (list(params), list(code), list(locals_))

    def add_macros(self, macro_dict: dict, overwrite: bool = True):
        """Batch add macros from {name: (params, code, [locals])}."""
        if not isinstance(macro_dict, dict):
            raise ValueError("macro_dict must be a dict")
        for k, v in macro_dict.items():
            if not (isinstance(v, tuple) and 2 <= len(v) <= 3):
                raise ValueError(f"Bad macro spec for '{k}'")
            params, code = v[0], v[1]
            locals_ = v[2] if len(v) == 3 else []
            self.add_macro(k, params, code, locals_, overwrite=overwrite)

    def remove_macro(self, name: str):
        """Delete a macro. No error if absent."""
        self.macros.pop(name, None)

    def remove_macros(self, *names: str):
        """Batch delete macros."""
        for n in names:
            self.macros.pop(n, None)

    def print_macros(self):
        """Print all macro names and arities."""
        for name in self.list_macros():
            params, _, locals_ = self.macros[name]
            print(f"{name}({', '.join(params)})  locals=[{', '.join(locals_)}]")

    def print_macro(self, name: str):
        """Pretty-print a single macro."""
        params, code, locals_ = self.get_macro(name)
        print(f"macro {name}({', '.join(params)})  locals=[{', '.join(locals_)}]")
        for instr in code:
            if instr[0].endswith(":"):
                print(f"  {instr[0]}")
            else:
                print(f"  {instr}")

    # ---------- execution control ----------

    def reset(self):
        self._validate_inputs()
        self.vars = dict(self.inputs)
        self.vars.setdefault("y", 0)
        self.program_flat, self.program_labels = self._resolve_labels(self.program_src, "")
        self.stack = [self._make_frame(self.program_flat, self.program_labels, {})]
        self.step_count = 0
        self.history = []
        # capture initial state
        self._save_snapshot(current_instr=self._peek_next_instr())

    def run(self, max_steps=100_000, print_steps=None, trace=False):
        if not self.stack:
            self.reset()
        while self.stack and self.step_count < max_steps:
            if (print_steps and self.step_count > 0) and (self.step_count % print_steps == 0):
                print(f'Executing step {self.step_count}')
            self.step(trace=trace)
        if self.step_count >= max_steps:
            raise RuntimeError("Maximum step count exceeded; possible undefined condition")
        return self.vars.get("y", 0)

    def step(self, trace=False):
        """Execute exactly one instruction (or return from a frame). Saves state."""
        if not self.stack:
            return False  # halted

        frame = self.stack[-1]
        code, pc, mapping = frame["code"], frame["pc"], frame["map"]

        # finished frame → pop and save state
        if pc >= len(code):
            self.stack.pop()
            self._save_snapshot(current_instr=self._peek_next_instr())
            return bool(self.stack)

        instr = code[pc]
        op, *args = instr

        if trace:
            print(f"step={self.step_count} depth={len(self.stack)} pc={pc} instr={instr} vars={self.vars}")

        # primitives
        if op == "inc":
            v = mapping.get(args[0], args[0])
            self.vars[v] = self.vars.get(v, 0) + 1
            frame["pc"] += 1

        elif op == "dec":
            v = mapping.get(args[0], args[0])
            self.vars[v] = max(0, self.vars.get(v, 0) - 1)
            frame["pc"] += 1

        elif op == "jnz":
            v = mapping.get(args[0], args[0])
            target_raw = args[1]
            target = mapping.get(target_raw, target_raw)
            if self.vars.get(v, 0) != 0:
                self._jump(target)
            else:
                frame["pc"] += 1

        # macro call
        elif op in self.macros:
            params, body, locals_list = self.macros[op]
            if len(args) != len(params):
                raise ValueError(f"Macro {op} expects {len(params)} args, got {len(args)}")
            call_id = next(self._call_ids)
            suffix = f"__m{call_id}"
            new_map = {p: mapping.get(a, a) for p, a in zip(params, args)}
            for loc in locals_list:
                new_map[loc] = f"{loc}{suffix}"
            flat_body, body_labels = self._resolve_labels(body, suffix)
            frame["pc"] += 1
            self.stack.append(self._make_frame(flat_body, body_labels, new_map))

        else:
            raise ValueError(f"Unknown instruction {op}")

        self.step_count += 1
        self._save_snapshot(current_instr=self._peek_next_instr())
        return True

    # ---------- inspection, history, rewind ----------

    def state(self):
        """Return current state (shallow copy for quick inspection)."""
        return {
            "step": self.step_count,
            "vars": dict(self.vars),
            "stack_depth": len(self.stack),
            "next_instr": self._peek_next_instr(),
            "top_frame": deepcopy(self.stack[-1]) if self.stack else None,
        }

    def print_state(self, idx: int | None = None):
        s = self.history[idx] if idx is not None else self.state()
        print(f"step={s['step']} depth={s.get('stack_depth', 0)} next={s.get('next_instr')}")
        print("vars:", {k: v for k, v in sorted(s["vars"].items())})

    def rewind(self, idx: int):
        """Restore machine to a previous snapshot index."""
        snap = self.history[idx]
        # deep restore to avoid aliasing
        self.vars = deepcopy(snap["vars"])
        self.stack = deepcopy(snap["stack"])
        self.step_count = snap["step"]
        # keep program/macros as-is


    # ---------- internals ----------

    @staticmethod
    def _make_frame(code, labels, mapping):
        return {"code": list(code), "pc": 0, "labels": dict(labels), "map": dict(mapping)}

    @staticmethod
    def _resolve_labels(code, suffix):
        labels, flat = {}, []
        for instr in code:
            op = instr[0]
            if op.endswith(":"):
                labels[op[:-1] + suffix] = len(flat)
            else:
                flat.append(instr)
        return flat, labels

    def _find_label_in_frame(self, label, frame):
        lbls = frame["labels"]
        if label in lbls:
            return lbls[label]
        for k in lbls:
            if k.startswith(label + "__"):
                return lbls[k]
        return None

    def _jump(self, target):
        # current frame
        idx = self._find_label_in_frame(target, self.stack[-1])
        if idx is not None:
            self.stack[-1]["pc"] = idx
            return
        # outward search
        for d in range(len(self.stack) - 2, -1, -1):
            idx = self._find_label_in_frame(target, self.stack[d])
            if idx is not None:
                del self.stack[d + 1 :]
                self.stack[-1]["pc"] = idx
                return
        raise KeyError(f"Label '{target}' not found in any frame")

    def _peek_next_instr(self):
        if not self.stack:
            return None
        fr = self.stack[-1]
        if fr["pc"] >= len(fr["code"]):
            return None
        return fr["code"][fr["pc"]]

    def _save_snapshot(self, current_instr):
        # deep snapshot so history is immutable
        self.history.append({
            "step": self.step_count,
            "vars": deepcopy(self.vars),
            "stack": deepcopy(self.stack),
            "stack_depth": len(self.stack),
            "next_instr": deepcopy(current_instr),
        })

    def _validate_inputs(self):
        for k, v in (self.inputs or {}).items():
            if not isinstance(v, int) or v < 0:
                raise ValueError(f"Input {k} must be a non-negative integer, got {v}")


# Macros for the S-language interpreter.
# These macros implement common operations like addition, subtraction, and equality checks.
example_ece664_macros = {

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
}

recursive_macros = {
    'recurse_add':(
        ['y', 'x1', 'x2'],
        [
            # transfer to locals
            ('equals', '_x1', 'x1'),
            ('equals', '_x2', 'x2'),

            ('equals', '_y', '_x1'),
            ('recurse_add_core', '_y', '_x2'),

            # transfer result
            ('equals', 'y', '_y'),
        ],
        ['_x1', '_x2', '_y'],
    ),
    'recurse_add_core':(
        ['y', 'x'],
        [
            # since wrapper alreayd transfered to locals, not needed here
            ('A:',),
            ('jnz', 'x', 'B'),
            ('goto', 'E'),

            ('B:',),
            ('inc', 'y'),
            ('dec', 'x'),
            ('recurse_add_core', 'y', 'x'),

            ('E:',),  
        ],
        [],
    ),

    'recurse_mul':(
        ['y', 'x1', 'x2'],
        [
            # transfer to locals
            ('equals', '_x', 'x1'),
            ('equals', '_k', 'x2'),

            ('recurse_mul_core', '_y', '_x', '_k'),

            # transfer result
            ('equals', 'y', '_y'),
        ],
        ['_x', '_k', '_y'],
    ),

    'recurse_mul_core':(
        ['y', 'x', 'k'],
        [
            # since wrapper alreayd transfered to locals, not needed here
            ('A:',),
            ('jnz', 'k', 'B'),
            ('goto', 'E'),

            ('B:',),
            ('recurse_add', 'y', 'x', 'y'), # recurse all the way through, baby!
            ('dec', 'k'),
            ('recurse_mul_core', 'y', 'x', 'k'),

            ('E:',),  

        ],
        [],

    ),
    
    'recurse_factorial':(
        ['y', 'x'],
        [
            # transfer to locals
            ('equals', '_x', 'x'),
            ('inc', '_y'),  # base case y=1 when x=0
            ('jnz', '_x', 'A'), # handles when x=0
            ('goto', 'E'),

            ('A:',),
            ('recurse_factorial_core', '_y', '_x'),

            ('E:',),
            ('equals', 'y', '_y'),
        ],
        [],
    ),

    'recurse_factorial_core':(
        ['y', 'x'],
        [

            ('A:',),
            ('mul', 'y', 'y', 'x'),
            ('dec', 'x'),
            ('jnz', 'x', 'A'),

            ('E:',),
        ],
        [],
    )
}

