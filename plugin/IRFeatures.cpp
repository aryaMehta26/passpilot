// IRFeatures: an LLVM pass plugin that prints a JSON summary of a module's IR.
// PassPilot feeds these numbers to the LLM agent (as context) and to the cost model (as features).
//   opt -load-pass-plugin=build/IRFeatures.dylib -passes=ir-features -disable-output x.bc
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/IntrinsicInst.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Plugins/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"
#include <map>
#include <string>

using namespace llvm;

namespace {

struct IRFeaturesPass : PassInfoMixin<IRFeaturesPass> {
  PreservedAnalyses run(Module &M, ModuleAnalysisManager &MAM) {
    auto &FAM = MAM.getResult<FunctionAnalysisManagerModuleProxy>(M).getManager();
    std::map<std::string, unsigned long> F;
    unsigned MaxDepth = 0;

    for (Function &Fn : M) {
      if (Fn.isDeclaration())
        continue;
      F["functions"]++;
      LoopInfo &LI = FAM.getResult<LoopAnalysis>(Fn);
      for (Loop *L : LI.getLoopsInPreorder()) {
        F["loops"]++;
        if (L->getSubLoops().empty())
          F["innermost_loops"]++;
        MaxDepth = std::max(MaxDepth, L->getLoopDepth());
      }
      for (BasicBlock &BB : Fn) {
        F["blocks"]++;
        unsigned Depth = LI.getLoopDepth(&BB);
        for (Instruction &I : BB) {
          F["insts"]++;
          if (Depth > 0)
            F["insts_in_loops"]++;
          if (isa<LoadInst>(I)) F["loads"]++;
          else if (isa<StoreInst>(I)) F["stores"]++;
          else if (isa<AllocaInst>(I)) F["allocas"]++;
          else if (isa<PHINode>(I)) F["phis"]++;
          else if (isa<GetElementPtrInst>(I)) F["geps"]++;
          else if (I.isTerminator()) F["terminators"]++;
          else if (isa<CmpInst>(I)) F["compares"]++;
          else if (isa<IntrinsicInst>(I)) F["intrinsics"]++;
          else if (isa<CallBase>(I)) F["calls"]++;
          if (I.getType()->isVectorTy()) F["vector_insts"]++;
          if (I.getType()->isFloatingPointTy()) F["fp_insts"]++;
          if (I.isBinaryOp()) F["binops"]++;
        }
      }
    }
    F["max_loop_depth"] = MaxDepth;

    outs() << "{";
    bool First = true;
    for (auto &[K, V] : F) {
      outs() << (First ? "" : ", ") << "\"" << K << "\": " << V;
      First = false;
    }
    outs() << "}\n";
    return PreservedAnalyses::all();
  }
};

} // namespace

extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo llvmGetPassPluginInfo() {
  return {LLVM_PLUGIN_API_VERSION, "IRFeatures", "0.1", [](PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [](StringRef Name, ModulePassManager &MPM, ArrayRef<PassBuilder::PipelineElement>) {
                  if (Name != "ir-features")
                    return false;
                  MPM.addPass(IRFeaturesPass());
                  return true;
                });
          }};
}
