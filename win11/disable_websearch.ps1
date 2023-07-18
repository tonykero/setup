$RegistryKeyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer"
if (! (Test-Path -Path $RegistryKeyPath)) 
{
    New-Item -Path $RegistryKeyPath -ItemType Directory -Force
}
Set-ItemProperty -Path $RegistryKeyPath -Name "DisableSearchBoxSuggestions" -Value 1 -Type DWORD
