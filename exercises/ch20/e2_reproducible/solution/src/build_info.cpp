// SPDX-License-Identifier: MIT
// No __DATE__ or __TIME__: a build made tomorrow from the same sources must give the same bytes.
const char* build_info() { return "reproducible-demo " DEMO_VERSION; }
