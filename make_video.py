from pathlib import Path
import subprocess
import shutil
import fitz
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# FLOODGUARD AI — FINAL 150 SECOND VIDEO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PPTX = Path(
    r"C:\Users\Prince\FloodGuard-Original\PPT-BentoGrid\OUTPUT\FloodGaurd_AI_BentoGrid.pptx"
)

OUTPUT_DIR = Path(
    r"C:\Users\Prince\FloodGuard-Original\output"
)

WORK_DIR = OUTPUT_DIR / "video_work"

BASE_VIDEO = OUTPUT_DIR / "FloodGuard_AI_150s_Video.mp4"

FINAL_VIDEO = OUTPUT_DIR / "FloodGuard_AI_150s_Video_Subtitled.mp4"

SRT_FILE = OUTPUT_DIR / "FloodGuard_AI_150s_Subtitles.srt"

SOFFICE = Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe"
)


# ============================================================
# EXISTING PDF LOCATIONS
# ============================================================

ROOT_PDF = BASE_DIR / "FloodGaurd_AI_BentoGrid.pdf"

OLD_PDF = OUTPUT_DIR / "FloodGaurd_AI_BentoGrid.pdf"


# ============================================================
# SLIDES
# ============================================================

# Opening:
# Slide 3 = Team Members

# Main:
# Slide 4, 7, 12, 14, 15, 18, 19, 20, 21, 22

MAIN_SLIDES = [
    4,
    7,
    12,
    14,
    15,
    18,
    19,
    20,
    21,
    22
]


# ============================================================
# VOICEOVER
# ============================================================

OPENING = (
    "Welcome to FloodGuard AI — an intelligent flood decision-support system "
    "that transforms real-time data into faster, explainable, "
    "and human-approved civic action."
)


NARRATIONS = [

    # Slide 4
    (
        "FloodGuard AI begins with a critical challenge: urban floods can change rapidly, "
        "while decision makers need reliable information in real time."
    ),

    # Slide 7
    (
        "Traditional flood prediction tells us where risk may occur, "
        "but prediction alone is not enough. Civic teams also need evidence, "
        "context, prioritization, and actionable recommendations."
    ),

    # Slide 12
    (
        "FloodGuard AI combines machine learning with multi-agent intelligence. "
        "It brings together live weather, flood risk, citizen reports, "
        "and operational evidence into one decision-support system."
    ),

    # Slide 14
    (
        "The pipeline starts with live weather and ML-based flood risk prediction. "
        "Citizen reports add ground-level evidence. Multiple AI agents then analyze "
        "the information and identify the most critical zones."
    ),

    # Slide 15
    (
        "Behind the system is a modular architecture connecting the dashboard, "
        "ML models, agent services, evidence processing, recommendations, "
        "and human approval into one coordinated workflow."
    ),

    # Slide 18
    (
        "Machine learning predicts flood risk from data. Agentic AI goes further "
        "by interpreting multiple sources, reasoning over evidence, generating "
        "explanations, and supporting operational decisions."
    ),

    # Slide 19
    (
        "Multiple specialized agents work together. They analyze weather, risk, "
        "citizen reports, and operational context before combining their findings "
        "into a unified decision."
    ),

    # Slide 20
    (
        "Evidence fusion brings these signals together, while zone prioritization "
        "ranks areas by risk, rainfall, water level, drainage capacity, "
        "and citizen reports."
    ),

    # Slide 21
    (
        "FloodGuard AI then generates an explainable recommendation for the selected zone. "
        "Human officers remain in control and can review, approve, reject, "
        "or modify the proposed action."
    ),

    # Slide 22
    (
        "The system connects AI intelligence with civic operations. "
        "Approved decisions can support response teams, while the complete decision "
        "process is recorded for transparency and auditability."
    )
]


# ============================================================
# THANK YOU
# ============================================================

THANK_YOU_NARRATION = (
    "Thank you for exploring FloodGuard AI — "
    "from prediction to action, with human-approved civic response."
)


# ============================================================
# TIMELINE
# ============================================================

# Opening
OPENING_DURATION = 8.0


# Main slides
MAIN_DURATIONS = [
    14.2,
    14.2,
    14.2,
    14.2,
    14.2,
    14.2,
    14.2,
    14.2,
    14.2,
    8.6
]


# Thank You
THANK_YOU_DURATION = 5.6


