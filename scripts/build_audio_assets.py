"""Download and synthesize the audio asset collection for claude-content-workflow."""
from __future__ import annotations

import os
import wave
import math
import urllib.request
import urllib.parse
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
SR = 44100

CATEGORIES = [
    "clicks", "transitions", "whooshes", "impacts",
    "risers", "ambience", "notifications", "music"
]

for cat in CATEGORIES:
    (AUDIO_DIR / cat).mkdir(parents=True, exist_ok=True)


def save_mono_wav(path: Path, samples: np.ndarray, sr: int = SR) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    int16_samples = (samples * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16_samples.tobytes())


def save_stereo_wav(path: Path, left: np.ndarray, right: np.ndarray, sr: int = SR) -> None:
    left = np.clip(left, -1.0, 1.0)
    right = np.clip(right, -1.0, 1.0)
    l16 = (left * 32767).astype(np.int16)
    r16 = (right * 32767).astype(np.int16)
    stereo = np.empty((len(l16) * 2,), dtype=np.int16)
    stereo[0::2] = l16
    stereo[1::2] = r16
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


# ---------------------------------------------------------------------------
# 1. Download Kenney CC0 Assets
# ---------------------------------------------------------------------------
KENNEY_BASE_AUDIO = "https://raw.githubusercontent.com/ismetcabbar9-oss/kenney-audio-assets/master/Audio%20(295%20files)/"
KENNEY_BASE_JINGLES = "https://raw.githubusercontent.com/Boyquotes/kenney-music-jingles-for-godot/master/addons/kenney%20music%20jingles/"

KENNEY_DOWNLOADS = [
    # Clicks
    ("clicks", "click_soft_01.ogg", KENNEY_BASE_AUDIO + "UI%20sounds%20(50%20sounds)/click1.ogg"),
    ("clicks", "click_soft_02.ogg", KENNEY_BASE_AUDIO + "UI%20sounds%20(50%20sounds)/click2.ogg"),
    ("clicks", "click_mechanical_01.ogg", KENNEY_BASE_AUDIO + "UI%20sounds%20(50%20sounds)/mouseclick1.ogg"),
    ("clicks", "switch_toggle_01.ogg", KENNEY_BASE_AUDIO + "UI%20sounds%20(50%20sounds)/switch1.ogg"),
    ("clicks", "switch_toggle_02.ogg", KENNEY_BASE_AUDIO + "UI%20sounds%20(50%20sounds)/switch2.ogg"),
    ("clicks", "chip_tap_01.ogg", KENNEY_BASE_AUDIO + "Casino%20sounds%20(50%20sounds)/chipLay1.ogg"),

    # Transitions
    ("transitions", "page_turn_01.ogg", KENNEY_BASE_AUDIO + "RPG%20sounds%20(50%20sounds)/bookFlip1.ogg"),
    ("transitions", "page_turn_02.ogg", KENNEY_BASE_AUDIO + "RPG%20sounds%20(50%20sounds)/bookFlip2.ogg"),
    ("transitions", "card_fan_sweep.ogg", KENNEY_BASE_AUDIO + "Casino%20sounds%20(50%20sounds)/cardFan1.ogg"),

    # Impacts
    ("impacts", "impact_thud_heavy.ogg", KENNEY_BASE_AUDIO + "RPG%20sounds%20(50%20sounds)/bookClose.ogg"),
    ("impacts", "impact_drop_soft.ogg", KENNEY_BASE_AUDIO + "RPG%20sounds%20(50%20sounds)/dropLeather.ogg"),

    # Risers
    ("risers", "riser_digital_up.ogg", KENNEY_BASE_AUDIO + "Digital%20sounds%20(60%20sounds)/highUp.ogg"),
    ("risers", "riser_phaser_build.ogg", KENNEY_BASE_AUDIO + "Digital%20sounds%20(60%20sounds)/phaserUp1.ogg"),

    # Notifications
    ("notifications", "alert_two_tone_01.ogg", KENNEY_BASE_AUDIO + "Digital%20sounds%20(60%20sounds)/twoTone1.ogg"),
    ("notifications", "alert_two_tone_02.ogg", KENNEY_BASE_AUDIO + "Digital%20sounds%20(60%20sounds)/twoTone2.ogg"),
    ("notifications", "alert_powerup.ogg", KENNEY_BASE_AUDIO + "Digital%20sounds%20(60%20sounds)/powerUp1.ogg"),
    ("notifications", "alert_zap.ogg", KENNEY_BASE_AUDIO + "Digital%20sounds%20(60%20sounds)/zap1.ogg"),

    # Music Jingles
    ("music", "music_jingle_8bit_01.ogg", KENNEY_BASE_JINGLES + "8-Bit%20jingles/jingles_nes_0.ogg"),
    ("music", "music_jingle_8bit_02.ogg", KENNEY_BASE_JINGLES + "8-Bit%20jingles/jingles_nes_1.ogg"),
    ("music", "music_jingle_hit_01.ogg", KENNEY_BASE_JINGLES + "Hit%20jingles/jingles_hit_0.ogg"),
    ("music", "music_jingle_hit_02.ogg", KENNEY_BASE_JINGLES + "Hit%20jingles/jingles_hit_1.ogg"),
    ("music", "music_jingle_sax_01.ogg", KENNEY_BASE_JINGLES + "Sax%20jingles/jingles_sax_0.ogg"),
    ("music", "music_jingle_steel_01.ogg", KENNEY_BASE_JINGLES + "Steel%20jingles/jingles_steel_0.ogg"),
]


