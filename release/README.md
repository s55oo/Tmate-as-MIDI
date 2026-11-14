# Windows package downloads

| File | Version |
| --- | --- |
| [TMate-1.0-Windows-v0.1.0.zip](TMate-1.0-Windows-v0.1.0.zip) | software v0.1.0 (pre-release, not yet tested on Windows) |

Download the ZIP, extract the whole folder, then follow `WINDOWS-QUICKSTART.txt`
inside it. Check the download with PowerShell:

```powershell
Get-FileHash .\TMate-1.0-Windows-v0.1.0.zip -Algorithm SHA256
```

and compare with `TMate-1.0-Windows-v0.1.0.zip.sha256`.

These ZIPs are built with `tools/build-windows-zip.sh --public` and do not
include the original ELAD/WoodBoxRadio software or driver (not needed).