# Exact target:
#
# 8.0
# + 136.4
# + 5.6
# = 150.0 seconds


TARGET_DURATION = 150.0


TOTAL_TARGET = (
    OPENING_DURATION
    + sum(MAIN_DURATIONS)
    + THANK_YOU_DURATION
)


if abs(TOTAL_TARGET - TARGET_DURATION) > 0.01:
    raise ValueError(
        f"Timeline error. Expected 150 sec, got {TOTAL_TARGET}"
    )


# ============================================================
# VALIDATION
# ============================================================

if not PPTX.exists():
    raise FileNotFoundError(
        f"PPTX not found:\n{PPTX}"
    )


if not SOFFICE.exists():
    raise FileNotFoundError(
        f"LibreOffice not found:\n{SOFFICE}"
    )


if len(MAIN_SLIDES) != len(NARRATIONS):
    raise ValueError(
        "MAIN_SLIDES and NARRATIONS count do not match."
    )


if len(MAIN_SLIDES) != len(MAIN_DURATIONS):
    raise ValueError(
        "MAIN_SLIDES and MAIN_DURATIONS count do not match."
    )


# ============================================================
# PREPARE OUTPUT
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


if WORK_DIR.exists():
    shutil.rmtree(WORK_DIR)


WORK_DIR.mkdir(
    parents=True,
    exist_ok=True
)


PDF_FILE = WORK_DIR / "FloodGaurd_AI_BentoGrid.pdf"

SLIDES_DIR = WORK_DIR / "slides"

VOICES_DIR = WORK_DIR / "voices"

CLIPS_DIR = WORK_DIR / "clips"


SLIDES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

VOICES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CLIPS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# STEP 1 — FIND / CREATE PDF
# ============================================================

print()
print("==========================================")
print("STEP 1 — Preparing PowerPoint PDF")
print("==========================================")
print()


# ------------------------------------------------------------
# FIRST: use existing PDF if available
# ------------------------------------------------------------

existing_pdf = None


if ROOT_PDF.exists():

    existing_pdf = ROOT_PDF

    print(
        f"Existing PDF found:\n{ROOT_PDF}"
    )


elif OLD_PDF.exists():

    existing_pdf = OLD_PDF

    print(
        f"Existing PDF found:\n{OLD_PDF}"
    )


# ------------------------------------------------------------
# IF NO EXISTING PDF — RUN LIBREOFFICE
# ------------------------------------------------------------

if existing_pdf is None:

    print(
        "No existing PDF found."
    )

    print(
        "Converting PPTX using LibreOffice..."
    )

    subprocess.run(
        [
            str(SOFFICE),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(WORK_DIR),
            str(PPTX)
        ],
        check=True
    )


# ------------------------------------------------------------
# SEARCH FOR GENERATED / EXISTING PDF
# ------------------------------------------------------------

pdf_candidates = []


# Expected WORK_DIR PDF
if PDF_FILE.exists():

    pdf_candidates.append(
        PDF_FILE
    )


# Root PDF
if ROOT_PDF.exists():

    pdf_candidates.append(
        ROOT_PDF
    )


# Output PDF
if OLD_PDF.exists():

    pdf_candidates.append(
        OLD_PDF
    )


# Search WORK_DIR
if WORK_DIR.exists():

    pdf_candidates.extend(
        WORK_DIR.glob("*.pdf")
    )


# Search project folder
pdf_candidates.extend(
    BASE_DIR.glob("*.pdf")
)


# Remove duplicates
unique_candidates = []


for pdf in pdf_candidates:

    pdf = pdf.resolve()

    if pdf not in unique_candidates:

        unique_candidates.append(pdf)


# ------------------------------------------------------------
# SELECT PDF
# ------------------------------------------------------------

if not unique_candidates:

    raise FileNotFoundError(
        "\nPDF conversion failed.\n"
        "No PDF was found after LibreOffice conversion.\n"
        f"PPTX: {PPTX}\n"
        f"WORK_DIR: {WORK_DIR}"
    )


# Prefer existing PDF
selected_pdf = unique_candidates[0]


print()
print(
    f"Using PDF:\n{selected_pdf}"
)


# Copy selected PDF into WORK_DIR
if selected_pdf.resolve() != PDF_FILE.resolve():

    shutil.copy2(
        selected_pdf,
        PDF_FILE
    )

