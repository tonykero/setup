Set-Itemproperty -path 'HKCU:\Control Panel\Mouse' -Name 'MouseSpeed' -value 0
Set-Itemproperty -path 'HKCU:\Control Panel\Mouse' -Name 'MouseThreshold1' -value 0
Set-Itemproperty -path 'HKCU:\Control Panel\Mouse' -Name 'MouseThreshold2' -value 0

$code=@'
[DllImport("user32.dll", EntryPoint = "SystemParametersInfo")]
 public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, int[] pvParam, uint fWinIni);
'@
Add-Type $code -name Win32 -NameSpace System
[System.Win32]::SystemParametersInfo(4,0,0,2)
