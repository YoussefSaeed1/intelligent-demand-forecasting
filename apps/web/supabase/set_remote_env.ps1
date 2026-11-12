# Phase 7D-1 helper: builds Supabase pooler connection strings in THIS PowerShell session only.
# Dot-source it:   . .\apps\web\supabase\set_remote_env.ps1
# Passwords are read with hidden prompts, URL-encoded, kept only in process environment variables and never printed.
# Clear afterwards with:   Clear-RemoteEnv
$ErrorActionPreference = 'Stop'
$ProjectRef = 'ecxswrwuylenwvsxghxg'

function Read-Secret([string]$Prompt) {
    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function New-PoolerUrl([string]$Role, [string]$Secret, [string]$PoolerHost, [int]$Port, [string]$TlsQuery) {
    if ([string]::IsNullOrEmpty($Secret)) { throw "Empty password for $Role" }
    $encoded = [uri]::EscapeDataString($Secret)
    return "postgresql://$Role.$ProjectRef`:$encoded@$PoolerHost`:$Port/postgres?$TlsQuery"
}

$PoolerHost = (Read-Host -Prompt 'Pooler host from Supabase Connect (e.g. aws-1-eu-central-1.pooler.supabase.com)').Trim()
if ($PoolerHost -notmatch '^aws-\d+-eu-central-1\.pooler\.supabase\.com$') { throw "Unexpected pooler host '$PoolerHost' (expected aws-N-eu-central-1.pooler.supabase.com)" }

# TLS: sslmode=require (encrypted) is the minimum. Supplying the Supabase CA certificate downloaded from the dashboard
# (Database settings > SSL configuration) upgrades to verify-full: certificate chain AND host name are verified.
$CaPath = (Read-Host -Prompt 'Path to the Supabase CA certificate for verify-full (press Enter to use sslmode=require)').Trim().Trim('"')
if ($CaPath) {
    $CaPath = (Resolve-Path -LiteralPath $CaPath).Path
    if (-not ((Get-Content -LiteralPath $CaPath -Raw) -match 'BEGIN CERTIFICATE')) { throw 'The file is not a PEM certificate' }
    $TlsQuery = 'sslmode=verify-full&ssl_min_protocol_version=TLSv1.2&sslrootcert=' + [uri]::EscapeDataString($CaPath)
    Write-Host 'TLS mode: verify-full (CA certificate supplied).'
} else {
    $TlsQuery = 'sslmode=require&ssl_min_protocol_version=TLSv1.2'
    Write-Host 'TLS mode: require (encrypted; server certificate not verified).'
}

$env:WEBAPP_OWNER_DATABASE_URL = New-PoolerUrl 'postgres' (Read-Secret 'Database (postgres) password') $PoolerHost 5432 $TlsQuery
Write-Host 'Owner session-pooler URL set (port 5432).'

$answer = Read-Host -Prompt 'Set webapp_api / engine_api transaction-pooler URLs now? (y/n)'
if ($answer -eq 'y') {
    $env:IDF_WEBAPP_URL = New-PoolerUrl 'webapp_api' (Read-Secret 'webapp_api password') $PoolerHost 6543 $TlsQuery
    $env:IDF_ENGINE_URL = New-PoolerUrl 'engine_api' (Read-Secret 'engine_api password') $PoolerHost 6543 $TlsQuery
    Write-Host 'webapp_api and engine_api transaction-pooler URLs set (port 6543).'
}

function global:Clear-RemoteEnv {
    Remove-Item Env:WEBAPP_OWNER_DATABASE_URL, Env:IDF_WEBAPP_URL, Env:IDF_ENGINE_URL -ErrorAction SilentlyContinue
    Write-Host 'Remote connection variables cleared from this session.'
}
