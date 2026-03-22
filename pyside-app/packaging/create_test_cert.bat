@echo off
echo Creating self-signed test certificate for MSIX signing...
echo (For development/testing only - use a real cert for distribution)

powershell -Command "
$cert = New-SelfSignedCertificate -Subject 'CN=OctoChat' -CertStoreLocation 'Cert:\CurrentUser\My' -Type CodeSigning -KeyAlgorithm RSA -KeyLength 2048 -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(5)
$pwd = ConvertTo-SecureString -String 'octochat' -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath '%~dp0OctoChat_test.pfx' -Password $pwd
Write-Host 'Certificate created: OctoChat_test.pfx (password: octochat)'
Write-Host 'Trust it with: Import-Certificate -FilePath OctoChat_test.cer -CertStoreLocation Cert:\LocalMachine\TrustedPeople'
"
