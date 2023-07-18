$RegistryKeyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Dsh"
if (! (Test-Path -Path $RegistryKeyPath)) 
{
    New-Item -Path $RegistryKeyPath -ItemType Directory -Force
}
Set-ItemProperty -Path $RegistryKeyPath -Name "AllowNewsAndInterests" -Value 0 -Type DWORD
