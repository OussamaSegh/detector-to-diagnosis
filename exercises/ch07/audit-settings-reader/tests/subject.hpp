// SPDX-License-Identifier: MIT
// Exercise 7.6 (A): the code under audit, chosen by EX_MUTANT. 0 is the
// corrected change, which your tests must pass; 1 the agent's change; 2 and up
// each defect of it on its own, which your tests must fail. Do not open
// reference/ or defects/ before your report is written: they are the answer.
#pragma once

#ifndef EX_MUTANT
#define EX_MUTANT 0
#endif

#if EX_MUTANT == 0
#include "reference/settings.hpp"
#elif EX_MUTANT == 1
#include "agent/settings.hpp"
#elif EX_MUTANT == 2
#include "defects/defect_1.hpp"
#elif EX_MUTANT == 3
#include "defects/defect_2.hpp"
#endif