else:

    PDF_FILE = selected_pdf


print(
    f"Working PDF:\n{PDF_FILE}"
)


# ============================================================
# STEP 2 — PDF → PNG
# ============================================================

print()
print("==========================================")
print("STEP 2 — Rendering selected slides")
print("==========================================")
print()


doc = fitz.open(
    str(PDF_FILE)
)


slides_to_render = sorted(
    set(
        [3] + MAIN_SLIDES
    )
)


for slide_number in slides_to_render:

    page_index = slide_number - 1


    if (
        page_index < 0
        or page_index >= len(doc)
    ):

        raise ValueError(
            f"Slide {slide_number} does not exist in PPT."
        )


    page = doc[page_index]


    zoom = 2.0

    matrix = fitz.Matrix(
        zoom,
        zoom
    )


    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False
    )


    slide_file = (
        SLIDES_DIR
        / f"slide_{slide_number}.png"
    )


    pix.save(
        str(slide_file)
    )


    print(
        f"Rendered slide {slide_number}"
    )


doc.close()


# ============================================================
# STEP 2b — FIX TEAM MEMBER PHOTOS ON OPENING SLIDE
# ============================================================
#
# LibreOffice mis-renders the two team member photos on slide 3
# (circles 2 and 3) as dark blobs. This step re-composites the
# original face photos into the correct circular frames.
#
# Only circles 2 (Alka Raikwar) and 3 (Aniket Jaiswal) are
# replaced. Circle 1 (Prince Jain / Team Leader) is untouched.
# Everything else on the slide is preserved pixel-for-pixel.
# ============================================================

print()
print("==========================================")
print("STEP 2b — Fixing team member photos")
print("==========================================")
print()


