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
  Must declare the local variables used in macros. See example macros. 

- **Y use in Macros**  
  To avoid global variable problems, macros treat _y as a local variable and copy to result y at end.  

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

print(s.run_program(program, {'x1': 7, 'x2': 3}, s.example_macros))  # → 10
```

---

## Example 2: Writing a Macro

Implements the same program aboe but as a macro for nested reuse.

```python
# Macro to implement program above

{('add': (
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
)}
```

When called as '("add", "y", "x1", "x2")', it expands into instructions where labels '(A, B, C, D, E)' and the locals ('_z', '_y') are automatically suffixed (e.g. 'A__m5', '_z__m5') to avoid collisions.

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
