"""biometric.py — Windows Hello biometric authentication via PowerShell subprocess."""
from __future__ import annotations
import sys
import subprocess


class WindowsHello:
    """Windows Hello authentication wrapper."""

    @staticmethod
    def is_available() -> bool:
        """Check if Windows Hello is available on this machine."""
        if sys.platform != 'win32':
            return False
        try:
            result = subprocess.run(
                [
                    'powershell', '-NoProfile', '-NonInteractive', '-Command',
                    '[Windows.Security.Credentials.KeyCredentialManager, Windows.Security.Credentials, ContentType=WindowsRuntime] | Out-Null;'
                    '$availability = [Windows.Security.Credentials.KeyCredentialManager]::IsSupportedAsync().GetAwaiter().GetResult();'
                    'Write-Output $availability'
                ],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip().lower() == 'true'
        except Exception:
            return False

    @staticmethod
    def verify(reason: str = 'Authenticate') -> bool:
        """Prompt Windows Hello and return True if user verified."""
        if sys.platform != 'win32':
            return False
        try:
            script = (
                'Add-Type -AssemblyName System.Runtime.WindowsRuntime;'
                '[Windows.Security.Credentials.UI.UserConsentVerifier, Windows.Security.Credentials.UI, ContentType=WindowsRuntime] | Out-Null;'
                f'$result = [Windows.Security.Credentials.UI.UserConsentVerifier]::RequestVerificationAsync("{reason}").GetAwaiter().GetResult();'
                'Write-Output ($result -eq [Windows.Security.Credentials.UI.UserConsentVerificationResult]::Verified)'
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout.strip().lower() == 'true'
        except Exception:
            return False
