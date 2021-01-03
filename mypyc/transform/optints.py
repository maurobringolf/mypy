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

    """
    for reg in new32regs:
        # Re-type the register in the function environment
        reg.type = int32_rprimitive
    """

    refineIntTypes = RefineTypeVisitor(new32regs, int32_rprimitive)

    for b in ir.blocks:
        for i, op in enumerate(b.ops):
            replaceOps = op.accept(refineIntTypes)

            # These ops need replacement
            if replaceOps is not None:
                # Replace in block
                b.ops = b.ops[0:i] + replaceOps + b.ops[i+1:]

                # Last op of replaceOps is assumed to be replacement of original
                replaceOpResult = replaceOps[-1]

                # Replace result in the function environment if present
                if op in ir.env.indexes:
                    ir.env.indexes[replaceOpResult] = ir.env.indexes[op]
                    del ir.env.indexes[op]

                # Add all new ops to the function environment
                for newOp in replaceOps[0:-1]:
                    ir.env.add(newOp)

                # Replace references other ops in same basicblock
                replaceVisitor = ReplaceVisitor(op, replaceOpResult)
                for oppp in b.ops[i+1:]:
                    oppp.accept(replaceVisitor)


def fits_int32(lo: float, hi: float) -> bool:
    return lo >= - (2**32) and hi <= 2**32 - 1


class RefineTypeVisitor(OpVisitor[Optional[List[Op]]]):
    """
    returns None: Modifications were done in place, no further actions required
    returns List[Op]: The returned list of operations should replace the visited operation.
                      For deletion, return empty list.
    """

    def __init__(self, regs: List[Register], toType: RType):
        self.regs = regs
        self.toType = toType
        super(RefineTypeVisitor, self)

    def visit_goto(self, op: Goto) -> Optional[List[Op]]:
        pass

    def visit_branch(self, op: Branch) -> Optional[List[Op]]:
        pass

    def visit_return(self, op: Return) -> Optional[List[Op]]:
        pass

    def visit_unreachable(self, op: Unreachable) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_assign(self, op: Assign) -> Optional[List[Op]]:
        if op.dest in self.regs and op.src.type == self.toType:
            op.dest.type = self.toType
            return None
        elif op.dest in self.regs and not op.src.type == self.toType:
            unbox = Unbox(op.src, self.toType, -1)
            return [unbox,
                    Assign(op.dest, unbox, op.line)]
        else:
            return None

    def visit_load_int(self, op: LoadInt) -> Optional[List[Op]]:
        if op in self.regs:
            print(op)
            op.value = op.value >> 1
            op.type = self.toType
        return None

    def visit_load_error_value(self, op: LoadErrorValue) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_get_attr(self, op: GetAttr) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_set_attr(self, op: SetAttr) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_load_static(self, op: LoadStatic) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_init_static(self, op: InitStatic) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_tuple_get(self, op: TupleGet) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_tuple_set(self, op: TupleSet) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_inc_ref(self, op: IncRef) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_dec_ref(self, op: DecRef) -> Optional[List[Op]]:
        # TODO need to remove this as int is no longer an object?
        pass

    def visit_call(self, op: Call) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_method_call(self, op: MethodCall) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_cast(self, op: Cast) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_box(self, op: Box) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_unbox(self, op: Unbox) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_raise_standard_error(self, op: RaiseStandardError) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_call_c(self, op: CallC) -> Optional[List[Op]]:
        if op in self.regs and all(map(lambda arg: arg in self.regs, op.sources())):
            if op.function_name == 'CPyTagged_Add':
                return [BinaryIntOp(self.toType, op.args[0], op.args[1], BinaryIntOp.ADD)]
            elif op.function_name == 'CPyTagged_Mult':
                return [BinaryIntOp(self.toType, op.args[0], op.args[1], BinaryIntOp.MUL)]
            elif op.function_name == 'CPyTagged_Sub':
                return [BinaryIntOp(self.toType, op.args[0], op.args[1], BinaryIntOp.SUB)]
            elif op.function_name == 'CPyTagged_Negate':
                i0 = LoadInt(0, -1, self.toType)
                return [i0,
                        BinaryIntOp(self.toType, i0, op.args[0], BinaryIntOp.SUB)
                        ]
            else:
                return None
        else:
            return None

    def visit_truncate(self, op: Truncate) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_load_global(self, op: LoadGlobal) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_binary_int_op(self, op: BinaryIntOp) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_comparison_op(self, op: ComparisonOp) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_load_mem(self, op: LoadMem) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_set_mem(self, op: SetMem) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_get_element_ptr(self, op: GetElementPtr) -> Optional[List[Op]]:
        # TODO
        pass

    def visit_load_address(self, op: LoadAddress) -> Optional[List[Op]]:
        # TODO
        pass


class ReplaceVisitor(OpVisitor[None]):

    def __init__(self, toReplace: Op, replaceWith: Op):
        self.toReplace = toReplace
        self.replaceWith = replaceWith
        super(ReplaceVisitor, self)

    def visit_goto(self, op: Goto) -> None:
        # TODO
        pass

    def visit_branch(self, op: Branch) -> None:
        # TODO
        pass

    def visit_return(self, op: Return) -> None:
        # TODO
        pass

    def visit_unreachable(self, op: Unreachable) -> None:
        # TODO
        pass

    def visit_assign(self, op: Assign) -> None:
        if op.src == self.toReplace:
            op.src = self.replaceWith

    def visit_load_int(self, op: LoadInt) -> None:
        # TODO
        pass

    def visit_load_error_value(self, op: LoadErrorValue) -> None:
        # TODO
        pass

    def visit_get_attr(self, op: GetAttr) -> None:
        # TODO
        pass

    def visit_set_attr(self, op: SetAttr) -> None:
        # TODO
        pass

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
        # TODO
        pass

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
