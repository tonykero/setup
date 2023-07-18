Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
scoop install sudo git
scoop bucket add main
scoop bucket add extras
scoop bucket add versions
sudo Add-MpPreference -ExclusionPath "$env:userprofile/scoop"

scoop install aria2 scoop-search