def _make_circle_photo(
    photo_path,
    diameter,
    face_top_fraction=0.75,
):
    """
    Load *photo_path*, crop a square centred on the face
    (upper *face_top_fraction* of image height, horizontally
    centred), resize to *diameter* × *diameter*, apply a
    circular mask, and return an RGBA PIL image ready to paste.
    """
    photo = Image.open(str(photo_path)).convert("RGBA")
    w, h = photo.size

    # --- crop a square that captures the face ---
    # Use the upper face_top_fraction of the height as the
    # region of interest, then take the largest square that
    # fits, horizontally centred.
    roi_h = int(h * face_top_fraction)
    side = min(w, roi_h)
    left_crop = (w - side) // 2
    top_crop = 0
    photo = photo.crop(
        (left_crop, top_crop, left_crop + side, top_crop + side)
    )

    # --- resize to circle diameter ---
    photo = photo.resize(
        (diameter, diameter),
        Image.Resampling.LANCZOS
    )

    # --- apply circular mask ---
    mask = Image.new("L", (diameter, diameter), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse(
        [0, 0, diameter - 1, diameter - 1],
        fill=255
    )
    photo.putalpha(mask)

    return photo


# Photo asset paths
_PHOTO_ALKA = Path(
    r"C:\Users\Prince\FloodGuard-Original\PPT-BentoGrid\ASSETS\Alka Raikwar.png.png"
)

_PHOTO_ANIKET = Path(
    r"C:\Users\Prince\FloodGuard-Original\PPT-BentoGrid\ASSETS\Aniket Jaiswal.png.png"
)

# Pixel coordinates of the three circles in the 2880×1620 slide PNG.
# Measured from the rendered slide (2× zoom from PDF).
# circle_bbox = (x_left, y_top, width, height)
_CIRCLE_1_BBOX = (79, 239, 320, 341)   # Team Leader — DO NOT TOUCH
_CIRCLE_2_BBOX = (79, 701, 320, 341)   # Team member 1 — Alka Raikwar
_CIRCLE_3_BBOX = (79, 1160, 320, 341)  # Team member 2 — Aniket Jaiswal

_SLIDE3_PATH = SLIDES_DIR / "slide_3.png"

if _SLIDE3_PATH.exists() and _PHOTO_ALKA.exists() and _PHOTO_ANIKET.exists():

    slide3 = Image.open(str(_SLIDE3_PATH)).convert("RGBA")

    for photo_path, bbox in [
        (_PHOTO_ALKA,   _CIRCLE_2_BBOX),
        (_PHOTO_ANIKET, _CIRCLE_3_BBOX),
    ]:
        bx, by, bw, bh = bbox

        # Use the shorter dimension as the diameter so the
        # circle fits exactly inside the bounding box.
        diameter = min(bw, bh)

        # Centre the circle within the bounding box.
        offset_x = bx + (bw - diameter) // 2
        offset_y = by + (bh - diameter) // 2

        circle_img = _make_circle_photo(
            photo_path,
            diameter,
            face_top_fraction=0.75,
        )

        # Paste using the alpha channel as the mask so only
        # pixels inside the circle are written.
        slide3.paste(circle_img, (offset_x, offset_y), circle_img)

        print(
            f"Composited {photo_path.name} "
            f"→ circle at ({offset_x},{offset_y}) "
            f"diameter={diameter}px"
        )

    # Save back as RGB (video pipeline expects no alpha)
    slide3.convert("RGB").save(str(_SLIDE3_PATH))
    print("slide_3.png updated with corrected team photos.")

else:

    missing = []
    if not _SLIDE3_PATH.exists():
        missing.append(str(_SLIDE3_PATH))
    if not _PHOTO_ALKA.exists():
        missing.append(str(_PHOTO_ALKA))
    if not _PHOTO_ANIKET.exists():
        missing.append(str(_PHOTO_ANIKET))
    print(
        f"WARNING: skipping photo fix — "
        f"missing files: {missing}"
    )


# ============================================================
# STEP 3 — CREATE THANK YOU IMAGE
# ============================================================

print()
print("==========================================")
print("STEP 3 — Creating THANK YOU screen")
print("==========================================")
print()


THANK_YOU_IMAGE = (
    SLIDES_DIR
    / "thank_you.png"
)


WIDTH = 1920
HEIGHT = 1080


img = Image.new(
    "RGB",
    (WIDTH, HEIGHT),
    (10, 18, 32)
)


draw = ImageDraw.Draw(
    img
)


# IBM-style top/bottom bars

draw.rectangle(
    [0, 0, WIDTH, 18],
    fill=(15, 98, 254)
)


draw.rectangle(
    [0, HEIGHT - 18, WIDTH, HEIGHT],
    fill=(15, 98, 254)
)


FONT_PATH = (
    r"C:\Windows\Fonts\arial.ttf"
)


FONT_BOLD_PATH = (
    r"C:\Windows\Fonts\arialbd.ttf"
)


try:

    title_font = ImageFont.truetype(
        FONT_BOLD_PATH,
        110
    )


    subtitle_font = ImageFont.truetype(
        FONT_PATH,
        42
    )


except Exception:

    title_font = ImageFont.load_default()

    subtitle_font = ImageFont.load_default()


THANK_TEXT = "THANK YOU"


SUBTITLE_TEXT = (
    "FloodGuard AI — From Prediction to Action"
)


# ------------------------------------------------------------
# TITLE
# ------------------------------------------------------------

bbox = draw.textbbox(
    (0, 0),
    THANK_TEXT,
    font=title_font
)


text_width = (
    bbox[2] - bbox[0]
)


title_x = (
    WIDTH - text_width
) // 2


title_y = 400


draw.text(
    (title_x, title_y),
    THANK_TEXT,
    font=title_font,
    fill=(255, 255, 255)
)


# ------------------------------------------------------------
# SUBTITLE
# ------------------------------------------------------------

bbox = draw.textbbox(
    (0, 0),
    SUBTITLE_TEXT,
    font=subtitle_font
)


subtitle_width = (
    bbox[2] - bbox[0]
)


subtitle_x = (
    WIDTH - subtitle_width
) // 2


subtitle_y = 560


draw.text(
    (subtitle_x, subtitle_y),
    SUBTITLE_TEXT,
    font=subtitle_font,
    fill=(120, 190, 255)
)


img.save(
    str(THANK_YOU_IMAGE)
)


# ============================================================
# STEP 4 — GENERATE VOICES
# ============================================================

print()
print("==========================================")
print("STEP 4 — Generating English AI voiceover")
print("==========================================")
print()


ALL_NARRATIONS = (
    [OPENING]
    + NARRATIONS
    + [THANK_YOU_NARRATION]
)


VOICE_FILES = []


for index, text in enumerate(
    ALL_NARRATIONS
):

    voice_file = (
        VOICES_DIR
        / f"voice_{index:02d}.mp3"
    )


    print(
        f"Generating voice "
        f"{index + 1}/{len(ALL_NARRATIONS)}"
    )


    tts = gTTS(
        text=text,
        lang="en",
        slow=False
    )


    tts.save(
        str(voice_file)
    )


    VOICE_FILES.append(
        voice_file
    )


# ============================================================
# VIDEO CLIP FUNCTION
# ============================================================

def create_clip(
    image_file,
    voice_file,
    output_file,
    duration
):

    subprocess.run(
        [
            "ffmpeg",
            "-y",

            "-loop",
            "1",

            "-i",
            str(image_file),

            "-i",
            str(voice_file),

            "-vf",
            (
                "scale=1920:1080:"
                "force_original_aspect_ratio=decrease,"
                "pad=1920:1080:"
                "(ow-iw)/2:(oh-ih)/2"
            ),

            # Pad audio with silence
            # so clip reaches exact duration
            "-af",
            "apad",

            "-t",
            str(duration),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-pix_fmt",
            "yuv420p",

            "-c:a",
            "aac",

            "-b:a",
            "192k",

            "-movflags",
            "+faststart",

            str(output_file)
        ],
        check=True
    )


# ============================================================
# STEP 5 — OPENING
# ============================================================

print()
print("==========================================")
print("STEP 5 — Creating opening")
print("==========================================")
print()


opening_image = (
    SLIDES_DIR
    / "slide_3.png"
)


opening_clip = (
    CLIPS_DIR
    / "clip_00_opening.mp4"
)


create_clip(
    opening_image,
    VOICE_FILES[0],
    opening_clip,
    OPENING_DURATION
)


# ============================================================
# STEP 6 — MAIN PROJECT CLIPS
# ============================================================

print()
print("==========================================")
print("STEP 6 — Creating main project clips")
print("==========================================")
print()


CLIP_FILES = [
    opening_clip
]


for index, slide_number in enumerate(
    MAIN_SLIDES
):

    print(
        f"Creating main clip "
        f"{index + 1}/{len(MAIN_SLIDES)} "
        f"— Slide {slide_number}"
    )


    image_file = (
        SLIDES_DIR
        / f"slide_{slide_number}.png"
    )


    voice_file = (
        VOICE_FILES[index + 1]
    )


    clip_file = (
        CLIPS_DIR
        / (
            f"clip_{index + 1:02d}"
            f"_slide_{slide_number}.mp4"
        )
    )


    create_clip(
        image_file,
        voice_file,
        clip_file,
        MAIN_DURATIONS[index]
    )


    CLIP_FILES.append(
        clip_file
    )


# ============================================================
# STEP 7 — THANK YOU CLIP
# ============================================================

print()
print("==========================================")
print("STEP 7 — Creating THANK YOU ending")
print("==========================================")
print()


thank_you_clip = (
    CLIPS_DIR
    / "clip_11_thank_you.mp4"
)


thank_you_voice = (
    VOICE_FILES[-1]
)


create_clip(
    THANK_YOU_IMAGE,
    thank_you_voice,
    thank_you_clip,
    THANK_YOU_DURATION
)


CLIP_FILES.append(
    thank_you_clip
)


# ============================================================
# STEP 8 — CONCAT
# ============================================================

print()
print("==========================================")
print("STEP 8 — Joining all clips")
print("==========================================")
print()


CONCAT_FILE = (
    WORK_DIR
    / "concat.txt"
)


with open(
    CONCAT_FILE,
    "w",
    encoding="utf-8"
) as f:

    for clip in CLIP_FILES:

        safe_path = (
            str(
                clip.resolve()
            )
            .replace("\\", "/")
        )


        f.write(
            f"file '{safe_path}'\n"
        )


# ============================================================
# CONCAT VIDEO
# ============================================================

subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(CONCAT_FILE),

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-movflags",
        "+faststart",

        str(BASE_VIDEO)
    ],
    check=True
)


