# MP-SPDZ: What to look at

## Goal

Understand how malicious-security mechanisms are implemented,
so we know where to inject faults and what a correct response looks like.

## Repository structure (relevant parts)

```
Protocols/       # Protocol implementations — THIS IS THE MAIN TARGET
  Spdz*          # SPDZ-family (dishonest majority, MAC-based)
  MaliciousShamir*  # Honest-majority Shamir
  Mascot*        # OT-based triple generation with malicious security
  Semi*          # Semi-honest variants (SPDZ minus security checks)
  Beaver*        # Beaver triple handling

Processor/       # VM that executes compiled MPC programs
  Machine.*      # Main execution loop
  Online*        # Online phase execution

Compiler/        # Python DSL → bytecode
  
Math/            # Field arithmetic, share representations
OT/              # Oblivious transfer
FHE/             # FHE-based offline phase (LowGear, HighGear)
```

## What to trace

### 1. MAC checks

The core of SPDZ malicious security.
Every secret value x has an associated MAC: γ(x) = α · x, where α is the global MAC key.
When opening a value, the MAC must be verified.

Questions:
- Where is the MAC check performed? (look for `check`, `verify`, `mac`)
- Is it batched or per-operation?
- What happens on failure? (abort? which parties are notified?)
- "Rushing at SPDZ" found a MISSING mac check in truncation. Where is truncation?

### 2. Semi-honest vs malicious: what's the diff?

The README says Semi/Semi2k are "MASCOT/SPDZ2k stripped of all steps
required for malicious security, namely:
- amplifying
- sacrificing
- MAC generation
- OT correlation checks"

→ Diff the Semi* and Spdz*/Mascot* files to see exactly what's added.
   That diff IS the attack surface for fault injection.

### 3. Beaver triple verification

In malicious SPDZ, triples are checked via "sacrificing":
generate extra triples, use them to verify the real ones.
- How is this implemented?
- What if a corrupt party provides a bad triple?

### 4. Shamir reconstruction

In MaliciousShamir, reconstruction uses error detection/correction
(Reed-Solomon properties of Shamir shares).
- How is reconstruction implemented?
- Does it actually detect a single corrupt share?
- Does behavior change with different (n, t)?

### 5. Opening protocol

Opening = revealing a secret-shared value.
This is where most attacks in "Rushing at SPDZ" happen.
- What's the sequence? (commit, open, check MAC, release)
- Is the MAC check BEFORE or AFTER the value is used?
- Thread safety? (the paper found race conditions here)

## Commands to try

```bash
# Clone MP-SPDZ
git clone https://github.com/data61/MP-SPDZ.git
cd MP-SPDZ

# Find MAC check implementations
grep -rn "mac_check\|MAC_Check\|MacCheck" Protocols/ --include="*.h" --include="*.cpp"

# Find where opening happens
grep -rn "open\|Open\|reveal" Protocols/ --include="*.h" --include="*.cpp" | head -40

# Find sacrifice/verification
grep -rn "sacrifice\|Sacrifice\|amplify\|Amplify" Protocols/ --include="*.h" --include="*.cpp"

# Diff semi-honest vs malicious
diff Protocols/SemiShare.h Protocols/SpdzShare.h
diff Protocols/SemiMC.h Protocols/MAC_Check.h

# Find truncation (where the Rushing at SPDZ bug was)
grep -rn "trunc\|Trunc" Protocols/ Processor/ --include="*.h" --include="*.cpp"
```

## After code reading: design decisions

- Which protocol to target first? (SPDZ is best-documented)
- What fault types? (corrupt share, corrupt MAC, corrupt triple, wrong message)
- How to inject? (modify MP-SPDZ source? interpose on network layer?)
- How to check? (protocol aborts = correct; wrong output = bug; crash = investigate)
