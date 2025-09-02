# S Language Simulator

Author: David Niblick  
Start Date: 2 September 2025  
Course: ECE 66400 (Computability, Complexity, and Languages) — Purdue University  
Instructor: Professor Avi Kak  

---

## Overview

This repository contains a Python interpreter for the minimalist programming language **S**, introduced in ECE66400.  
Language S is defined with only three primitive instructions and operates over the domain of natural numbers.

The three instructions:

1. `variable = variable + 1`  
2. `variable = variable - 1`  (floored at 0)  
3. `if variable != 0 goto L`  

All computations operate over non-negative integers.  
The distinguished output variable is **`y`**, which always starts at 0.  
Programs can take multiple inputs (`x1`, `x2`, etc)

Additional internal variables (`z`, `z1`, etc.) are created on demand and initialized to 0.  

---

## Features

- **Core S semantics**: faithful execution of the three instructions.  
- **Labels**: user-defined symbolic labels for human-readable control flow.  
- **Macros**: higher-level constructs built entirely from the three primitives.  
  - Parameterized macros allow code reuse (e.g., `("add", "y", "x1", "x2")`).  
  - Macros are expanded before execution into flat S instructions with uniquified labels.  
  - Keeps the theoretical purity of S while simplifying program design.  
- **Safety**: configurable step limit prevents infinite loops.  

---

## Example Usage

### Program: Addition

Define a macro to compute `dst = a + b`:

```py
