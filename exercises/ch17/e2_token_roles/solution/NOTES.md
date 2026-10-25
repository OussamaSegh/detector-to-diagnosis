# Exercise 17.2: notes on the solution

The four defects of the starter are the four that real access-control code has most often:

1. **Fail open.** `required_role()` returned `none` for a command it did not know, so the
   `calibrate` command that someone adds next year would be open to everybody. The fix inverts
   the default: list what is allowed, and give everything else the strictest role.
2. **A default role.** An unknown role in the file (`admin`, `Operator`) became `observer`. A
   misspelling must stop the server with a message, not grant something.
3. **Lenient parsing.** A short digest, uppercase hex or a fourth field are signs of a broken or
   tampered file. A duplicate digest means two names share one token, so the audit trail could
   not tell them apart; a duplicate name makes revocation ambiguous.
4. **Timing.** `==` on `std::string` stops at the first differing byte, and the loop returned at
   the first match. Either tells an attacker something through the response time. The product
   uses `CRYPTO_memcmp` and a loop without an early exit.

**Why count comparisons.** A timing test would need thousands of repetitions, would be flaky on
a shared CI machine, and would still not prove much. Counting proves the property the code is
responsible for (every entry is compared, by the constant-time function) deterministically. It
does not prove that the comparison itself is constant time, which is OpenSSL's job (a SOUP
requirement), nor that the compiler did not optimize the loop; that is why the product keeps
the result in a variable instead of returning early, and why hashing first helps: an attacker
controls the token, not the digest that is compared.

Refusing malformed tokens before hashing costs nothing and keeps the comparison's inputs to
one length; the test checks that no comparison runs for them.
