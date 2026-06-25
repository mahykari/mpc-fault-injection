// Interface for runtime-disabling MAC staging at specific call sites.
// Used by the seeded-bug instrumentation to simulate missing MAC checks.
//
// Usage: MPSPDZ_DISABLED_SITES=processor_open,beaver_exchange ./mascot-party.x ...

#pragma once
#include <cstdlib>
#include <cstring>

inline bool MPSPDZ_SITE_DISABLED(const char* site_id) {
    static const char* disabled = std::getenv("MPSPDZ_DISABLED_SITES");
    if (!disabled) return false;
    return std::strstr(disabled, site_id) != nullptr;
}
