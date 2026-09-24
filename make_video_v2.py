from pathlib import Path
import subprocess
import shutil
import fitz
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# FLOODGUARD AI -- NEW VIDEO (Team-7 Bob_Ai_Mavericks PPT)
# Target: 2:45 (165 seconds)
# Source: floodguard-ai/Team-7 Bob_Ai_Mavericks.pptx
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PPTX = BASE_DIR / "Team-7 Bob_Ai_Mavericks.pptx"

OUTPUT_DIR = Path(
    r"C:\Users\Prince\FloodGuard-Original\output"
)

WORK_DIR = OUTPUT_DIR / "video_work_v2"

BASE_VIDEO    = OUTPUT_DIR / "FloodGuard_AI_v2_Base.mp4"
FINAL_VIDEO   = OUTPUT_DIR / "FloodGuard_AI_v2_Subtitled.mp4"
SRT_FILE      = OUTPUT_DIR / "FloodGuard_AI_v2_Subtitles.srt"
EXACT_VIDEO   = OUTPUT_DIR / "FloodGuard_AI_150s_Final.mp4"

SOFFICE = Path(
    r"C:\Program Files\LibreOffice\program\soffice.exe"
)


# ============================================================
# SLIDES (1-based)
# All 6 slides from the new PPT are used:
#   Slide 1 -- Hackathon / IBM SkillsBuild title
#   Slide 2 -- Methodology & team
#   Slide 3 -- Development with IBM Bob
#   Slide 4 -- IBM Bob screenshots
#   Slide 5 -- Key Features
#   Slide 6 -- Novelty & Future Scope
# ============================================================

OPENING_SLIDE = 1       # title slide used as opening frame
MAIN_SLIDES   = [2, 3, 4, 5, 6]


# ============================================================
# VOICEOVER -- derived from new PPT content only
# ============================================================

OPENING_NARRATION = (
    "Welcome to FloodGuard AI -- Team 7, Bob AI Mavericks. "
    "Presented at the Edunet Hackathon in collaboration with "
    "IBM SkillsBuild, powered by IBM Bob."
)

NARRATIONS = [

    # Slide 2 -- Methodology & team
    (
        "FloodGuard AI addresses urban flooding in Ahmedabad and Surat. "
        "The system collects rainfall, weather, drainage, and citizen-report data, "
        "uses machine learning to predict zone-level flood risk, "
        "and employs multiple AI agents to analyze evidence and generate "
        "explainable, prioritized response recommendations -- "
        "all with human-in-the-loop approval."
    ),

    # Slide 3 -- Development with IBM Bob
    (
        "IBM Bob supported every stage of the development lifecycle. "
        "The team used Bob to define requirements, plan the architecture, "
        "generate Python and Streamlit code, review outputs, "
        "validate flood-risk workflows, and produce technical documentation. "
        "Every Bob-assisted change was reviewed, refined, and approved by the team."
    ),

    # Slide 4 -- IBM Bob screenshots
    (
        "IBM Bob analyzed the FloodGuard AI project structure, "
        "assisted with machine learning flood-risk prediction, "
        "AI-agent workflows, and Streamlit dashboard components. "
        "Bob's code generation covered the full application -- "
        "from ML models and agent logic to UI modules and configuration."
    ),

    # Slide 5 -- Key Features
    (
        "FloodGuard AI delivers six key capabilities: "
        "a multi-agent AI system, ML-based flood-risk prediction, "
        "citizen flood reporting, drainage prioritization, "
        "evidence fusion across all data sources, "
        "and risk-to-action intelligence with human-approved civic response."
    ),

    # Slide 6 -- Novelty & Future Scope
    (
        "The system's novelty lies in combining multi-agent flood intelligence, "
        "evidence-based risk prioritization, explainable AI recommendations, "
        "and human-in-the-loop response. "
        "Future scope includes real-time sensor integration, "
        "advanced flood forecasting, GIS-based flood intelligence, "
        "and scaling to more flood-prone cities across India."
    ),
]

THANK_YOU_NARRATION = (
    "Thank you for exploring FloodGuard AI -- "
    "from prediction to action, with human-approved civic response. "
    "Team 7: Prince Jain, Alka Raikwar, and Aniket Jaiswal. Parul University."
)


