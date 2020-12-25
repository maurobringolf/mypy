import functools

from typing import (
    Optional,
    List,
)

from mypyc.analysis.dataflow import (
    get_cfg,
    cleanup_cfg,
    analyze_integer_ranges,
    joinLocalAbstractStates,
)
from mypyc.ir.func_ir import FuncIR


# TODO clean this up
from mypyc.ir.ops import (
    OpVisitor,
    Goto,
    Branch,
    Return,
    Unreachable,
    Assign,
    LoadInt,
    LoadErrorValue,
    GetAttr,
    SetAttr,
    LoadStatic,
    InitStatic,
    TupleSet,
    TupleGet,
    IncRef,
    DecRef,
    Call,
    MethodCall,
    Cast,
    Box,
    Unbox,
    RaiseStandardError,
    CallC,
    Truncate,
    LoadGlobal,
    BinaryIntOp,
    ComparisonOp,
    LoadMem,
    SetMem,
    GetElementPtr,
    LoadAddress,
    Register,
    Op,
)
from mypyc.ir.rtypes import (
    RType,
    int32_rprimitive,
)


def optimize_integer_types(ir: FuncIR) -> None:
    # Remove dead blocks from the CFG, which helps avoid spurious
    # checks due to unused error handling blocks.
    cleanup_cfg(ir.blocks)

    cfg = get_cfg(ir.blocks)

    for i, block in enumerate(ir.blocks):
        block.label = i

    initial_tops = ir.args

    local_ranges = analyze_integer_ranges(ir.blocks,
                                          cfg,
                                          initial_tops)

    # Join ranges over all blocks
    total_ranges = functools.reduce(joinLocalAbstractStates, [local_ranges[b.label]
        for b in ir.blocks])
    new32regs = [reg for reg, (lo, hi) in total_ranges.items() if fits_int32(lo, hi)]

    refineIntTypes = RefineTypeVisitor(new32regs, int32_rprimitive)
    for i, b in enumerate(ir.blocks):
        for ii, op in enumerate(b.ops):
            opp = op.accept(refineIntTypes)

            # These ops can be deleted
            if False:
                b.ops = b.ops[0:ii] + b.ops[ii+1:]

            # These ops need replacement
            if isinstance(op, CallC):
                # Replace in block
                ir.blocks[i].ops[ii] = opp

                # Replace in the function environment
                ir.env.indexes[opp] = ir.env.indexes[op]
                del ir.env.indexes[op]

                # Replace references other ops in same basicblock
                replaceVisitor = ReplaceVisitor(op, opp)
                for oppp in b.ops[i+1:]:
                    oppp.accept(replaceVisitor)

    for reg in new32regs:
        # Re-type the register in the function environment
        reg.type = int32_rprimitive


def fits_int32(lo: float, hi: float) -> bool:
    return lo >= - (2**32) and hi <= 2**32 - 1


class RefineTypeVisitor(OpVisitor[Optional[Op]]):

    def __init__(self, regs: List[Register], toType: RType):
        self.regs = regs
        self.toType = toType
        super(RefineTypeVisitor, self)

    def visit_goto(self, op: Goto) -> Optional[Op]:
        pass

    def visit_branch(self, op: Branch) -> Optional[Op]:
        pass

    def visit_return(self, op: Return) -> Optional[Op]:
        pass

    def visit_unreachable(self, op: Unreachable) -> Optional[Op]:
        # TODO
        pass

    def visit_assign(self, op: Assign) -> Optional[Op]:
        # TODO
        pass

    def visit_load_int(self, op: LoadInt) -> Optional[Op]:
        if op in self.regs:
            op.value = op.value >> 1

    def visit_load_error_value(self, op: LoadErrorValue) -> Optional[Op]:
        # TODO
        pass

    def visit_get_attr(self, op: GetAttr) -> Optional[Op]:
        # TODO
        pass

    def visit_set_attr(self, op: SetAttr) -> Optional[Op]:
        # TODO
        pass

    def visit_load_static(self, op: LoadStatic) -> Optional[Op]:
        # TODO
        pass

    def visit_init_static(self, op: InitStatic) -> Optional[Op]:
        # TODO
        pass

    def visit_tuple_get(self, op: TupleGet) -> Optional[Op]:
        # TODO
        pass

    def visit_tuple_set(self, op: TupleSet) -> Optional[Op]:
        # TODO
        pass

    def visit_inc_ref(self, op: IncRef) -> Optional[Op]:
        # TODO
        pass

    def visit_dec_ref(self, op: DecRef) -> Optional[Op]:
        # TODO need to remove this as int is no longer an object?
        pass

    def visit_call(self, op: Call) -> Optional[Op]:
        # TODO
        pass

    def visit_method_call(self, op: MethodCall) -> Optional[Op]:
        # TODO
        pass

    def visit_cast(self, op: Cast) -> Optional[Op]:
        # TODO
        pass

    def visit_box(self, op: Box) -> Optional[Op]:
        # TODO
        pass

    def visit_unbox(self, op: Unbox) -> Optional[Op]:
        # TODO
        pass

    def visit_raise_standard_error(self, op: RaiseStandardError) -> Optional[Op]:
        # TODO
        pass

    def visit_call_c(self, op: CallC) -> Optional[Op]:
        if op.function_name == 'CPyTagged_Add':
            return BinaryIntOp(self.toType, op.args[0], op.args[1], BinaryIntOp.ADD)
        else:
            return Op

    def visit_truncate(self, op: Truncate) -> Optional[Op]:
        # TODO
        pass

    def visit_load_global(self, op: LoadGlobal) -> Optional[Op]:
        # TODO
        pass

    def visit_binary_int_op(self, op: BinaryIntOp) -> Optional[Op]:
        # TODO
        pass

    def visit_comparison_op(self, op: ComparisonOp) -> Optional[Op]:
        # TODO
        pass

    def visit_load_mem(self, op: LoadMem) -> Optional[Op]:
        # TODO
        pass

    def visit_set_mem(self, op: SetMem) -> Optional[Op]:
        # TODO
        pass

    def visit_get_element_ptr(self, op: GetElementPtr) -> Optional[Op]:
        # TODO
        pass

    def visit_load_address(self, op: LoadAddress) -> Optional[Op]:
        # TODO
        pass


