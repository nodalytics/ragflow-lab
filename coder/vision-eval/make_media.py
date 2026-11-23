"""Build the vision test set in media/ and its answer key in items.json.

Generated images (every fact exact): an invoice and a code snippet to transcribe, a bar chart and a table to read,
shapes to count. A generated video: a red ball crossing left to right, then "GOAL" on a darkening background, made
with ffmpeg and sampled back into 8 frames the way any real video would be. Real photos: six from the COCO 2017
validation set (Flickr, their owners' licences), downloaded by URL and not committed, with fact lists written by
looking at each one.

Grading (run_vision.py): each item lists facts (a regex each, any wording that states the fact; fixed
2026-11-23 after reading the descriptions: two false negatives, chart values phrased at length and the video's
order told as numbered steps) and hallucinations
(things not in the picture), and the text items list the exact lines to transcribe.
Run: python3 make_media.py   (needs Pillow and ffmpeg)
"""

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(HERE, "media")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
DESCRIBE = "Describe this image in detail. Transcribe any text in it exactly."
COCO = "http://images.cocodataset.org/val2017/{}.jpg"


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else FONT, size)


def invoice():
    lines = ["INVOICE #4471", "Date: 2026-03-14", "Bill to: Harbor Supply Co.", "3 x Steel bolts M8      $4.50",
             "1 x Torque wrench       $38.00", "TOTAL DUE: $51.50"]  # fmt: skip
    im = Image.new("RGB", (760, 420), "white")
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((40, 30 + i * 60), ln, fill="black", font=font(30 if i else 38, mono=i in (3, 4)))
    im.save(os.path.join(M, "gen-invoice.png"))
    return {"id": "invoice", "files": ["gen-invoice.png"], "prompt": DESCRIBE, "ocr": lines,
            "facts": [["an invoice", r"invoice"], ["total 51.50", r"51\.50"], ["two items", r"bolt.*wrench|wrench.*bolt"]],
            "hallucinations": []}  # fmt: skip


def chart():
    data = [("North", 42), ("South", 17), ("East", 30), ("West", 8)]
    im = Image.new("RGB", (760, 480), "white")
    d = ImageDraw.Draw(im)
    d.text((240, 15), "Sales by region", fill="black", font=font(32))
    base, scale = 420, 7.5
    for i, (name, v) in enumerate(data):
        x = 90 + i * 165
        d.rectangle([x, base - v * scale, x + 100, base], fill=(60, 110, 200))
        d.text((x + 30, base - v * scale - 34), str(v), fill="black", font=font(26))
        d.text((x + 15, base + 10), name, fill="black", font=font(26))
    d.line([60, base, 720, base], fill="black", width=2)
    im.save(os.path.join(M, "gen-chart.png"))
    return {"id": "bar-chart", "files": ["gen-chart.png"], "prompt": DESCRIBE + " If it is a chart, give its values.",
            "ocr": [], "facts": [["a bar chart", r"bar"], ["the title", r"sales by region"],
                                 ["North 42", r"north[^\n\d]{0,100}42|42[^\n\d]{0,100}north"], ["South 17", r"south[^\n\d]{0,100}17|17[^\n\d]{0,100}south"],
                                 ["East 30", r"east[^\n\d]{0,100}30|30[^\n\d]{0,100}east"], ["West 8", r"west[^\n\d]{0,100}\b8\b|\b8\b[^\n\d]{0,100}west"]],
            "hallucinations": [["a line chart or pie", r"pie chart|line chart"]]}  # fmt: skip


def table():
    rows = [["Name", "Age", "City"], ["Amara", "34", "Lagos"], ["Bruno", "27", "Porto"], ["Chen", "45", "Xi'an"]]
    im = Image.new("RGB", (620, 300), "white")
    d = ImageDraw.Draw(im)
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            x, y = 30 + c * 190, 30 + r * 60
            d.rectangle([x, y, x + 190, y + 60], outline="black", width=2, fill=(225, 225, 225) if r == 0 else "white")
            d.text((x + 15, y + 14), cell, fill="black", font=font(28))
    im.save(os.path.join(M, "gen-table.png"))
    return {"id": "table", "files": ["gen-table.png"], "prompt": DESCRIBE + " If it is a table, give every row.",
            "ocr": [], "facts": [["a table", r"table"], ["Amara 34 Lagos", r"amara\W{0,20}34\W{0,20}lagos"],
                                 ["Bruno 27 Porto", r"bruno\W{0,20}27\W{0,20}porto"], ["Chen 45 Xi'an", r"chen\W{0,20}45\W{0,20}xi.?an"]],
            "hallucinations": []}  # fmt: skip


