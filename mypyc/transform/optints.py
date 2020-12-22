
from mypyc.analysis.dataflow import (
    get_cfg,
    cleanup_cfg,
    analyze_integer_ranges
)
from mypyc.ir.func_ir import FuncIR
from mypyc.ir.ops import Register


def optimize_integer_types(ir: FuncIR) -> None:
    # Remove dead blocks from the CFG, which helps avoid spurious
    # checks due to unused error handling blocks.
    cleanup_cfg(ir.blocks)

    cfg = get_cfg(ir.blocks)

    for i, block in enumerate(ir.blocks):
        block.label = i

    int_ranges = analyze_integer_ranges(ir.blocks,
                                        cfg,
                                        filter(lambda r: isinstance(r, Register), ir.env.regs()))

    print(ir.decl.name)
    print(dict((r, dict((reg.name, v)
        for (reg, v) in m.items()))
            for (r, m) in int_ranges.items()))