# ============================================================
# TIMELINE  (total = 165 seconds = 2:45)
#
#   Opening  :  9.0 s
#   Slide 2  : 28.0 s
#   Slide 3  : 31.0 s
#   Slide 4  : 22.0 s
#   Slide 5  : 28.0 s
#   Slide 6  : 33.0 s   ← longest narration
#   Thank You: 14.0 s
#   ─────────────────
#   Total    : 165.0 s
# ============================================================

OPENING_DURATION  = 9.0
MAIN_DURATIONS    = [28.0, 31.0, 22.0, 28.0, 33.0]
THANK_YOU_DURATION = 14.0

TARGET_DURATION = 165.0

TOTAL_TARGET = (
    OPENING_DURATION
    + sum(MAIN_DURATIONS)
    + THANK_YOU_DURATION
)

if abs(TOTAL_TARGET - TARGET_DURATION) > 0.01:
    raise ValueError(
        f"Timeline error. Expected {TARGET_DURATION} s, got {TOTAL_TARGET} s"
    )


# ============================================================
# VALIDATION
# ============================================================

if not PPTX.exists():
    raise FileNotFoundError(f"PPTX not found:\n{PPTX}")

if not SOFFICE.exists():
    raise FileNotFoundError(f"LibreOffice not found:\n{SOFFICE}")

if len(MAIN_SLIDES) != len(NARRATIONS):
    raise ValueError("MAIN_SLIDES and NARRATIONS count do not match.")

if len(MAIN_SLIDES) != len(MAIN_DURATIONS):
    raise ValueError("MAIN_SLIDES and MAIN_DURATIONS count do not match.")


# ============================================================
# PREPARE OUTPUT DIRECTORIES
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if WORK_DIR.exists():
    shutil.rmtree(WORK_DIR)

WORK_DIR.mkdir(parents=True, exist_ok=True)

PDF_FILE   = WORK_DIR / "Team-7_Bob_Ai_Mavericks.pdf"
SLIDES_DIR = WORK_DIR / "slides"
VOICES_DIR = WORK_DIR / "voices"
CLIPS_DIR  = WORK_DIR / "clips"