def shapes():
    im = Image.new("RGB", (700, 460), "white")
    d = ImageDraw.Draw(im)
    for x, y in [(70, 70), (250, 60), (480, 90), (120, 300), (600, 330)]:
        d.ellipse([x - 40, y - 40, x + 40, y + 40], fill=(220, 30, 30))
    for x, y in [(330, 220), (560, 200), (300, 380)]:
        d.rectangle([x - 35, y - 35, x + 35, y + 35], fill=(30, 70, 220))
    for x, y in [(110, 180), (430, 340)]:
        d.polygon([(x, y - 45), (x - 45, y + 35), (x + 45, y + 35)], fill=(30, 160, 60))
    im.save(os.path.join(M, "gen-shapes.png"))
    n = r"(?:{}|{})"
    return {"id": "count-shapes", "files": ["gen-shapes.png"],
            "prompt": "Describe this image. How many shapes of each kind and colour are there?", "ocr": [],
            "facts": [["5 red circles", n.format("5", "five") + r"\W{0,3}(?:red\W{0,3})?circles?|red circles?\D{0,20}" + n.format("5", "five")],
                      ["3 blue squares", n.format("3", "three") + r"\W{0,3}(?:blue\W{0,3})?squares?|blue squares?\D{0,20}" + n.format("3", "three")],
                      ["2 green triangles", n.format("2", "two") + r"\W{0,3}(?:green\W{0,3})?triangles?|green triangles?\D{0,20}" + n.format("2", "two")]],
            "hallucinations": [["a shape that is not there", r"star|hexagon|yellow"]]}  # fmt: skip


def code():
    lines = ["def area(radius):", "    return 3.14159 * radius ** 2", "", "print(area(2.5))"]
    im = Image.new("RGB", (720, 240), (30, 30, 30))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((30, 30 + i * 46), ln, fill=(230, 230, 230), font=font(30, mono=True))
    im.save(os.path.join(M, "gen-code.png"))
    return {"id": "code-screenshot", "files": ["gen-code.png"], "prompt": DESCRIBE, "ocr": [x for x in lines if x],
            "facts": [["python code", r"python"], ["a function computing an area", r"area"]], "hallucinations": []}  # fmt: skip


def video():
    tmp = tempfile.mkdtemp()
    n = 48  # 4 s at 12 fps
    for i in range(n):
        dark = max(0.0, (i - 32) / 15)  # the background darkens over the last third
        bg = tuple(int(255 * (1 - dark) + c * dark) for c in (15, 20, 60))
        im = Image.new("RGB", (480, 270), bg)
        d = ImageDraw.Draw(im)
        x = 30 + min(i, 30) * 14  # the ball crosses in the first 30 frames, then rests at the right
        d.ellipse([x - 25, 110, x + 25, 160], fill=(220, 30, 30))
        if i >= 30:
            d.text((150, 30), "GOAL", fill=(250, 200, 0), font=font(64))
        im.save(os.path.join(tmp, f"f{i:03d}.png"))
    mp4 = os.path.join(M, "gen-video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12", "-i", os.path.join(tmp, "f%03d.png"),
                    "-pix_fmt", "yuv420p", mp4], check=True)  # fmt: skip
    shutil.rmtree(tmp)
    files = frames(mp4, "gen-video", 8)
    return {"id": "video", "files": files, "video": "gen-video.mp4",
            "prompt": f"These are {len(files)} frames sampled in order from a short video. Describe what happens in the "
                      "video, in order.", "ocr": [],
            "facts": [["a red ball", r"red (?:ball|circle|sphere|dot)"], ["it moves left to right", r"left\W.{0,60}right|rightward|to the right"],
                      ["GOAL appears", r"goal"], ["the background darkens", r"dark|black|night|navy|fades?"],
                      ["GOAL comes after the movement", r"^(?:(?!goal).)*(?:mov|cross|right).*goal"]],
            "hallucinations": [["a person or a field", r"player|person|people|field|pitch"]]}  # fmt: skip


