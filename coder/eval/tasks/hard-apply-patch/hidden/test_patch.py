import pytest
from patch import apply_patch, PatchError

TEXT = "".join(f"line {i}\n" for i in range(1, 21))

P1 = """--- a/f.txt
+++ b/f.txt
@@ -3,3 +3,3 @@
 line 3
-line 4
+line four
 line 5
""".replace("            ", "")

def test_one_hunk():
    assert apply_patch(TEXT, P1) == TEXT.replace("line 4\n", "line four\n")

def test_two_hunks_add_and_remove():
    p = """@@ -1,2 +1,3 @@
 line 1
+inserted
 line 2
@@ -18,3 +19,2 @@
 line 18
-line 19
 line 20
""".replace("            ", "")
    out = apply_patch(TEXT, p).splitlines()
    assert out[:3] == ["line 1", "inserted", "line 2"] and "line 19" not in out and out[-1] == "line 20"

def test_offset_when_lines_moved():
    shifted = "new a\nnew b\nnew c\n" + TEXT
    assert apply_patch(shifted, P1) == shifted.replace("line 4\n", "line four\n")

def test_short_header_and_insert_at_end():
    p = "@@ -20,0 +21 @@\n+line 21\n"
    assert apply_patch(TEXT, p) == TEXT + "line 21\n"
    p2 = "@@ -5 +5 @@\n-line 5\n+LINE 5\n"
    assert apply_patch(TEXT, p2) == TEXT.replace("line 5\n", "LINE 5\n")

def test_mismatch_raises():
    bad = P1.replace(" line 5", " line 55")
    with pytest.raises(PatchError):
        apply_patch(TEXT, bad)

def test_too_far_raises():
    far = "".join(f"pad {i}\n" for i in range(15)) + TEXT
    with pytest.raises(PatchError):
        apply_patch(far, P1)

def test_no_final_newline_kept():
    t = "a\nb\nc"
    assert apply_patch(t, "@@ -1,2 +1,2 @@\n-a\n+A\n b\n") == "A\nb\nc"