class ReplaceVisitor(OpVisitor[None]):

    def __init__(self, toReplace: Op, replaceWith: Op):
        self.toReplace = toReplace
        self.replaceWith = replaceWith
        super(ReplaceVisitor, self)

    def visit_goto(self, op: Goto) -> Optional[Op]:
        # TODO
        pass

    def visit_branch(self, op: Branch) -> Optional[Op]:
        # TODO
        pass

    def visit_return(self, op: Return) -> Optional[Op]:
        # TODO
        pass

    def visit_unreachable(self, op: Unreachable) -> Optional[Op]:
        # TODO
        pass

    def visit_assign(self, op: Assign) -> Optional[Op]:
        if op.src == self.toReplace:
            op.src = self.replaceWith

    def visit_load_int(self, op: LoadInt) -> Optional[Op]:
        # TODO
        pass

    def visit_load_error_value(self, op: LoadErrorValue) -> Optional[Op]:
        # TODO
        pass

    def visit_get_attr(self, op: GetAttr) -> Optional[Op]:
        # TODO
        pass

    def visit_set_attr(self, op: SetAttr) -> Optional[Op]:
        # TODO
        pass

    def visit_load_static(self, op: LoadStatic) -> Optional[Op]:
        # TODO
        pass

    def visit_init_static(self, op: InitStatic) -> Optional[Op]:
        # TODO
        pass

    def visit_tuple_get(self, op: TupleGet) -> Optional[Op]:
        # TODO
        pass

    def visit_tuple_set(self, op: TupleSet) -> Optional[Op]:
        # TODO
        pass

    def visit_inc_ref(self, op: IncRef) -> Optional[Op]:
        # TODO
        pass

    def visit_dec_ref(self, op: DecRef) -> Optional[Op]:
        # TODO need to remove this as int is no longer an object?
        pass

    def visit_call(self, op: Call) -> Optional[Op]:
        # TODO
        pass

    def visit_method_call(self, op: MethodCall) -> Optional[Op]:
        # TODO
        pass

    def visit_cast(self, op: Cast) -> Optional[Op]:
        # TODO
        pass

    def visit_box(self, op: Box) -> Optional[Op]:
        # TODO
        pass

    def visit_unbox(self, op: Unbox) -> Optional[Op]:
        # TODO
        pass

    def visit_raise_standard_error(self, op: RaiseStandardError) -> Optional[Op]:
        # TODO
        pass

    def visit_call_c(self, op: CallC) -> Optional[Op]:
        # TODO
        pass

    def visit_truncate(self, op: Truncate) -> Optional[Op]:
        # TODO
        pass

    def visit_load_global(self, op: LoadGlobal) -> Optional[Op]:
        # TODO
        pass

    def visit_binary_int_op(self, op: BinaryIntOp) -> Optional[Op]:
        # TODO
        pass

    def visit_comparison_op(self, op: ComparisonOp) -> Optional[Op]:
        # TODO
        pass

    def visit_load_mem(self, op: LoadMem) -> Optional[Op]:
        # TODO
        pass

    def visit_set_mem(self, op: SetMem) -> Optional[Op]:
        # TODO
        pass

    def visit_get_element_ptr(self, op: GetElementPtr) -> Optional[Op]:
        # TODO
        pass

    def visit_load_address(self, op: LoadAddress) -> Optional[Op]:
        # TODO
        pass
