# SPDX-License-Identifier: Apache-2.0

function Import-QwenCloudEnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return @()
    }

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Env file not found: $Path"
    }

    $imported = @()
    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    foreach ($rawLine in $lines) {
        $line = $rawLine.Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith("#")) {
            continue
        }
        if ($line.StartsWith("export ")) {
            $line = $line.Substring(7).Trim()
        }

        $separator = $line.IndexOf("=")
        if ($separator -lt 1) {
            throw "Invalid env line in ${Path}: $rawLine"
        }

        $name = $line.Substring(0, $separator).Trim()
        $value = $line.Substring($separator + 1).Trim()
        if ($name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
            throw "Invalid env variable name in ${Path}: $name"
        }

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        [Environment]::SetEnvironmentVariable($name, $value, "Process")
        $imported += $name
    }

    return $imported
}

function Test-QwenCloudEnvValuePresent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $false
    }

    $trimmed = $value.Trim()
    $placeholderTokens = @(
        "<alibaba-access-key-id>",
        "<alibaba-access-key-secret>",
        "<optional-account-id>",
        "<qwen-cloud-api-key>",
        "<registry-host>",
        "<registry-password>",
        "<registry-username>",
        "<namespace>"
    )
    foreach ($token in $placeholderTokens) {
        if ($trimmed.Contains($token)) {
            return $false
        }
    }

    return $true
}
