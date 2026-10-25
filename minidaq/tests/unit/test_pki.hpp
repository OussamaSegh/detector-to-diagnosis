// SPDX-License-Identifier: MIT
// A throw-away certificate authority for the TLS tests (Chapter 17): a CA, and
// a server certificate it signs for 127.0.0.1 and localhost, made at run time
// so that no private key is ever committed. ECDSA P-256, valid for one day.
#pragma once

#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>

#include <cstdio>
#include <filesystem>
#include <memory>
#include <string>

namespace minidaq::test_support {

struct Pki {
  std::filesystem::path ca_cert, server_cert, server_key, other_ca_cert;
};

namespace pki_detail {

struct KeyFree {
  void operator()(EVP_PKEY* k) const { EVP_PKEY_free(k); }
};
struct CertFree {
  void operator()(X509* c) const { X509_free(c); }
};
using Key = std::unique_ptr<EVP_PKEY, KeyFree>;
using Cert = std::unique_ptr<X509, CertFree>;

inline Key make_key() { return Key{EVP_EC_gen("P-256")}; }

inline void add_ext(X509* cert, X509* issuer, int nid, const char* value) {
  X509V3_CTX ctx;
  X509V3_set_ctx_nodb(&ctx);
  X509V3_set_ctx(&ctx, issuer, cert, nullptr, nullptr, 0);
  X509_EXTENSION* ext = X509V3_EXT_conf_nid(nullptr, &ctx, nid, value);
  X509_add_ext(cert, ext, -1);
  X509_EXTENSION_free(ext);
}

// A certificate for `key`, named `cn`, signed by issuer_key (self-signed if issuer is null).
inline Cert make_cert(EVP_PKEY* key, const char* cn, X509* issuer, EVP_PKEY* issuer_key, bool ca, long serial) {
  Cert cert{X509_new()};
  X509_set_version(cert.get(), 2);
  ASN1_INTEGER_set(X509_get_serialNumber(cert.get()), serial);
  X509_gmtime_adj(X509_getm_notBefore(cert.get()), -60);
  X509_gmtime_adj(X509_getm_notAfter(cert.get()), 24L * 3600);
  X509_set_pubkey(cert.get(), key);
  X509_NAME* name = X509_get_subject_name(cert.get());
  X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC, reinterpret_cast<const unsigned char*>(cn), -1, -1, 0);
  X509_set_issuer_name(cert.get(), issuer != nullptr ? X509_get_subject_name(issuer) : name);
  X509* signer = issuer != nullptr ? issuer : cert.get();
  if (ca) {
    add_ext(cert.get(), signer, NID_basic_constraints, "critical,CA:TRUE");
    add_ext(cert.get(), signer, NID_key_usage, "critical,keyCertSign,cRLSign");
  } else {
    add_ext(cert.get(), signer, NID_basic_constraints, "critical,CA:FALSE");
    add_ext(cert.get(), signer, NID_key_usage, "critical,digitalSignature");
    add_ext(cert.get(), signer, NID_ext_key_usage, "serverAuth");
    add_ext(cert.get(), signer, NID_subject_alt_name, "IP:127.0.0.1,DNS:localhost");
  }
  X509_sign(cert.get(), issuer_key != nullptr ? issuer_key : key, EVP_sha256());
  return cert;
}

inline void write_cert(const std::filesystem::path& p, X509* c) {
  FILE* f = std::fopen(p.c_str(), "w");
  PEM_write_X509(f, c);
  std::fclose(f);
}

inline void write_key(const std::filesystem::path& p, EVP_PKEY* k) {
  FILE* f = std::fopen(p.c_str(), "w");
  PEM_write_PrivateKey(f, k, nullptr, nullptr, 0, nullptr, nullptr);
  std::fclose(f);
}

}  // namespace pki_detail

// Writes the files into `dir`, which must exist.
inline Pki make_pki(const std::filesystem::path& dir) {
  using namespace pki_detail;
  const Key ca_key = make_key();
  const Cert ca = make_cert(ca_key.get(), "MiniDAQ test CA", nullptr, nullptr, true, 1);
  const Key server_key = make_key();
  const Cert server = make_cert(server_key.get(), "minidaq test server", ca.get(), ca_key.get(), false, 2);
  const Key other_key = make_key();
  const Cert other = make_cert(other_key.get(), "Some other CA", nullptr, nullptr, true, 3);
  Pki p{dir / "ca.pem", dir / "server.pem", dir / "server.key", dir / "other-ca.pem"};
  write_cert(p.ca_cert, ca.get());
  write_cert(p.server_cert, server.get());
  write_key(p.server_key, server_key.get());
  write_cert(p.other_ca_cert, other.get());
  return p;
}

}  // namespace minidaq::test_support
