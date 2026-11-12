// Quality gate U-05 (Phase 7 quality gates, as interpreted in docs/PHASE7C_QA_REPORT.md section 4).
//
// The gate's purpose is that the application never makes a positive financial claim about simulated results.
// The same copy rules REQUIRE the negated caveat "not realised savings" (API ncuNotice, limitation L1, UI copy),
// so exactly these negated forms are approved. Any other occurrence of savings/profit/ROI/optimal fails, as does
// NCU without a hypothetical label or the fixed reorder point without its low-stock comparator label.

export const APPROVED_CAVEATS = [/\bnot\s+(?:realised\s+|realized\s+)?(?:financial\s+)?savings\b/gi];
const FORBIDDEN = [/\bsavings?\b/i, /\bprofits?\b/i, /\bprofitab\w*/i, /\bROI\b/, /\boptimal(?:ly|ity)?\b/i];

export function scanCopy(text) {
  const approvedCaveats = APPROVED_CAVEATS.reduce((n, re) => n + (text.match(re)?.length ?? 0), 0);
  const stripped = APPROVED_CAVEATS.reduce((t, re) => t.replace(re, " "), text);
  const violations = stripped.split(/\n+|(?<=\.)\s+/).map((s) => s.trim()).filter((line) => FORBIDDEN.some((re) => re.test(line)));
  const ncuWithoutHypothetical = /\bNCU\b/.test(text) && !/hypothetical/i.test(text);
  const ropWithoutComparatorLabel = /\bFixed (?:reorder point|ROP)\b/i.test(text) && !/low-stock comparator/i.test(text);
  return {
    pass: violations.length === 0 && !ncuWithoutHypothetical && !ropWithoutComparatorLabel,
    approvedCaveats,
    violations,
    ncuWithoutHypothetical,
    ropWithoutComparatorLabel,
  };
}