for d in (SLIDES_DIR, VOICES_DIR, CLIPS_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ============================================================
# STEP 1 -- PPTX → PDF  (LibreOffice)
# ============================================================

print()
print("==========================================")
print("STEP 1 -- Converting PPTX to PDF")
print("==========================================")
print()

subprocess.run(
    [
        str(SOFFICE),
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(WORK_DIR),
        str(PPTX),
    ],
    check=True,
)

# LibreOffice names the output after the source file stem
generated_pdf = WORK_DIR / "Team-7 Bob_Ai_Mavericks.pdf"
if generated_pdf.exists() and generated_pdf.resolve() != PDF_FILE.resolve():
    shutil.move(str(generated_pdf), str(PDF_FILE))

if not PDF_FILE.exists():
    # fallback: look for any PDF in WORK_DIR
    pdfs = list(WORK_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(
            f"PDF conversion produced no file.\nWORK_DIR: {WORK_DIR}"
        )
    PDF_FILE = pdfs[0]

print(f"Working PDF: {PDF_FILE}")


# ============================================================
# STEP 2 -- PDF → PNG  (all 6 slides)
# ============================================================

print()
print("==========================================")
print("STEP 2 -- Rendering slides to PNG")
print("==========================================")
print()

doc = fitz.open(str(PDF_FILE))

slides_to_render = sorted(set([OPENING_SLIDE] + MAIN_SLIDES))

for slide_number in slides_to_render:

    page_index = slide_number - 1

    if page_index < 0 or page_index >= len(doc):
        raise ValueError(
            f"Slide {slide_number} does not exist in the PDF "
            f"(total pages: {len(doc)})."
        )

    page   = doc[page_index]
    zoom   = 2.0
    matrix = fitz.Matrix(zoom, zoom)
    pix    = page.get_pixmap(matrix=matrix, alpha=False)

    slide_file = SLIDES_DIR / f"slide_{slide_number}.png"
    pix.save(str(slide_file))
    print(f"Rendered slide {slide_number} -> {slide_file.name}")

doc.close()


# ============================================================
# STEP 3 -- CREATE THANK YOU IMAGE
# ============================================================

print()
print("==========================================")
print("STEP 3 -- Creating THANK YOU screen")
print("==========================================")
print()

THANK_YOU_IMAGE = SLIDES_DIR / "thank_you.png"

W, H = 1920, 1080
img  = Image.new("RGB", (W, H), (10, 18, 32))
draw = ImageDraw.Draw(img)

# IBM-style accent bars
draw.rectangle([0, 0, W, 18],       fill=(15, 98, 254))
draw.rectangle([0, H - 18, W, H],   fill=(15, 98, 254))

FONT_PATH      = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD_PATH = r"C:\Windows\Fonts\arialbd.ttf"

try:
    title_font    = ImageFont.truetype(FONT_BOLD_PATH, 110)
    subtitle_font = ImageFont.truetype(FONT_PATH, 38)
    credit_font   = ImageFont.truetype(FONT_PATH, 28)
except Exception:
    title_font    = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()
    credit_font   = ImageFont.load_default()

THANK_TEXT    = "THANK YOU"
SUBTITLE_TEXT = "FloodGuard AI -- From Prediction to Action"
CREDIT_TEXT   = "Team 7 · Prince Jain · Alka Raikwar · Aniket Jaiswal · Parul University"

def _centre_text(draw_obj, text, font, y, fill):
    bbox  = draw_obj.textbbox((0, 0), text, font=font)
    tw    = bbox[2] - bbox[0]
    x     = (W - tw) // 2
    draw_obj.text((x, y), text, font=font, fill=fill)

_centre_text(draw, THANK_TEXT,    title_font,    370, (255, 255, 255))
_centre_text(draw, SUBTITLE_TEXT, subtitle_font, 510, (120, 190, 255))
_centre_text(draw, CREDIT_TEXT,   credit_font,   580, (160, 200, 240))

img.save(str(THANK_YOU_IMAGE))
print(f"Thank You image saved -> {THANK_YOU_IMAGE.name}")


# ============================================================
# STEP 4 -- GENERATE VOICEOVERS  (gTTS)
# ============================================================

print()
print("==========================================")
print("STEP 4 -- Generating English voiceover")
print("==========================================")
print()

ALL_NARRATIONS = (
    [OPENING_NARRATION]
    + NARRATIONS
    + [THANK_YOU_NARRATION]
)

VOICE_FILES = []

for index, text in enumerate(ALL_NARRATIONS):

    voice_file = VOICES_DIR / f"voice_{index:02d}.mp3"

    print(f"Generating voice {index + 1}/{len(ALL_NARRATIONS)} …")

    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(str(voice_file))

    VOICE_FILES.append(voice_file)


# ============================================================
# CLIP HELPER
# ============================================================

def create_clip(image_file, voice_file, output_file, duration):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_file),
            "-i", str(voice_file),
            "-vf",
            (
                "scale=1920:1080:"
                "force_original_aspect_ratio=decrease,"
                "pad=1920:1080:"
                "(ow-iw)/2:(oh-ih)/2"
            ),
            "-af", "apad",
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_file),
        ],
        check=True,
    )


# ============================================================
# STEP 5 -- OPENING CLIP  (slide 1)
# ============================================================

print()
print("==========================================")
print("STEP 5 -- Creating opening clip")
print("==========================================")
print()

opening_image = SLIDES_DIR / f"slide_{OPENING_SLIDE}.png"
opening_clip  = CLIPS_DIR  / "clip_00_opening.mp4"

create_clip(opening_image, VOICE_FILES[0], opening_clip, OPENING_DURATION)

CLIP_FILES = [opening_clip]


# ============================================================
# STEP 6 -- MAIN SLIDES (2–6)
# ============================================================

print()
print("==========================================")
print("STEP 6 -- Creating main slide clips")
print("==========================================")
print()

for index, slide_number in enumerate(MAIN_SLIDES):

    print(
        f"  Clip {index + 1}/{len(MAIN_SLIDES)} -- Slide {slide_number}"
    )

    image_file = SLIDES_DIR / f"slide_{slide_number}.png"
    voice_file = VOICE_FILES[index + 1]
    clip_file  = CLIPS_DIR  / f"clip_{index + 1:02d}_slide_{slide_number}.mp4"

    create_clip(image_file, voice_file, clip_file, MAIN_DURATIONS[index])
    CLIP_FILES.append(clip_file)


