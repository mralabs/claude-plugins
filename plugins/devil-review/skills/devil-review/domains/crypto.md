# Domain checklist — Crypto / security-critical code

**Authoritative loading rules live in `SKILL.md` Step 5.** This list is a human-readable summary of when the checklist applies. If the two drift, SKILL.md wins.

Load this checklist when the diff touches:
- anything that generates, stores, transmits, or verifies secrets: passwords, API keys, session tokens, JWTs, OAuth tokens, refresh tokens, TLS material
- calls to cryptographic libraries: `crypto`, `subtle`, `libsodium`, `openssl`, `ring`, `cryptography`, `bcrypt`, `argon2`, `scrypt`, `pbkdf2`, `hashlib`, `secrets`
- signature generation / verification paths: webhook signatures, JWT signing, request signing, package signatures
- encryption / decryption routines: symmetric (AES, ChaCha20) or asymmetric (RSA, ECC, Ed25519, X25519)
- key management: key generation, rotation, derivation (HKDF, PBKDF2), storage (KMS, keychain, HSM)
- random number generation that affects security: nonces, IVs, salts, session IDs, CSRF tokens, password reset tokens
- authentication flows: login, logout, password reset, 2FA/MFA, session creation
- authorization tokens: JWTs, opaque tokens, bearer tokens, capability tokens

Crypto bugs are **silent, catastrophic, and auditable after the fact**. A bug that leaks your database is embarrassing. A bug that leaks your signing key is existential. Every change in this domain is reviewed under the assumption that **someone will find it, and someone will exploit it**.

---

## Random source quality

- **Is the randomness cryptographically secure?** `Math.random()`, `rand()`, `Random` (Java), `random.random()` (Python) are NOT secure. Use `crypto.randomBytes`, `crypto.getRandomValues`, `secrets` (Python), `SecureRandom` (Java), `/dev/urandom`.
- **Is the entropy source available at the time of use?** Early boot, containers without `/dev/urandom`, sandboxed environments may return low-entropy values. Does the code check?
- **How many bytes?** A 32-bit token (~4 billion values) is guessable. Minimum 128 bits (16 bytes) for security-relevant tokens; 256 bits (32 bytes) for key material.
- **Token encoding**: hex is 4 bits per char, base64 is 6, base64url is URL-safe. Does the encoding change the effective entropy (e.g., truncation)?

---

## Nonce / IV / salt discipline

- **Nonce reuse with the same key is catastrophic** for most stream ciphers and AEAD modes (AES-GCM, ChaCha20-Poly1305). Two ciphertexts with the same (key, nonce) pair leak plaintext XOR and may allow forgery.
- **Is the nonce fresh per message?** Counter-based nonces need persistent state across restarts. Random nonces need enough bits (96-bit for GCM is borderline under birthday bound — use XChaCha20 or a nonce misuse-resistant mode for bulk encryption).
- **Is the salt fresh per password hash?** A shared salt across accounts defeats its purpose. Each stored password needs its own random salt (at least 16 bytes).
- **Is the IV reused on re-encryption?** When a message is re-encrypted (e.g., key rotation, re-wrapping), a new IV must be generated — reusing the old one with a new key is safe, but reusing with the same key is not.

---

## Algorithm choice

- **Password storage**: only `bcrypt`, `scrypt`, `argon2id`, or PBKDF2 with high iteration count (>600k for SHA-256). Never MD5, SHA-1, unsalted SHA-256. Not HMAC for passwords.
- **Symmetric encryption**: AES-GCM, AES-GCM-SIV, ChaCha20-Poly1305, XChaCha20-Poly1305, or AES-CBC with HMAC (encrypt-then-MAC). Not AES-ECB. Not DES/3DES. Not AES-CBC without HMAC.
- **Asymmetric encryption / signatures**: Ed25519 (signatures), X25519 (key exchange), RSA-PSS (signatures, min 2048-bit), RSA-OAEP (encryption). Not RSA-PKCS1v1.5 for new code. Not ECDSA without a secure random (known nonce bug).
- **Hashing for integrity / content addressing**: SHA-256, SHA-3, BLAKE2/BLAKE3. Not MD5, not SHA-1.
- **MACs**: HMAC-SHA256+, Poly1305, KMAC. Not naive `hash(key || message)` constructions.
- **Deprecated**: RC4, DES, 3DES, MD5, SHA-1. If the diff adds any of these, it's a finding regardless of context.

---

## Constant-time comparisons

- **Comparing secrets with `==` or `strcmp` leaks timing**. Authentication tokens, HMAC verification, password hashes — all require constant-time comparison:
  - Node: `crypto.timingSafeEqual`
  - Python: `hmac.compare_digest`
  - Go: `crypto/subtle.ConstantTimeCompare`
  - Rust: `constant_time_eq` or `subtle` crate
  - Java: `MessageDigest.isEqual`
