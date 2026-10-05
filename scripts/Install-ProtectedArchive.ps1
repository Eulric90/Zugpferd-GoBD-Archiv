param(
    [Parameter(Mandatory=$true)][string]$ArchiveRoot,
    [Parameter(Mandatory=$true)][string]$MediumA,
    [Parameter(Mandatory=$true)][string]$MediumB,
    [Parameter(Mandatory=$true)][string[]]$Operators,
    [string]$MigrateFrom
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Als Administrator starten; Einrichtung ändert sichtbar Dienst und NTFS-Rechte.' }
if (Get-Service ZugpferdArchivWriter -ErrorAction SilentlyContinue) { throw 'Dienst existiert bereits; kein stilles Neuinstallieren.' }
if ($ArchiveRoot.Contains('"') -or $ArchiveRoot.Contains("`n")) { throw 'Ungültiger Archivpfad' }
$rootPath = [IO.Path]::GetFullPath($ArchiveRoot)
$container = Split-Path $rootPath -Parent
$keyName = '.' + (Split-Path $rootPath -Leaf) + '-Schluessel'
if ($container.TrimEnd('\') -eq [IO.Path]::GetPathRoot($rootPath).TrimEnd('\')) { throw 'Eigenen Archivcontainer wählen, z.B. C:\GoBD\Archiv. Keine Rechteänderung am gesamten Laufwerk.' }
if (Test-Path $container) {
    $other = Get-ChildItem -LiteralPath $container -Force | Where-Object { $_.Name -notin @((Split-Path $rootPath -Leaf),$keyName) }
    if ($other) { throw 'Archivcontainer enthält fremde Daten. Neuen eigenen Container wählen; keine Rechteänderung an gemeinsamen Ordnern.' }
}
$volume = Get-Volume -DriveLetter ([IO.Path]::GetPathRoot($rootPath).Substring(0,1))
if ($volume.FileSystem -ne 'NTFS') { throw 'Lokales Dienstarchiv benötigt NTFS. Keine automatische Formatierung.' }
if ((Test-Path $rootPath) -and (Get-ChildItem -Force $rootPath)) { throw 'Neuen leeren Archivordner wählen; Altbestand ausdrücklich mit MigrateFrom übernehmen.' }
foreach ($account in $Operators) { $null = Get-LocalUser -Name $account }
$group = Get-LocalGroup ZugpferdArchivBediener -ErrorAction SilentlyContinue
if (-not $group) { $group = New-LocalGroup ZugpferdArchivBediener -Description 'Persönliche Archivbediener; keine direkten Schreibrechte auf übernommene Belege' }
foreach ($account in $Operators) {
    if (-not (Get-LocalGroupMember $group | Where-Object Name -eq "$env:COMPUTERNAME\$account")) { Add-LocalGroupMember -Group $group -Member $account }
}
$install = Join-Path $env:ProgramFiles 'ZugpferdArchiv'
if (Test-Path $install) { throw 'Installationsordner besteht; kein Überschreiben bestehender Installation.' }
Copy-Item (Join-Path $PSScriptRoot 'ZugpferdArchiv') $install -Recurse
$exe = Join-Path $install 'ZugpferdArchivService.exe'
$keys = Join-Path (Split-Path $rootPath -Parent) ('.' + (Split-Path $rootPath -Leaf) + '-Schluessel')
New-Item $rootPath,$keys -ItemType Directory -Force | Out-Null
foreach ($path in @($container,$rootPath,$keys)) {
    $initialAcl = [Security.AccessControl.DirectorySecurity]::new()
    $initialAcl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @('S-1-5-18','S-1-5-32-544')) {
        $initialAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
    }
    Set-Acl -LiteralPath $path -AclObject $initialAcl
}
$arguments = @('--provision','--root',$rootPath,'--medium-a',$MediumA,'--medium-b',$MediumB)
if ($MigrateFrom) { $arguments += @('--migrate-from',$MigrateFrom) }
$process = Start-Process -FilePath $exe -ArgumentList ($arguments | ForEach-Object { '"' + $_ + '"' }) -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Archivprüfung/Übernahme fehlgeschlagen; Quellen bleiben erhalten. Installation nicht abgeschlossen.' }
$serviceName = 'ZugpferdArchivWriter'
$serviceExe = Join-Path $install 'ZugpferdArchivService.exe'
& sc.exe create $serviceName binPath= ('"' + $serviceExe + '" --service') start= auto obj= "NT SERVICE\$serviceName"
if ($LASTEXITCODE -ne 0) { throw 'Dienstinstallation fehlgeschlagen' }
& sc.exe sidtype $serviceName unrestricted
if ($LASTEXITCODE -ne 0) { throw 'Dienstidentität konnte nicht eingerichtet werden' }
$serviceSid = ([Security.Principal.NTAccount]::new("NT SERVICE\$serviceName")).Translate([Security.Principal.SecurityIdentifier]).Value
$configFolder = Join-Path $env:ProgramData 'ZugpferdArchiv'
New-Item $configFolder -ItemType Directory -Force | Out-Null
$staging = Join-Path $configFolder 'Staging'
$keys = Join-Path (Split-Path $rootPath -Parent) ('.' + (Split-Path $rootPath -Leaf) + '-Schluessel')
New-Item $staging,$keys -ItemType Directory -Force | Out-Null
@{root=$rootPath;staging=$staging;operator_group_sid=$group.SID.Value} | ConvertTo-Json | Set-Content (Join-Path $configFolder 'service.json') -Encoding utf8
function Protect-Folder([string]$Path,[bool]$OperatorRead,[bool]$ResetChildren=$true) {
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
    foreach ($sid in @('S-1-5-18','S-1-5-32-544',$serviceSid)) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')
        $acl.AddAccessRule($rule)
    }
    if ($OperatorRead) { $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($group.SID,'ReadAndExecute','ContainerInherit,ObjectInherit','None','Allow')) }
    Set-Acl -LiteralPath $Path -AclObject $acl
    & icacls.exe $Path /setowner '*S-1-5-32-544' /T /C | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Eigentümerschutz fehlgeschlagen: $Path" }
    if ($ResetChildren -and (Get-ChildItem -LiteralPath $Path -Force | Select-Object -First 1)) {
        & icacls.exe "$Path\*" /reset /T /C | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Rechteprüfung fehlgeschlagen: $Path" }
    }
}
Protect-Folder $container $true $false
Protect-Folder $rootPath $true
Protect-Folder $configFolder $false
Protect-Folder $keys $false
foreach ($medium in @($MediumA,$MediumB)) {
    $mediumPath = [IO.Path]::GetFullPath($medium)
    $mediaVolume = Get-Volume -DriveLetter ([IO.Path]::GetPathRoot($mediumPath).Substring(0,1))
    if ($mediaVolume.FileSystem -eq 'NTFS' -and $mediumPath.TrimEnd('\') -ne [IO.Path]::GetPathRoot($mediumPath).TrimEnd('\')) {
        Protect-Folder $mediumPath $true
    } else {
        Write-Warning "Medium $mediumPath: kein NTFS-Ordnerschutz eingerichtet. Archivunterordner auf NTFS bevorzugen; keine automatische Formatierung."
        if ($mediaVolume.FileSystem -eq 'NTFS') {
            & icacls.exe $mediumPath /grant ("*$($serviceSid):(OI)(CI)M") /T /C | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Schreibdienst kann das USB-Archiv nicht erreichen' }
        }
    }
    Write-Host "USB $mediumPath : $($mediaVolume.FileSystem), frei $($mediaVolume.SizeRemaining) Bytes. Beide vollständigen Bestände plus Sicherungsstände benötigen ausreichend Platz."
}
Start-Service $serviceName
Write-Host "Geschütztes Archiv: $rootPath"
Write-Host 'Neu anmelden, damit Gruppenmitgliedschaft wirksam wird. Oberfläche als persönlicher Standardbenutzer starten.'
Write-Host 'Abnahme durchführen: Originalbearbeitung/-löschung müssen scheitern; Übernahme über Assistent und A/B-Rückleseprüfung müssen gelingen.'
Write-Host 'USB-Sticks A/B werden nicht formatiert. Vorhandene Konten wurden nicht zu Administratoren gemacht.'