# ============================================================
# STEP 9 — CREATE SRT
# ============================================================

print()
print("==========================================")
print("STEP 9 — Creating subtitles")
print("==========================================")
print()


def format_srt_time(
    seconds
):

    milliseconds = int(
        round(
            (
                seconds
                - int(seconds)
            ) * 1000
        )
    )


    # Handle rounding to exactly 1000 ms
    if milliseconds >= 1000:

        milliseconds = 0

        seconds = (
            int(seconds) + 1
        )


    total_seconds = int(
        seconds
    )


    hours = (
        total_seconds
        // 3600
    )


    minutes = (
        total_seconds
        % 3600
    ) // 60


    secs = (
        total_seconds
        % 60
    )


    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


ALL_DURATIONS = (
    [OPENING_DURATION]
    + MAIN_DURATIONS
    + [THANK_YOU_DURATION]
)


current_time = 0.0


srt_lines = []


for index, (
    narration,
    duration
) in enumerate(
    zip(
        ALL_NARRATIONS,
        ALL_DURATIONS
    ),
    start=1
):

    start_time = (
        current_time
    )


    end_time = (
        current_time
        + duration
    )


    srt_lines.append(
        str(index)
    )


    srt_lines.append(
        f"{format_srt_time(start_time)} --> "
        f"{format_srt_time(end_time)}"
    )


    srt_lines.append(
        narration
    )


    srt_lines.append("")


    current_time = (
        end_time
    )