# ============================================================
# STEP 7 -- THANK YOU CLIP
# ============================================================

print()
print("==========================================")
print("STEP 7 -- Creating THANK YOU ending")
print("==========================================")
print()

thank_you_clip  = CLIPS_DIR / f"clip_{len(MAIN_SLIDES) + 1:02d}_thank_you.mp4"
thank_you_voice = VOICE_FILES[-1]

create_clip(THANK_YOU_IMAGE, thank_you_voice, thank_you_clip, THANK_YOU_DURATION)
CLIP_FILES.append(thank_you_clip)


# ============================================================
# STEP 8 -- CONCAT ALL CLIPS
# ============================================================

print()
print("==========================================")
print("STEP 8 -- Joining all clips")
print("==========================================")
print()

CONCAT_FILE = WORK_DIR / "concat.txt"

with open(CONCAT_FILE, "w", encoding="utf-8") as f:
    for clip in CLIP_FILES:
        safe_path = str(clip.resolve()).replace("\\", "/")
        f.write(f"file '{safe_path}'\n")

subprocess.run(
    [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(CONCAT_FILE),
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(BASE_VIDEO),
    ],
    check=True,
)


# ============================================================
# STEP 9 -- BUILD SRT SUBTITLES
# ============================================================

print()
print("==========================================")
print("STEP 9 -- Creating subtitles")
print("==========================================")
print()


def format_srt_time(seconds):
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 0
        seconds = int(seconds) + 1
    ts  = int(seconds)
    h   = ts // 3600
    m   = (ts % 3600) // 60
    s   = ts % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


ALL_DURATIONS = (
    [OPENING_DURATION]
    + MAIN_DURATIONS
    + [THANK_YOU_DURATION]
)

current_time = 0.0
srt_lines    = []

for idx, (narration, duration) in enumerate(
    zip(ALL_NARRATIONS, ALL_DURATIONS), start=1
):
    start = current_time
    end   = current_time + duration
    srt_lines.extend([
        str(idx),
        f"{format_srt_time(start)} --> {format_srt_time(end)}",
        narration,
        "",
    ])
    current_time = end

with open(SRT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(srt_lines))


# ============================================================
# STEP 10 -- BURN SUBTITLES
# ============================================================

print()
print("==========================================")
print("STEP 10 -- Burning subtitles")
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
    str(SRT_FILE.resolve())
    .replace("\\", "/")
    .replace(":", "\\:")
)

subtitle_filter = (
    f"subtitles='{srt_filter_path}':"
    f"force_style='{subtitle_style}'"
)

subprocess.run(
    [
        "ffmpeg", "-y",
        "-i", str(BASE_VIDEO),
        "-vf", subtitle_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(FINAL_VIDEO),
    ],
    check=True,
)


# ============================================================
# STEP 11 -- TRIM TO EXACT TARGET DURATION  (165 s)
# ============================================================

print()
print("==========================================")
print("STEP 11 -- Trimming to exact 165 seconds")
print("==========================================")
print()

subprocess.run(
    [
        "ffmpeg", "-y",
        "-i", str(FINAL_VIDEO),
        "-t", str(int(TARGET_DURATION)),
        "-c:v", "libx264",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(EXACT_VIDEO),
    ],
    check=True,
)

# Replace previous final video
shutil.copy2(EXACT_VIDEO, FINAL_VIDEO)


# ============================================================
# STEP 12 -- DURATION PROBE
# ============================================================

print()
print("==========================================")
print("STEP 12 -- Checking final video")
print("==========================================")
print()

probe = subprocess.run(
    [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(EXACT_VIDEO),
    ],
    capture_output=True,
    text=True,
    check=True,
)

final_duration = float(probe.stdout.strip())


# ============================================================
# DONE
# ============================================================

print()
print("==========================================")
print("VIDEO GENERATION COMPLETE")
print("==========================================")
print()
print(f"Final video  : {EXACT_VIDEO}")
print(f"Target       : {TARGET_DURATION:.0f} s  ({TARGET_DURATION/60:.2f} min)")
print(f"Actual       : {final_duration:.2f} s  ({final_duration/60:.2f} min)")
print()
print("Resolution   : 1920x1080 Full HD")
print("Source PPT   : Team-7 Bob_Ai_Mavericks.pptx  (6 slides)")
print()
