# Pre-Export Checklist

Before publishing, verify the technical parameters of your render:

- [ ] **Resolution**: Exactly 1080x1920 (9:16 vertical aspect ratio).
- [ ] **Frame Rate**: Constant 30 fps (or 60 fps for ultra-smooth screen recordings).
- [ ] **Video Codec**: H.264 / AVC in High Profile, level 4.2.
- [ ] **Pixel Format**: `yuv420p` for maximum device compatibility.
- [ ] **Audio Stream**: AAC-LC, 48 kHz stereo, minimum 192 kbps.
- [ ] **Integrated Loudness**: -14.0 LUFS (±1.5 LUFS tolerance).
- [ ] **Maximum True Peak**: -1.0 dBFS to prevent clipping during platform transcoding.
- [ ] **Safe Zones**: Ensure no text or UI elements are covered by platform overlays (profile icons, comment trays, captions).
- [ ] **Artifacts & Frozen Frames**: Verify with `python engine/inspect_video.py <video>`.
