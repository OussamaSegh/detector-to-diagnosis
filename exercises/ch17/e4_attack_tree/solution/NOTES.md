# Exercise 17.4: notes on the solution

**The evaluator.** `attacks()` is a small recursive function once you see that an OR node is the
union of its children's attack sets and an AND node their cross product. Minimizing after every
node keeps the sets small and gives the result an exact meaning: each set is an attack that
needs every leaf in it and no fewer.

**What the threat model's tree says.** With every security requirement verified and the site
doing its part, one attack remains: fill the disk (3.2). The run then fails with a write fault,
so the scan is not silently wrong, but it is lost. Without the site's assumptions, four more attacks
appear, and one of them is the residual risk of H-08: a process running as the operator, with
the operator's token. `critical()` shows which requirements carry the weight: seven of the eight
requirements in the tree open an attack on their own if they fail. SRS-SEC-005 (no binding beyond
loopback without TLS and tokens) is not among them while the site keeps the account safe,
because reaching the port from the network still needs a token; it becomes critical once the
assumptions are dropped. That is defense in depth, measured.

**Your tree.** The solution's tree has nine leaves. With all controls and assumptions it is
closed; without the assumptions, four attacks open: three ways to write the files, each with
recomputing the CRC (1.2.2), which nothing blocks, and removing records from the audit trail
with the operator's account (3.1 with 3.2). Those are the two gaps in
threat-model.md, section 7: list-mode files are not signed, and the audit trail is not
tamper-evident.

**Disk full: security or safety?** Both. As a safety problem (a lost scan, a repeated dose) it
is H-01's territory, and its control is detection: the run is incomplete, and says so. As a
security problem (another user can cause it on purpose) its control is the site's: a partition
or a quota for the data (section 6, item 8). MiniDAQ could add a check for free space before a
run starts, which is a change request, not a fix.