- **Early return on length mismatch is also a timing leak** in some implementations — the comparison function should handle length-normalization.
- **Look for patterns like**: `if (providedToken === expectedToken)`, `if (hmac === computed)`, `if (password === stored)` — all potential timing leaks.

---

## Key management

- **Where does the key come from?** Hardcoded (bad), environment variable (okay for non-production), config file (depends on protection), KMS / HSM / secret manager (good).
- **Is the key logged?** Use the Grep tool to find the key variable name in error paths. A single `console.log(config)` with a key in it burns the key.
- **Key rotation**: does the change support rotation? Can old data still be decrypted with the previous key? Is there a key ID embedded in ciphertext so the right key is selected?
- **Key derivation**: if a key is derived from a password or master secret, is HKDF (or equivalent) used? Is there domain separation (distinct salts / info strings per use)?
- **Key material in memory**: does the change hold key bytes longer than necessary? Zeroize on drop where the language allows (Rust `zeroize` crate, explicit overwrite in Go/C).
- **Envelope encryption**: for large data or rotating keys, is data encrypted with a DEK, and DEK encrypted with a KEK? Does the change skip the envelope and encrypt directly with the KEK?

---

## Signature / MAC verification

- **Always verify before use**. Never parse a JWT, deserialize a signed payload, or act on a signed message before the signature is verified.
- **Algorithm confusion**: a JWT library that accepts `alg: none` is a classic bug. So is accepting `alg: HS256` with an RSA public key as the HMAC secret (algorithm downgrade).
- **Pin the expected algorithm**: don't let the token tell you which algorithm to use. Enforce from the verifier side.
- **Verify the claims after verifying the signature**: `iss`, `aud`, `exp`, `nbf`, `sub`. A valid signature on an expired token is still expired.
- **Webhook signatures**: is the signing secret per-source? Is replay prevented (timestamp + nonce + window)? Does the verifier reject missing signatures, or default to "allow if absent"?

---

## TLS / transport

- **Certificate verification**: is `rejectUnauthorized: false` / `verify=False` / `InsecureSkipVerify: true` anywhere in the diff? Usually a finding unless there's documented pinning.
- **TLS version floor**: minimum TLS 1.2, prefer 1.3. Any code that enables older versions is a finding.
- **Cipher suite restriction**: if the code explicitly configures ciphers, are weak ones excluded (RC4, 3DES, NULL, EXPORT)?
- **Certificate pinning**: does the code pin? Does the change update the pin correctly when rotating certs?
- **Hostname verification**: separate from cert verification. Some libraries disable hostname check by default (e.g., old Java HttpsURLConnection).

---

## Session / token handling

- **Session fixation**: is the session ID regenerated on login? If the pre-login session is reused post-login, an attacker who set the pre-login cookie has the authenticated session.
- **Session expiry**: absolute (max lifetime) AND idle (no activity). Both should be enforced.
- **Revocation**: can a session / token be revoked? Stateless JWTs have no native revocation — is there an allowlist / denylist?
- **Cookie flags**: `Secure`, `HttpOnly`, `SameSite=Strict` (or `Lax` with CSRF protection). Missing any is a finding for session cookies.
- **Token scope**: does a token carry the minimum privileges needed? Overbroad scopes are a breach amplifier.

---

## Input handling at the crypto boundary

- **User-supplied keys / IVs / signatures** are untrusted input. Validate length, format, encoding before passing to crypto primitives.
- **Padding oracle**: AES-CBC decryption that leaks "padding error" vs "MAC error" via distinct error messages or timing is a classic oracle. Use AEAD (GCM) instead, or constant-time error handling.
- **Deserialization of signed payloads**: verify signature first, then deserialize. Never the other way around — deserialization may execute code or allocate unbounded memory.
- **URL/form parameters with crypto**: a token passed in a URL ends up in logs, browser history, referer headers. Prefer POST body or headers.

---

## Storage of sensitive data

- **Encryption at rest**: is sensitive data encrypted in the database? Is the encryption key managed separately?
- **Logs**: does any log statement print request/response bodies that could contain tokens, passwords, or PII? Are log levels respected (debug-only vs production)?
- **Backups**: are database backups encrypted? Are backup keys rotated independently?
- **Memory dumps / crash reports**: are secrets scrubbed before upload?
- **Browser storage**: `localStorage` is accessible to XSS — tokens belong in HttpOnly cookies, not localStorage, for session auth. Does the change violate this?

---

## Signed payload contract (producer ↔ verifier drift)

