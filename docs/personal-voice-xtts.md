# XTTS Personal Voice

Files are ready to copy into `facebook-ai-studio`.

## Required GitHub secret

Create `VOICE_REFERENCE_B64` from `voice_reference_a.wav`.

Linux/macOS:

```bash
base64 -w 0 voice_reference_a.wav
```

PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("voice_reference_a.wav"))
```

Run **Actions → Personal Voice XTTS → Run workflow**.
The generated MP3 is uploaded as a workflow artifact.

Never commit the WAV reference to a public repository.
