# S Language Simulator

Author: David Niblick  

Start Date: 2 September 2025  

Course: ECE 66400 (Computability, Complexity, and Languages) Fall 2025

Link: https://engineering.purdue.edu/kak/ComputabilityComplexityLanguages/

Instructor: Professor Avinash Kak 

Purdue University, Robotic Vision Lab

---

## Overview

This repository contains a Python interpreter for the minimalist programming language **S**, introduced in ECE66400.  
Language S is defined with only three primitive instructions:

1. `variable = variable + 1`  
2. `variable = variable - 1` (floored at 0)  
3. `if variable != 0 goto L` 

All computations operate over natural numbers (no negatives).  
The output variable **`y`** always starts at 0.  
Programs may take multiple input variables (`x1`, `x2`, …).  
Additional temporary variables are created on demand and start at 0.  
Macros may be defined for convenient code reuse.
Labels may be definied for convenient control.

Note that this is only for educational purposes and likely not useful for real-world applications.

---

## Features

- **Faithful S semantics**  
  Executes only the three primitive operations over natural numbers.  

- **Labels**  
  Programs use symbolic labels for control flow. Each macro invocation dynamically generates unique suffixes (`__m0`, `__m1`, …) for its labels, so recursion and repeated calls are safe.  

- **Macros**  
  Higher-level abstractions built entirely from the three primitives.  
  - **Parameterized**: pass variables and labels as arguments.  
  - **Locals**: declare local variables to be renamed with a unique suffix at runtime, giving each macro call its own namespace. Uses convention of a prefix underscore (e.g. `_z`)  
  - **Recursive**: macros may call themselves (direct or mutual recursion).  

- **Safety**  
  Step limit prevents runaway infinite loops.  

---

## Differences from ECE664

- **Declare Local Variables in Macros**  
  Currently, local variables must be declared instead of assuming all inputs are copied to local variables. While future work might automate this global->local transition upon macro calls (as lsn 4 dictates), for now must be manually done within custom macros 

- **Y use in Macros**  
  In addition to above, user should also declare a local 'y' macro (usually '_y' in examples) and copy to result y at end. Alternate approach is to zero y at the beginning of each macro. Otherwise, namespace collisions will cause drift to results.  

- **Macro Exit**  
  Need to deliberately add [E] at end of macro. This is a convenient place to copy _y to result.

- **Macro Expansion**  
  Local variable name expansion is currently handled differently than as explained in ECE664 Lec4. However, namespace collision is still avoided.

---


## Example 1: Simple Program

A program to add `x1` and `x2` into `y` using two `equals` macro calls and a loop to labeled instructions:

```python
import s_programming_language as s

# Program to add two numbers x1 and x2, storing result in y
# as implemented in EC664 lec 3
program = [
    ('equals', 'y', 'x1'),   # macro for y <- x1
    ('equals', 'z', 'x2'),   # macro for z <- x2

    ('B:',),
    ('jnz', 'z', 'A'),
    ('goto', 'E'),  # macro for (inc _z), (jnz _z 'E') 

    ('A:',),
    ('dec', 'z'),
    ('inc', 'y'),
    ('goto', 'B'),

    ('E:',),
]


vm = s.SMachine(s.example_macros)
vm.set_inputs({"x1": 2, "x2": 3})
vm.set_program(program)

# run fully
print(vm.run())            # 5

```

---

## Example 2: Writing a Macro

Implements the same program aboe but as a macro for nested reuse.

```python
# Macro to implement program above

new_macros = {'add': (
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
        ('equals', 'y', '_y'),  # copy result back to y, avoids namespace collisions
    ],
    ['_z', '_y'],  # locals to suffix at runtime
),
}

vm.add_macros(new_macros)
```

When called as '("add", "y", "x1", "x2")', it expands into instructions where labels '(A, B, C, D, E)' and the locals ('_z', '_y') are automatically suffixed (e.g. 'A__m5', '_z__m5') to avoid collisions.

---


## Example 3: Inspect State

View internal working of S as it iterates through a program.

```python
# inspect history
vm.print_state(-1)         # last state
vm.rewind(0)               # back to initial snapshot
vm.print_state()           # show current (rewound) state

# step-by-step
vm.reset()
while vm.step(trace=True):
    pass
print("y =", vm.vars["y"])

```

---


## Theoretical Context

Despite its spartan instruction set, **S** can express arbitrary computations and is **Turing-complete**.
This project illustrates how higher-level constructs (macros, loops, recursion) can be built purely from three primitive instructions, preserving theoretical elegance while enabling practical experimentation.

---

## License

Educational use only. Author retains rights.

---

## Use of Gen AI

ChatGPT was used during the development of this code.
