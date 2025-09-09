import s_programming_language as s


# program: y = x1 + x2
prog = [("add","y","x1","x2")]

vm = s.SMachine(s.example_ece664_macros)
vm.set_inputs({"x1": 2, "x2": 3})
vm.set_program(prog)

# run fully
print(vm.run())            # 5

# inspect history
vm.print_state(-1)         # last state
vm.rewind(0)               # back to initial snapshot
vm.print_state()           # show current (rewound) state

# step-by-step
vm.reset()
while vm.step(trace=True):
    pass
print("y =", vm.vars["y"])

# add one macro
vm.add_macro(
    "zeros",
    ["y"],
    [("L:",), ("dec","y"), ("jnz","y","L")]
)

# add many macros
vm.add_macros({
    "goto": (["label"], [("inc","_z"), ("jnz","_z","label")], ["_z"]),
    "inc2": (["y","x"], [("inc","x"), ("inc","y")])
})

# list / print macros
print(vm.list_macros())
vm.print_macros()
vm.print_macro("goto")

# get programmatic access
params, code, locals_ = vm.get_macro("zeros")

# replace or protect
vm.add_macro("zeros", ["y"], [("dec","y")], overwrite=True)   # replace
# vm.add_macro("zeros", ["y"], [("dec","y")], overwrite=False)  # would raise

# delete
vm.remove_macro("inc2")
vm.remove_macros("goto", "zeros")

