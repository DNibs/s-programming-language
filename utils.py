
from itertools import count
_call_ids = count()

# Call stack holds (instructions, pc, label_map, var_mapping)
# var_mapping: maps formal parameters -> actual variables
def resolve_label_map(code, suffix):
    """Build label map for a block of code with uniquified suffix."""
    label_map = {}
    flat = []
    for instr in code:
        if instr[0].endswith(":"):
            label = instr[0][:-1] + suffix
            label_map[label] = len(flat)
        else:
            flat.append(instr)
    return flat, label_map


def run_program(instructions, inputs=None, macros=None, max_steps=100000):
    """
    Run the S-language interpreter with support for recursive macros.

    Primitive instructions:
      ("inc", var)
      ("dec", var)
      ("jnz", var, "label")
      ("label:",)

    Macros:
      macros = {
          "name": (["param1", "param2", ...], [code], [locals vars])
      }
      Called with ("name", arg1, arg2, ...)
      Supports recursion via runtime call stack.
    """
    macros = macros or {}
    vars = {**inputs} if inputs else {}
    vars["y"] = 0

    # Initial frame
    flat, label_map = resolve_label_map(instructions, "")
    stack = [(flat, 0, label_map, {})]

    steps = 0
    while stack and steps < max_steps:
        instrs, pc, lbls, mapping = stack[-1]

        if pc >= len(instrs):
            stack.pop()  # return from macro or end of program
            continue

        op, *args = instrs[pc]

        # --- Primitive instructions ---
        if op == "inc":
            v = mapping.get(args[0], args[0])
            vars[v] = vars.get(v, 0) + 1
            stack[-1] = (instrs, pc + 1, lbls, mapping)

        elif op == "dec":
            v = mapping.get(args[0], args[0])
            vars[v] = max(0, vars.get(v, 0) - 1)
            stack[-1] = (instrs, pc + 1, lbls, mapping)

        elif op == "jnz":
            v = mapping.get(args[0], args[0])
            raw_target = args[1]

            # Map formal label params (e.g., in ("goto", "E"))
            target = mapping.get(raw_target, raw_target)

            if vars.get(v, 0) != 0:
                # 1) Exact hit in current frame
                if target in lbls:
                    stack[-1] = (instrs, lbls[target], lbls, mapping)
                    steps += 1
                    continue

                # 2) Local label without suffix: try to find its suffixed variant
                #    e.g., "A" -> "A__m7" in this frame
                suffixed = next((k for k in lbls.keys() if k.startswith(target + "__")), None)
                if suffixed is not None:
                    stack[-1] = (instrs, lbls[suffixed], lbls, mapping)
                    steps += 1
                    continue

                # 3) Outer-frame labels (for macros like goto that jump to caller labels)
                for i in range(len(stack) - 2, -1, -1):
                    instrs_i, pc_i, lbls_i, mapping_i = stack[i]
                    # try exact
                    if target in lbls_i:
                        stack = stack[:i + 1]
                        stack[-1] = (instrs_i, lbls_i[target], lbls_i, mapping_i)
                        steps += 1
                        break
                    # try suffixed match in that frame
                    suffixed_i = next((k for k in lbls_i.keys() if k.startswith(target + "__")), None)
                    if suffixed_i is not None:
                        stack = stack[:i + 1]
                        stack[-1] = (instrs_i, lbls_i[suffixed_i], lbls_i, mapping_i)
                        steps += 1
                        break
                else:
                    raise KeyError(f"Label '{target}' not found in any frame")
            else:
                stack[-1] = (instrs, pc + 1, lbls, mapping)


        # --- Macro call ---
        elif op in macros:
            formals, code, *maybe_locals = macros[op]
            locals_list = maybe_locals[0] if maybe_locals else []

            if len(args) != len(formals):
                raise ValueError(f"Macro {op} expects {len(formals)} args, got {len(args)}")

            # Build mapping for this call: formals -> actuals, locals -> suffixed locals
            call_id = next(_call_ids)
            suffix = f"__m{call_id}"

            new_mapping = {f: mapping.get(a, a) for f, a in zip(formals, args)}
            for loc in locals_list:
                new_mapping[loc] = f"{loc}{suffix}"

            # Labels inside the macro body get suffixed by resolve_label_map
            flat_code, label_map2 = resolve_label_map(code, suffix)

            # advance caller pc and push callee frame
            stack[-1] = (instrs, pc + 1, lbls, mapping)
            stack.append((flat_code, 0, label_map2, new_mapping))

        else:
            raise ValueError(f"Unknown instruction {op}")

        steps += 1

    return vars["y"]

macros = {
    # Unconditional jump using local dummy _z
    "goto": (
        ["label",],
        [
            ('inc', '_z'),
            ('jnz', '_z', 'label'),
        ],
        ["_z"]  # locals to suffix at runtime 
    ),

    # equals(y, x): copy x into y without destroying x, using LOCAL _z
    'equals': (
        ['y', 'x'],
        [
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
        ['_z'] # locals to suffix at runtime 
    ),

    'zeros': (
        ['y',],
        [
            ('A:',),
            ('dec', 'y'),
            ('jnz', 'y', 'A'),
        ]
    )
}