def frames(mp4, stem, k):
    """Sample k frames evenly from a video, as a client would before sending a video to an image model."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                               capture_output=True, text=True, check=True).stdout)  # fmt: skip
    out = []
    for j in range(k):
        t = dur * (j + 0.5) / k
        f = f"{stem}-frame{j}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", mp4, "-frames:v", "1",
                        os.path.join(M, f)], check=True)  # fmt: skip
        out.append(f)
    return out


PHOTOS = [
    ("000000039769", "cats", [["two cats", r"two (?:\w+ )?(?:cats|kittens)|2 cats"], ["asleep or lying", r"sleep|lying|lie|rest|napp"],
      ["a pink blanket", r"pink|magenta"], ["a couch", r"couch|sofa"], ["remote controls", r"remote"]],
     [["a dog", r"\bdogs?\b|puppy"]]),
    ("000000000139", "living-room", [["a television", r"\btv\b|television"], ["a dining table", r"table"], ["chairs", r"chair"],
      ["windows", r"window"], ["a person standing", r"woman|person|lady|someone|figure"], ["a kitchen or fridge", r"kitchen|fridge|refrigerator"],
      ["a fireplace", r"fireplace|hearth"], ["a flower in a vase", r"vase|flower"], ["a wooden floor", r"wood\w*\s+(?:\w+\s+)?floor|hardwood"]],
     [["a dog or a cat", r"\bdogs?\b|\bcats?\b"]]),
    ("000000397133", "old-kitchen", [["a kitchen", r"kitchen"], ["hanging pots and pans", r"pots|pans"], ["copper", r"copper"],
      ["a person with their back turned", r"back|facing away|from behind"], ["an apron", r"apron"], ["suspenders or braces", r"suspender|brace"],
      ["pies or pastry", r"pie|pastr|dough|tart"], ["a rolling pin", r"rolling pin"], ["a stove", r"stove|oven|range"]],
     [["a refrigerator or microwave", r"fridge|refrigerator|microwave"]]),
    ("000000000724", "stop-sign", [["a stop sign", r"stop sign"], ["upside down", r"upside[- ]down|inverted|rotated|flipped"],
      ["trees", r"tree"], ["a road", r"road|street|parking"], ["a blue sky", r"sky"], ["a building", r"building|house"]],
     [["a person", r"\bperson\b|\bpeople\b|pedestrian"]]),
    ("000000000776", "teddy-bears", [["teddy bears", r"teddy|stuffed (?:bear|animal)|plush"], ["several of them", r"three|four|3|4|several|group|multiple"],
      ["brown", r"brown|golden|tan|orange"], ["blue fabric", r"blue"]],
     [["a real animal", r"\breal (?:bear|animal)|\bdog\b"]]),
    ("000000001000", "tennis-group", [["a group of children", r"child|kid|boy|girl|young"], ["tennis", r"tennis"],
      ["a trophy", r"trophy|award|cup"], ["caps", r"cap|hat"], ["rackets", r"racket|racquet"], ["a fence or net", r"fence|net"]],
     [["adults only", r"group of (?:adults|men|women)\b"]]),
]  # fmt: skip


def photos():
    items = []
    for cid, name, facts, hall in PHOTOS:
        f = f"coco-{cid}.jpg"
        p = os.path.join(M, f)
        if not os.path.exists(p):
            urllib.request.urlretrieve(COCO.format(cid), p)
        items.append({"id": name, "files": [f], "prompt": DESCRIBE, "ocr": [], "facts": facts, "hallucinations": hall,
                      "source": COCO.format(cid)})  # fmt: skip
    return items


if __name__ == "__main__":
    os.makedirs(M, exist_ok=True)
    items = [invoice(), chart(), table(), shapes(), code(), video()] + photos()
    json.dump(items, open(os.path.join(HERE, "items.json"), "w"), indent=1)
    print(f"{len(items)} items, {sum(len(i['facts']) for i in items)} facts, "
          f"{sum(len(i['ocr']) for i in items)} lines to transcribe")  # fmt: skip
