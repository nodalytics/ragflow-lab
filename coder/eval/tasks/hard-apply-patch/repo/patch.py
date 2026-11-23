class PatchError(Exception):
    pass


def apply_patch(text, patch):
    """Apply a unified diff for one file to `text` and return the new text.

    `patch` may start with `--- ` and `+++ ` header lines; then come hunks, each starting with
    `@@ -a,b +c,d @@` (`,b` and `,d` may be left out, meaning 1). Hunk lines start with a space (context),
    `-` (removed) or `+` (added). Context and removed lines must match the text exactly.
    A hunk normally applies at line a (1-based; with b = 0 it inserts after line a). If the text there
    does not match, look for the same old lines up to 10 lines earlier or later, the nearest offset first
    (earlier before later at equal distance), and keep that offset for later hunks. If no position
    matches, raise PatchError. Lines keep their own line endings; the text's last line may lack a newline.
    """
    raise NotImplementedError