with open(
    SRT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(srt_lines)
    )


# ============================================================
# STEP 10 — BURN SUBTITLES
# ============================================================

print()
print("==========================================")
print("STEP 10 — Burning subtitles")
print("==========================================")
print()


subtitle_style = (
    "FontName=Arial,"
    "FontSize=16,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,"
    "BorderStyle=1,"
    "Outline=1,"
    "Shadow=0,"
    "Alignment=2,"
    "MarginV=30"
)


srt_filter_path = (
    str(
        SRT_FILE.resolve()
    )
    .replace("\\", "/")
)


srt_filter_path = (
    srt_filter_path
    .replace(":", "\\:")
)


subtitle_filter = (
    f"subtitles='{srt_filter_path}':"
    f"force_style='{subtitle_style}'"
)


subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-i",
        str(BASE_VIDEO),

        "-vf",
        subtitle_filter,

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-movflags",
        "+faststart",

        str(FINAL_VIDEO)
    ],
    check=True
)


# ============================================================
# STEP 11 — FORCE FINAL VIDEO TO EXACT 150 SECONDS
# ============================================================

print()
print("==========================================")
print("STEP 11 — Final 150 second correction")
print("==========================================")
print()


EXACT_VIDEO = (
    OUTPUT_DIR
    / "FloodGuard_AI_150s_Final.mp4"
)


subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-i",
        str(FINAL_VIDEO),

        "-t",
        "150",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-movflags",
        "+faststart",

        str(EXACT_VIDEO)
    ],
    check=True
)


# Replace subtitled video with exact final version

shutil.copy2(
    EXACT_VIDEO,
    FINAL_VIDEO
)


# ============================================================
# STEP 12 — FINAL DURATION CHECK
# ============================================================

print()
print("==========================================")
print("STEP 12 — Checking final video")
print("==========================================")
print()


probe = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",

        "-show_entries",
        "format=duration",

        "-of",
        "default="
        "noprint_wrappers=1:"
        "nokey=1",

        str(FINAL_VIDEO)
    ],

    capture_output=True,
    text=True,
    check=True
)


final_duration = float(
    probe.stdout.strip()
)


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("==========================================")
print("VIDEO GENERATION COMPLETE")
print("==========================================")
print()


print("Final video:")
print(
    FINAL_VIDEO
)


print()


print(
    f"Target duration: "
    f"{TARGET_DURATION:.2f} seconds"
)


print(
    f"Actual duration: "
    f"{final_duration:.2f} seconds"
)


print()


print(
    "Resolution: 1920x1080 Full HD"
)


print(
    "Audio: English AI voiceover"
)


print()


print(
    "Opening: "
    "Slide 3 — Team Members + WELCOME voice"
)


print(
    "Main: Slides "
    + ", ".join(
        map(
            str,
            MAIN_SLIDES
        )
    )
)


print(
    "Ending: "
    "THANK YOU screen + THANK YOU voice"
)


print(
    "Subtitles: "
    "English, bottom-center, small font"
)


print()


print(
    "Original PPT was NOT modified."
)


print()


if abs(
    final_duration - TARGET_DURATION
) <= 0.5:

    print(
        "STATUS: PERFECT — approximately 150 seconds"
    )

else:

    print(
        "STATUS: CHECK — duration is "
        f"{final_duration:.2f} seconds"
    )


print()
print("==========================================")
print()