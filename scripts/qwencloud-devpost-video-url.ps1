# SPDX-License-Identifier: Apache-2.0

$script:QwenCloudDevpostVideoPlatformLabel = "YouTube, Vimeo, Facebook Video, or Youku"

function Get-QwenCloudDevpostVideoPlatformMessage {
    return "must be a public $script:QwenCloudDevpostVideoPlatformLabel URL"
}

function Test-QwenCloudDevpostVideoUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }
    if ($Url -match "[<>]|\.\.\.") { return $false }

    foreach ($pattern in @(
        "^https?://(www\.|m\.)?youtube\.com/watch\?v=",
        "^https?://(www\.|m\.)?youtube\.com/shorts/",
        "^https?://youtu\.be/",
        "^https?://(www\.)?vimeo\.com/",
        "^https?://player\.vimeo\.com/video/",
        "^https?://(www\.|m\.|web\.)?facebook\.com/watch/\?v=",
        "^https?://(www\.|m\.|web\.)?facebook\.com/.+/videos/",
        "^https?://fb\.watch/",
        "^https?://(v\.|m\.)?youku\.com/",
        "^https?://(www\.)?youku\.com/"
    )) {
        if ($Url -match $pattern) { return $true }
    }

    return $false
}
