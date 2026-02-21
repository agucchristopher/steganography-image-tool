# just a quick test script to make sure the encryption actually works
# creates a tiny test image, hides a message in it, then tries to read it back
# tests three cases: right password, wrong password, and no password at all

from PIL import Image
import os
from steganography import encode_message, decode_message

TEST_IMG  = "_test_carrier.png"
TEST_OUT  = "_test_stego.png"
MESSAGE   = "this is a secret message!! nobody can see this 🔐"
PASSWORD  = "hunter2"

# make a tiny solid-color test image (100x100 is more than enough)
print("\n creating test image...")
img = Image.new("RGB", (100, 100), color=(42, 58, 90))
img.save(TEST_IMG)
print(f" saved: {TEST_IMG}")

print("\n" + "─" * 55)

# ── test 1: encode with password ──────────────────────────────
print("\n TEST 1 — encode with password")
r = encode_message(TEST_IMG, MESSAGE, TEST_OUT, password=PASSWORD)
assert r["success"], f"encode failed: {r['message']}"
print(f"  ✓ encoded! used {r['used']} chars out of {r['capacity']} capacity")

# ── test 2: decode with CORRECT password ──────────────────────
print("\n TEST 2 — decode with CORRECT password")
r = decode_message(TEST_OUT, password=PASSWORD)
assert r["success"], f"decode failed: {r['message']}"
assert r["secret"] == MESSAGE, f"message mismatch!\n  expected: {MESSAGE}\n  got:      {r['secret']}"
print(f"  ✓ decoded correctly!")
print(f"  message: \"{r['secret']}\"")

# ── test 3: decode with WRONG password ────────────────────────
print("\n TEST 3 — decode with WRONG password")
r = decode_message(TEST_OUT, password="wrongpassword123")
# it'll still find "a" message (the garbled one) - just not the right one
if r["success"]:
    garbled = r["secret"]
    same = (garbled == MESSAGE)
    print(f"  ✓ decoded something but it's {'the same (bad!!)' if same else 'garbled (correct!)'}")
    if not same:
        print(f"  garbled: \"{garbled[:60]}{'...' if len(garbled) > 60 else ''}\"")
    assert not same, "FAIL — wrong password gave back the original message, encryption is broken!!"
else:
    print(f"  ✓ got nothing back (also fine): {r['message']}")

# ── test 4: decode with NO password ───────────────────────────
print("\n TEST 4 — decode with NO password (should be garbled)")
r = decode_message(TEST_OUT, password="")
if r["success"]:
    garbled = r["secret"]
    same = (garbled == MESSAGE)
    print(f"  ✓ decoded something but it's {'the same (bad!!)' if same else 'garbled (correct!)'}")
    if not same:
        print(f"  garbled: \"{garbled[:60]}{'...' if len(garbled) > 60 else ''}\"")
    assert not same, "FAIL — no password gave back the original message!!"
else:
    print(f"  ✓ got nothing back: {r['message']}")

# ── test 5: encode WITHOUT password, decode WITHOUT password ──
print("\n TEST 5 — no password at all (should round-trip perfectly)")
r = encode_message(TEST_IMG, MESSAGE, TEST_OUT, password="")
assert r["success"]
r = decode_message(TEST_OUT, password="")
assert r["success"] and r["secret"] == MESSAGE, f"no-password round-trip failed: {r}"
print(f"  ✓ no-password round-trip works!")
print(f"  message: \"{r['secret']}\"")

# cleanup temp files
os.remove(TEST_IMG)
os.remove(TEST_OUT)

print("\n" + "─" * 55)
print(" all tests passed!! encryption is working correctly 🎉\n")
