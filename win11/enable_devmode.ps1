$RegistryKeyPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
if (! (Test-Path -Path $RegistryKeyPath)) 
{
    New-Item -Path $RegistryKeyPath -ItemType Directory -Force
}
Set-ItemProperty -Path $RegistryKeyPath -Name AllowDevelopmentWithoutDevLicense -Type DWORD -Value 1

Enable-WindowsOptionalFeature -FeatureName Microsoft-Windows-Subsystem-Linux -Online -All -LimitAccess -NoRestart
Enable-WindowsOptionalFeature -FeatureName Microsoft-Hyper-V -Online -All -LimitAccess -NoRestart
Enable-WindowsOptionalFeature -FeatureName Containers -Online -All -LimitAccess -NoRestart