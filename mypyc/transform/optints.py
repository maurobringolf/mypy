import functools

from mypyc.analysis.dataflow import (
    get_cfg,
    cleanup_cfg,
    analyze_integer_ranges,
    allTop,
    joinLocalAbstractStates,
)
from mypyc.ir.func_ir import FuncIR


# TODO clean this up
from mypyc.ir.ops import *
from mypyc.ir.rtypes import (
    int32_rprimitive,
    int64_rprimitive,
)


def optimize_integer_types(ir: FuncIR) -> None:
    # Remove dead blocks from the CFG, which helps avoid spurious
    # checks due to unused error handling blocks.
    cleanup_cfg(ir.blocks)

    cfg = get_cfg(ir.blocks)

    for i, block in enumerate(ir.blocks):
        block.label = i
    to_analyze = ir.env.regs() #filter(lambda r: r.type == int_rprimitive, ir.env.regs())


    local_ranges = analyze_integer_ranges(ir.blocks,
                                          cfg,
                                          to_analyze)

    # Join ranges over all blocks
    total_ranges = functools.reduce(joinLocalAbstractStates, [local_ranges[b.label]
        for b in ir.blocks], allTop(to_analyze))

    print(total_ranges)

    new64regs = [reg for reg, (lo, hi) in total_ranges.items() if fits_int64(lo, hi)]

    refineIntTypes = RefineTypeVisitor(new64regs, int64_rprimitive)
    for b in ir.blocks:
        for op in b.ops:
            op.accept(refineIntTypes)
    for reg in new64regs:
        print(reg)

        # Re-type the register in the function environment
        reg.type = int64_rprimitive


def fits_int64(lo: float, hi: float) -> bool:
    return lo >= - (2**64) and hi <= 2**64 - 1


class RefineTypeVisitor(OpVisitor[None]):

    def __init__(self, regs: List[Register], toType: RType):
        self.regs = regs
        self.toType = toType
        super(RefineTypeVisitor, self)

    def visit_goto(self, op: Goto) -> None:
        pass

    def visit_branch(self, op: Branch) -> None:
        pass

    def visit_return(self, op: Return) -> None:
        pass

    def visit_unreachable(self, op: Unreachable) -> None:
        pass # TODO

    def visit_assign(self, op: Assign) -> None:
        pass # TODO

    def visit_load_int(self, op: LoadInt) -> None:
        pass

    def visit_load_error_value(self, op: LoadErrorValue) -> None:
        pass # TODO

    def visit_get_attr(self, op: GetAttr) -> None:
        pass # TODO

    def visit_set_attr(self, op: SetAttr) -> None:
        pass # TODO

    def visit_load_static(self, op: LoadStatic) -> None:
        # TODO
        pass

    def visit_init_static(self, op: InitStatic) -> None:
        # TODO
        pass

    def visit_tuple_get(self, op: TupleGet) -> None:
        # TODO
        pass

    def visit_tuple_set(self, op: TupleSet) -> None:
        # TODO
        pass

    def visit_inc_ref(self, op: IncRef) -> None:
        # TODO
        pass

    def visit_dec_ref(self, op: DecRef) -> None:
        # TODO need to remove this as int is no longer an object?
        pass

    def visit_call(self, op: Call) -> None:
        # TODO
        pass

    def visit_method_call(self, op: MethodCall) -> None:
        # TODO
        pass

    def visit_cast(self, op: Cast) -> None:
        # TODO
        pass

    def visit_box(self, op: Box) -> None:
        # TODO
        pass

    def visit_unbox(self, op: Unbox) -> None:
        # TODO
        pass

    def visit_raise_standard_error(self, op: RaiseStandardError) -> None:
        # TODO
        pass

    def visit_call_c(self, op: CallC) -> None:
        pass # TODO

    def visit_truncate(self, op: Truncate) -> None:
        # TODO
        pass

    def visit_load_global(self, op: LoadGlobal) -> None:
        # TODO
        pass

    def visit_binary_int_op(self, op: BinaryIntOp) -> None:
        # TODO
        pass

    def visit_comparison_op(self, op: ComparisonOp) -> None:
        # TODO
        pass

    def visit_load_mem(self, op: LoadMem) -> None:
        # TODO
        pass

    def visit_set_mem(self, op: SetMem) -> None:
        # TODO
        pass

    def visit_get_element_ptr(self, op: GetElementPtr) -> None:
        # TODO
        pass

    def visit_load_address(self, op: LoadAddress) -> None:
        # TODO
        pass