Every signed payload — JWT, webhook, signed URL, SAML assertion, session cookie — is a contract between the producer (signer) and the verifier (consumer). The type signature `{ claims: { sub: string, exp: number } }` tells you nothing about the runtime format. Apply the **Runtime contract verification** step from `methodology.md` whenever a signed payload shape changes:

- **Claim type drift**: the producer writes `exp` as a Unix timestamp in seconds (standard for JWT), the verifier reads it as a JavaScript `Date` constructor argument (expects milliseconds). Off by 1000x — token expires way in the future or way in the past depending on direction. Type signature says `number`; neither side is wrong in isolation.
- **Claim rename**: the producer starts emitting `user_id` where the verifier expects `sub`. JSON parsing does not throw; `claims.sub` is `undefined` and most verifier libraries will happily accept that as "no subject claim".
- **Algorithm string casing / aliasing**: JWT `alg: "HS256"` vs `alg: "hs256"`. Some libraries are case-insensitive, some are not. A producer library upgrade that changes the case silently breaks verification on strict libraries.
- **Claim-shape backward compatibility**: adding a new required claim to the producer breaks existing in-flight tokens during deployment. Removing a claim from the producer leaves the verifier reading `undefined`.
- **Signed field vs unsigned envelope**: the verifier must operate on the *signed* representation (the exact bytes that were hashed), not on the parsed / re-serialized representation. JSON canonicalization differs across libraries — parsing and re-serializing a payload before verification invalidates the signature.
- **Webhook body vs headers**: the signature usually covers the raw request body. If middleware parses and re-serializes the body before the signature check (common in Express with `body-parser`), the bytes differ from what the producer signed. Result: verification always fails, or (worse) developer disables verification in frustration.
- **Nonce / timestamp is part of the signature computation — or not**: the real axis is not *where* the timestamp is transmitted (most providers use a header) but whether it is included in the bytes that the HMAC/signature covers. Stripe signs `<timestamp>.<body>` — the timestamp lives in the `Stripe-Signature` header but is also hashed, so replay protection works if and only if the verifier reconstructs the same `<timestamp>.<body>` string before comparing. GitHub's `X-Hub-Signature-256` covers the raw body only — the delivery timestamp is advisory, not cryptographically bound, and replay protection must come from application-level idempotency. A diff that switches providers without updating the verifier's reconstruction logic will either always fail verification (wrong string hashed) or silently accept replays (no timestamp in the signed data). Read the provider's signing docs directly — do not infer from the library's type signature.

**Read the producer's signing code, not the verifier's type signature.** The producer might be a different language, a different service, or a third-party whose source you have to find in their SDK. For JWTs specifically: read the **signing call site**, not just the claims type — the `jwt.sign(payload, secret, options)` call's `options` determines whether `exp`, `iat`, `nbf` are set automatically or must be in the payload.

When you verify a signed-payload contract, record both producer and verifier locations in the finding body (e.g., "producer: `auth-service/token.rs:88` sets `exp` as `SystemTime::now() + Duration::hours(1)` serialized as seconds — verifier: `api/middleware/jwt.ts:22` does `new Date(claims.exp)` which interprets as milliseconds — off by 1000x").

---

## Session / auth record fanout

Session and token records are frequent **Mutated record fanout** targets per `methodology.md`. A session object typically holds `access_token`, `refresh_token`, `expires_at`, `scope`, `user_id`, `device_id`, `last_seen`, `revoked_at`, `issued_at`. A diff that rotates one without the others leaves the session claiming the wrong thing:

- **Rotating `access_token` without `expires_at`**: session claims new token, old expiry — either prematurely rejected or accepted past its real lifetime.
- **Rotating `access_token` without `scope`**: the new token may have different scope than the old, but the cached `scope` claim is stale — authorization checks pass or fail incorrectly.
- **Logging out without clearing `refresh_token`**: the access token is gone but the refresh token can mint a new one — session revocation is incomplete.
- **Step-up auth that elevates `user_role`**: role changed but MFA-verified-at timestamp not updated, leaving derived "is this session currently MFA-verified?" checks reading stale state.

Record session/token entities in `mutated_records_inspected` with `kind: store-entity` and list every persisted field, not just the ones the diff wrote.

---

## Output integration

`scenarios_considered` must include at least one **attacker scenario** and one **misconfiguration scenario**. Examples:

```
- attacker replays a captured webhook request one hour later — signature still valid?
- attacker supplies JWT with alg: none — does verifier reject?
- nonce counter state is lost across restart — does encryption reuse an old nonce?
- developer hardcodes a test key in env var — does it end up in production config?
- TLS handshake fails during cert rotation — does the client fall back to plaintext?
- logged error includes the bearer token in a stack trace — does it reach the logging pipeline?
- password hash verification happens before user existence check — timing oracle reveals valid usernames?
```
