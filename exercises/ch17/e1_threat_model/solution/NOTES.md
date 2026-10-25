# Exercise 17.1: notes on the solution

**The checker.** Coverage is the rule that catches the most: a first draft almost always has
spoofing and disclosure, and almost never repudiation for the process or denial of service for
the flow. The status rules make each status carry its evidence: a requirement for "mitigated",
an assumption for "environment", a reason for the rest. The starter's D-02 ("someone stops the
scan through the page: accepted") fails them, and it should: accepting an elevation of
privilege on an interface that is meant to be read-only is a design decision nobody would sign.

**The model.** 14 threats for 3 elements; the 11 categories that apply each have at least one.
The ones that are easy to miss:

- D-02, the cross-site request. A browser that holds the operator's token for the room display
  can be made to send requests by any page it opens. The defense is structural: a token in a
  header (never a cookie) and no state-changing request at all.
- D-04, a false status page. A page that always says "running, complete" is a safety problem
  (the operator trusts an incomplete scan) more than a security one. TLS with a verified
  certificate is what makes the display's status trustworthy.
- D-13, framing. Cheap to prevent (DASH-008), and nobody thinks of it for an internal page.

**The questions.**

- *Drop:* nothing outright, but DASH-006 could log only refusals at a rate limit, so that a
  scan of the port does not flood the audit trail.
- *Missing:* how the display gets and stores its observer token, and how it is revoked when the
  display is replaced. That is a requirement on the installation, and the threat model is
  where it shows up first.
- *Worth it:* the status page adds a second network interface, an HTTP parser and a browser
  as a client, to show what `minidaq_ctl status` already shows. A display could instead run
  `minidaq_ctl status` with an observer token every second. The cheapest secure interface is
  the one you do not build; the threat model is the evidence for that discussion.
