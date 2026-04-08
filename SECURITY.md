# Security Policy

## Scope

cyrius-doom processes untrusted WAD files. Buffer overflow in WAD parsing is the primary attack surface.
All lump sizes must be bounds-checked before loading.

## Reporting

Report vulnerabilities to robert.maccracken@gmail.com.