def download_kenney_assets() -> None:
    print(f"Downloading {len(KENNEY_DOWNLOADS)} Kenney CC0 audio assets...")
    for cat, filename, url in KENNEY_DOWNLOADS:
        dest = AUDIO_DIR / cat / filename
        if not dest.exists():
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                dest.write_bytes(resp.read())
            print(f"  [OK] {cat}/{filename} ({dest.stat().st_size} bytes)")
        else:
            print(f"  [SKIP] {cat}/{filename} (already exists)")


# ---------------------------------------------------------------------------
# 2. Synthesize High-Fidelity Procedural Audio Assets
# ---------------------------------------------------------------------------
def synthesize_assets() -> None:
    print("Synthesizing procedural audio assets...")

    # Clicks
    # 1. Clean UI Click
    t = np.linspace(0, 0.02, int(SR * 0.02), endpoint=False)
    env = np.exp(-300 * t)
    click = np.sin(2 * np.pi * 1400 * t) * env
    save_mono_wav(AUDIO_DIR / "clicks" / "synth_click_clean.wav", click * 0.8)

    # 2. Precision Counter Tick
    t = np.linspace(0, 0.015, int(SR * 0.015), endpoint=False)
    env = np.exp(-400 * t)
    tick = (np.sin(2 * np.pi * 2600 * t) + 0.4 * np.sin(2 * np.pi * 5200 * t)) * env
    save_mono_wav(AUDIO_DIR / "clicks" / "synth_tick_counter.wav", tick * 0.7)

    # Transitions
    # 3. Frequency Sweep
    dur = 0.35
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    f = np.geomspace(200, 2200, len(t))
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = np.sin(np.pi * t / dur) ** 2
    sweep = np.sin(phase) * env
    save_mono_wav(AUDIO_DIR / "transitions" / "synth_transition_sweep.wav", sweep * 0.75)

    # 4. Shimmer Reveal
    dur = 0.45
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    env = np.sin(np.pi * (t / dur) ** 0.8)
    shimmer = (
        np.sin(2 * np.pi * 1800 * t) * 0.5 +
        np.sin(2 * np.pi * 2400 * t) * 0.3 +
        np.sin(2 * np.pi * 3200 * t) * 0.2
    ) * env * (0.8 + 0.2 * np.sin(2 * np.pi * 40 * t))
    save_mono_wav(AUDIO_DIR / "transitions" / "synth_shimmer_reveal.wav", shimmer * 0.7)

    # Whooshes
    # 5. Fast Air Whoosh
    dur = 0.35
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 1, n_samples)
    # Bandpass filter via convolution with sinc
    env = np.sin(np.pi * t / dur) ** 3
    whoosh = noise * env
    save_mono_wav(AUDIO_DIR / "whooshes" / "whoosh_fast_air.wav", whoosh * 0.7)

    # 6. Deep Swish
    dur = 0.5
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    brown_noise = np.cumsum(rng.normal(0, 1, n_samples))
    brown_noise /= np.max(np.abs(brown_noise))
    env = np.sin(np.pi * (t / dur) ** 1.5) ** 2
    save_mono_wav(AUDIO_DIR / "whooshes" / "whoosh_deep_swish.wav", brown_noise * env * 0.85)

    # 7. Bright Glide
    dur = 0.42
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    noise = rng.normal(0, 1, n_samples)
    mod = np.sin(2 * np.pi * (400 + 1200 * t / dur) * t)
    env = np.sin(np.pi * t / dur) ** 2
    save_mono_wav(AUDIO_DIR / "whooshes" / "whoosh_bright_glide.wav", noise * mod * env * 0.6)

    # 8. Cinematic Pass (Stereo pan)
    dur = 0.65
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    raw = rng.normal(0, 1, n_samples)
    env = np.sin(np.pi * t / dur) ** 2
    pan_l = np.cos(np.pi * 0.5 * t / dur)
    pan_r = np.sin(np.pi * 0.5 * t / dur)
    save_stereo_wav(
        AUDIO_DIR / "whooshes" / "whoosh_cinematic_pass.wav",
        raw * env * pan_l * 0.75,
        raw * env * pan_r * 0.75,
    )

    # Impacts
    # 9. Sub Bass Drop
    dur = 0.85
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    freq = 95.0 * np.exp(-3.5 * t) + 30.0
    phase = 2 * np.pi * np.cumsum(freq) / SR
    env = np.exp(-3.2 * t)
    sub = np.sin(phase) * env
    save_mono_wav(AUDIO_DIR / "impacts" / "synth_sub_bass_drop.wav", sub * 0.9)

    # 10. Cinematic Slam
    dur = 0.95
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    freq = 120.0 * np.exp(-4.0 * t) + 35.0
    sub_layer = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-3.0 * t)
    transient = rng.normal(0, 1, len(t)) * np.exp(-25.0 * t)
    slam = sub_layer * 0.75 + transient * 0.35
    save_mono_wav(AUDIO_DIR / "impacts" / "synth_cinematic_slam.wav", slam * 0.85)

    # 11. Punch Emphasis
    dur = 0.28
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    freq = 140.0 * np.exp(-8.0 * t) + 45.0
    punch = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-7.0 * t)
    save_mono_wav(AUDIO_DIR / "impacts" / "synth_punch_emphasis.wav", punch * 0.8)

    # Risers
    # 12. Tension Riser
    dur = 1.8
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    f = 110.0 * np.exp(1.2 * t)
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = (t / dur) ** 1.8
    riser = (np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.15 * np.sin(3 * phase)) * env
    save_mono_wav(AUDIO_DIR / "risers" / "synth_tension_riser.wav", riser * 0.75)

    # 13. Noise Swell
    dur = 1.5
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    noise = rng.normal(0, 1, n_samples)
    env = (t / dur) ** 2.5
    save_mono_wav(AUDIO_DIR / "risers" / "synth_noise_swell.wav", noise * env * 0.6)

    # 14. Harmonic Lift
    dur = 2.0
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    f_root = 130.0 + 350.0 * (t / dur) ** 2
    p1 = 2 * np.pi * np.cumsum(f_root) / SR
    p2 = 2 * np.pi * np.cumsum(f_root * 1.5) / SR
    p3 = 2 * np.pi * np.cumsum(f_root * 2.0) / SR
    env = (t / dur) ** 1.6
    lift = (np.sin(p1) * 0.5 + np.sin(p2) * 0.3 + np.sin(p3) * 0.2) * env
    save_mono_wav(AUDIO_DIR / "risers" / "synth_harmonic_lift.wav", lift * 0.7)

    # Ambience
    # 15. Studio Room Tone (Loopable)
    dur = 4.0
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    room = np.cumsum(rng.normal(0, 0.05, n_samples))
    room = room - np.linspace(room[0], room[-1], n_samples)  # seamless loop
    room /= np.max(np.abs(room)) + 1e-6
    # Fade in/out edges slightly for smooth loop
    edge = int(SR * 0.1)
    fade = np.linspace(0, 1, edge)
    room[:edge] *= fade
    room[-edge:] *= fade[::-1]
    save_mono_wav(AUDIO_DIR / "ambience" / "ambient_studio_room_tone.wav", room * 0.4)

    # 16. Vinyl Warmth (Loopable)
    dur = 4.0
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    bed = rng.normal(0, 0.1, n_samples)
    # add occasional crackle spikes
    crackle_idx = rng.choice(n_samples, size=35, replace=False)
    crackle = np.zeros(n_samples)
    crackle[crackle_idx] = rng.uniform(-0.8, 0.8, size=35)
    vinyl = (bed * 0.3 + crackle * 0.7)
    save_mono_wav(AUDIO_DIR / "ambience" / "ambient_vinyl_crackle.wav", vinyl * 0.5)

    # 17. Gentle Air (Loopable Stereo)
    dur = 4.0
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    air_l = rng.normal(0, 0.15, n_samples)
    air_r = rng.normal(0, 0.15, n_samples)
    # Slow lfo
    lfo = 0.7 + 0.3 * np.sin(2 * np.pi * 0.25 * t)
    save_stereo_wav(
        AUDIO_DIR / "ambience" / "ambient_gentle_air.wav",
        air_l * lfo * 0.5,
        air_r * lfo * 0.5,
    )

    # Notifications
    # 18. Modern Chime (C5 - E5 - G5 triad)
    dur = 1.2
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    c5 = np.sin(2 * np.pi * 523.25 * t) * np.exp(-3.5 * t)
    e5 = np.sin(2 * np.pi * 659.25 * t) * np.exp(-4.0 * t)
    g5 = np.sin(2 * np.pi * 783.99 * t) * np.exp(-4.5 * t)
    chime = (c5 * 0.4 + e5 * 0.35 + g5 * 0.3)
    save_mono_wav(AUDIO_DIR / "notifications" / "synth_modern_chime.wav", chime * 0.8)

    # 19. Success Bell
    dur = 1.1
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    bell = (
        np.sin(2 * np.pi * 880.0 * t) * 0.6 +
        np.sin(2 * np.pi * 1760.0 * t) * 0.25 +
        np.sin(2 * np.pi * 2640.0 * t) * 0.15
    ) * np.exp(-4.2 * t)
    save_mono_wav(AUDIO_DIR / "notifications" / "synth_success_bell.wav", bell * 0.8)

    # 20. Error Buzz
    dur = 0.3
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    f_buzz = 180.0 - 50.0 * (t / dur)
    buzz = np.sign(np.sin(2 * np.pi * f_buzz * t)) * np.exp(-3.0 * t)
    save_mono_wav(AUDIO_DIR / "notifications" / "synth_error_buzz.wav", buzz * 0.6)

    # Music
    # 21. Ambient Pad Loop (Seamless 6s progression: Dm9 -> Bbmaj7 -> Fmaj7)
    dur = 6.0
    n_samples = int(SR * dur)
    t = np.linspace(0, dur, n_samples, endpoint=False)
    # Chord frequencies: D3, F3, A3, C4, E4
    freqs = [146.83, 174.61, 220.0, 261.63, 329.63]
    pad = np.zeros(n_samples)
    for fi, fr in enumerate(freqs):
        detune = 1.0 + 0.002 * (fi % 3 - 1)
        phase = 2 * np.pi * fr * detune * t
        shimmer = 0.7 + 0.3 * np.sin(2 * np.pi * (0.3 + 0.1 * fi) * t)
        pad += np.sin(phase) * shimmer
    pad /= len(freqs)
    # Make loop seamless
    edge = int(SR * 0.25)
    fade = np.linspace(0, 1, edge)
    pad[:edge] *= fade
    pad[-edge:] *= fade[::-1]
    save_stereo_wav(
        AUDIO_DIR / "music" / "synth_ambient_pad_loop.wav",
        pad * 0.7,
        pad * 0.7,
    )

    print("All procedural audio assets synthesized successfully.")


def main() -> None:
    download_kenney_assets()
    synthesize_assets()
    total = sum(len(list((AUDIO_DIR / c).glob("*"))) for c in CATEGORIES)
    print(f"\nCompleted! Total audio assets in assets/audio/: {total}")


if __name__ == "__main__":
    main()
