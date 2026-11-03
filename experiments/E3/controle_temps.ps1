<#
.SYNOPSIS
  E3 - controle des horodatages et des extraits de preuve, avec ffmpeg et ffprobe uniquement.

.DESCRIPTION
  Pour chaque video :
    1. chronologie : temps de chaque image decodee (ffprobe) et empreinte MD5 de chaque image decodee (framemd5) ;
    2. pour des instants demandes, extraction d'une vignette et d'un extrait par plusieurs methodes ;
       l'image obtenue est retrouvee par son empreinte, puis comparee a l'image attendue.
  Sorties : experiments/E3/out/<nom_video>/ (non versionne). Voir PROTOCOLE.md.

.EXAMPLE
  .\controle_temps.ps1 -GenererMires
  .\controle_temps.ps1 -Video ..\..\data\videos\caviar\OneStopEnter2front.mpg -NbInstants 8
#>
[CmdletBinding()]
param(
    [switch]$GenererMires,
    [string[]]$Video = @(),
    [double[]]$Instants = @(),
    [int]$NbInstants = 8,
    [int]$Graine = 42,
    [double]$AvantS = 3.0,
    [double]$ApresS = 3.0,
    [switch]$SansSeekSortie
)

$ErrorActionPreference = 'Stop'
$inv = [Globalization.CultureInfo]::InvariantCulture
$racineSorties = Join-Path $PSScriptRoot 'out'
New-Item -ItemType Directory -Force $racineSorties | Out-Null

function Invoke-Outil([string]$exe, [string[]]$arguments) {
    # Windows PowerShell 5.1 transforme stderr en erreurs bloquantes si l'on redirige avec Stop.
    $ErrorActionPreference = 'Continue'
    $sortie = & $exe @arguments 2>$null
    if ($LASTEXITCODE -ne 0) { throw "$exe a echoue (code $LASTEXITCODE) : $($arguments -join ' ')" }
    return $sortie
}

function Format-Nombre([double]$x) { return $x.ToString('0.###', $inv) }
function Format-Temps([double]$x) { return $x.ToString('0.######', $inv) }

function New-Mires {
    $dossier = Join-Path $racineSorties 'mires'
    New-Item -ItemType Directory -Force $dossier | Out-Null
    $police = "fontfile='C\:/Windows/Fonts/arial.ttf'"
    $texte = "drawtext=${police}:text='n=%{n} pts=%{pts}':x=10:y=10:fontsize=28:fontcolor=white:box=1:boxcolor=black"
    $base = @('-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi')

    $cfr = Join-Path $dossier 'mire_cfr25_gop50.mp4'
    Invoke-Outil ffmpeg ($base + @('-i', 'testsrc2=size=640x360:rate=25:duration=60', '-vf', $texte,
            '-c:v', 'libx264', '-g', '50', '-pix_fmt', 'yuv420p', $cfr)) | Out-Null

    $vfr = Join-Path $dossier 'mire_vfr30_trous_gop60.mp4'
    Invoke-Outil ffmpeg ($base + @('-i', 'testsrc2=size=640x360:rate=30:duration=60',
            '-vf', "$texte,select='not(between(mod(n\,30)\,10\,19))'", '-fps_mode', 'vfr',
            '-c:v', 'libx264', '-g', '60', '-pix_fmt', 'yuv420p', $vfr)) | Out-Null

    $decale = Join-Path $dossier 'mire_cfr25_debut10s.ts'
    Invoke-Outil ffmpeg ($base + @('-i', 'testsrc2=size=640x360:rate=25:duration=60', '-vf', $texte,
            '-c:v', 'libx264', '-g', '50', '-pix_fmt', 'yuv420p', '-output_ts_offset', '10', '-f', 'mpegts', $decale)) | Out-Null

    return @($cfr, $vfr, $decale)
}

function Get-Valeur([string]$ligne, [string]$cle) {
    $m = [regex]::Match($ligne, "(?:^|\|)$cle=([^|]*)")
    if ($m.Success) { return $m.Groups[1].Value } else { return $null }
}

function ConvertTo-Double([string]$s) {
    if ([string]::IsNullOrEmpty($s) -or $s -eq 'N/A') { return $null }
    return [double]::Parse($s, $inv)
}

function Get-Chronologie([string]$chemin) {
    $flux = Invoke-Outil ffprobe @('-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_name,width,height,r_frame_rate,avg_frame_rate,time_base,start_time',
        '-of', 'compact=p=0', $chemin) | Select-Object -First 1
    $format = Invoke-Outil ffprobe @('-v', 'error', '-show_entries', 'format=format_name,start_time,duration',
        '-of', 'compact=p=0', $chemin) | Select-Object -First 1

    $images = New-Object System.Collections.Generic.List[object]
    $lignes = Invoke-Outil ffprobe @('-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'frame=pts_time,best_effort_timestamp_time', '-of', 'compact=p=0', $chemin)
    foreach ($l in $lignes) {
        if (-not ($l -match 'best_effort_timestamp_time=')) { continue }
        $pts = ConvertTo-Double (Get-Valeur $l 'pts_time')
        $be = ConvertTo-Double (Get-Valeur $l 'best_effort_timestamp_time')
        $images.Add([pscustomobject]@{ index = $images.Count; t_abs_s = $be; pts_absent = ($null -eq $pts); md5 = $null })
    }

    $empreintes = Invoke-Outil ffmpeg @('-hide_banner', '-loglevel', 'error', '-i', $chemin, '-map', '0:v:0',
        '-fps_mode', 'passthrough', '-f', 'framemd5', '-') | Where-Object { $_ -and -not $_.StartsWith('#') }
    $md5 = @($empreintes | ForEach-Object { ($_ -split ',')[-1].Trim() })

    $debutFormat = ConvertTo-Double (Get-Valeur $format 'start_time')
    if ($null -eq $debutFormat) { $debutFormat = 0.0 }
    $avg = Get-Valeur $flux 'avg_frame_rate'
    $p = $avg -split '/'
    $fps = if ($p.Count -eq 2 -and [double]$p[1] -ne 0) { [double]$p[0] / [double]$p[1] } else { $null }

    $coherent = ($md5.Count -eq $images.Count)
    if ($coherent) { for ($i = 0; $i -lt $images.Count; $i++) { $images[$i].md5 = $md5[$i] } }

    return [pscustomobject]@{
        flux = $flux; format = $format; images = $images; nb_md5 = $md5.Count; coherent = $coherent
        debut_format_s = $debutFormat; debut_video_s = $images[0].t_abs_s; fps_moyen = $fps
    }
}

function Get-IndexAttendu($chrono, [double]$tAbs) {
    $imgs = $chrono.images
    $lo = 0; $hi = $imgs.Count - 1; $res = 0
    while ($lo -le $hi) {
        $mid = [int][math]::Floor(($lo + $hi) / 2)
        if ($imgs[$mid].t_abs_s -le $tAbs + 0.000001) { $res = $mid; $lo = $mid + 1 } else { $hi = $mid - 1 }
    }
    return $res
}

function Find-Image($index, [string]$hash, [int]$attendu) {
    if (-not $hash -or -not $index.ContainsKey($hash)) { return @{ idx = $null; nb = 0 } }
    $cands = $index[$hash]
    $best = $cands | Sort-Object { [math]::Abs($_ - $attendu) } | Select-Object -First 1
    return @{ idx = $best; nb = $cands.Count }
}

function Get-PremiereEmpreinte([string[]]$argsAvantSortie) {
    $l = Invoke-Outil ffmpeg (@('-hide_banner', '-loglevel', 'error') + $argsAvantSortie +
        @('-map', '0:v:0', '-frames:v', '1', '-f', 'framemd5', '-')) | Where-Object { $_ -and -not $_.StartsWith('#') }
    if (-not $l) { return $null }
    return (@($l)[0] -split ',')[-1].Trim()
}

function Test-Video([string]$chemin) {
    $nom = [IO.Path]::GetFileName($chemin)
    $dossier = Join-Path $racineSorties $nom
    New-Item -ItemType Directory -Force $dossier | Out-Null
    Write-Host "== $nom"

    $c = Get-Chronologie $chemin
    $imgs = $c.images
    $c.images | ForEach-Object {
        [pscustomobject]@{ index = $_.index; t_abs_s = Format-Nombre $_.t_abs_s
            t_rel_ms = [math]::Round(($_.t_abs_s - $c.debut_video_s) * 1000); pts_absent = $_.pts_absent; md5 = $_.md5 }
    } | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $dossier 'chronologie.csv')

    $deltas = for ($i = 1; $i -lt $imgs.Count; $i++) { [math]::Round(($imgs[$i].t_abs_s - $imgs[$i - 1].t_abs_s) * 1000, 3) }
    $stats = $deltas | Measure-Object -Minimum -Maximum
    $nonMonotone = @($deltas | Where-Object { $_ -le 0 }).Count
    $ecartIndex = $null
    if ($c.fps_moyen) {
        $ecartIndex = ($imgs | ForEach-Object { [math]::Abs(($_.t_abs_s - $c.debut_video_s) - $_.index / $c.fps_moyen) * 1000 } |
            Measure-Object -Maximum).Maximum
    }
    $dupliquees = 0
    $index = @{}
    if ($c.coherent) {
        foreach ($im in $imgs) {
            if (-not $index.ContainsKey($im.md5)) { $index[$im.md5] = New-Object System.Collections.Generic.List[int] }
            $index[$im.md5].Add($im.index)
        }
        $dupliquees = ($index.Values | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Count - 1 } | Measure-Object -Sum).Sum
    }

    # Maximum plutot que derniere image : une derniere image sans PTS peut revenir a 0 (constate sur CAVIAR).
    $duree = ($imgs | Measure-Object -Property t_abs_s -Maximum).Maximum - $c.debut_video_s
    $resume = @(
        "video: $chemin"
        "flux: $($c.flux)"
        "format: $($c.format)"
        "images (ffprobe): $($imgs.Count) ; empreintes (framemd5): $($c.nb_md5) ; coherent: $($c.coherent)"
        "debut format (s): $(Format-Nombre $c.debut_format_s) ; premiere image (s): $(Format-Nombre $c.debut_video_s) ; decalage (ms): $(Format-Nombre (($c.debut_video_s - $c.debut_format_s) * 1000))"
        "duree mesuree premiere image->temps maximal (s): $(Format-Nombre $duree)"
        "intervalle entre images (ms): min $($stats.Minimum) ; max $($stats.Maximum) ; non croissants: $nonMonotone"
        "images sans PTS: $(@($imgs | Where-Object pts_absent).Count)"
        "ecart max temps lu vs index/fps_moyen (ms): $(if ($null -ne $ecartIndex) { Format-Nombre $ecartIndex } else { 'n/a' })"
        "images identiques a une autre (empreinte): $dupliquees"
    )

    if (-not $c.coherent) {
        $resume += "ARRET: nombre d'images different entre ffprobe et framemd5 ; appariement par empreinte impossible."
        $resume | Set-Content -Encoding UTF8 (Join-Path $dossier 'resume.txt'); $resume | Write-Host
        return
    }

    $quelconques = @($Instants)
    if ($quelconques.Count -eq 0) {
        $rng = New-Object System.Random $Graine
        $min = $AvantS; $max = [math]::Max($AvantS, $duree - $ApresS)
        $quelconques = 1..$NbInstants | ForEach-Object { [math]::Round($min + $rng.NextDouble() * ($max - $min), 3) }
    }
    # Chaque instant est teste tel quel, puis cale sur le temps exact de l'image visible a cet instant
    # (cas d'un evenement, qui est toujours date sur une image).
    $liste = foreach ($q in $quelconques) {
        [pscustomobject]@{ t = [double]$q; type = 'quelconque' }
        $k = Get-IndexAttendu $c ($c.debut_format_s + $q)
        # Arrondi a la microseconde inferieure pour ne pas demander un instant posterieur a l'image visee.
        [pscustomobject]@{ t = [math]::Floor(($imgs[$k].t_abs_s - $c.debut_format_s) * 1e6) / 1e6; type = 'image_exacte' }
    }

    $mesures = New-Object System.Collections.Generic.List[object]
    $ajouter = {
        param($methode, $tDemande, $tCibleAbs, $hash, $nbImagesExtrait, $nbImagesAttendues)
        $att = Get-IndexAttendu $c $tCibleAbs
        $r = Find-Image $index $hash $att
        $obt = $r.idx
        $mesures.Add([pscustomobject]@{
                methode = $methode; type_instant = $typeInstant; t_demande_s = Format-Temps $tDemande
                index_attendu = $att; index_obtenu = $obt; nb_candidats = $r.nb
                ecart_images = if ($null -ne $obt) { $obt - $att } else { $null }
                ecart_ms = if ($null -ne $obt) { [math]::Round(($imgs[$obt].t_abs_s - $imgs[$att].t_abs_s) * 1000) } else { $null }
                images_extrait = $nbImagesExtrait; images_attendues = $nbImagesAttendues
                statut = if ($null -eq $obt) { 'introuvable' } elseif ($r.nb -gt 1) { 'ambigu' } else { 'ok' }
            })
    }

    $ss = { param($x) Format-Temps $x }
    foreach ($instant in $liste) {
        $t = $instant.t; $typeInstant = $instant.type
        $tAbs = $c.debut_format_s + $t
        $h = Get-PremiereEmpreinte @('-ss', (& $ss $t), '-i', $chemin)
        & $ajouter 'vignette_ss_avant_entree' $t $tAbs $h $null $null
        if (-not $SansSeekSortie) {
            $h = Get-PremiereEmpreinte @('-i', $chemin, '-ss', (& $ss $t))
            & $ajouter 'vignette_ss_apres_entree' $t $tAbs $h $null $null
        }

        $debut = [math]::Max([double]0, $t - $AvantS); $dur = $AvantS + $ApresS
        $debutAbs = $c.debut_format_s + $debut
        $attendues = @($imgs | Where-Object { $_.t_abs_s -ge $debutAbs - 0.000001 -and $_.t_abs_s -lt $debutAbs + $dur - 0.000001 }).Count
        foreach ($mode in 'copie', 'reencode_sans_perte') {
            $fichier = Join-Path $dossier ("extrait_{0}_{1}_{2}.mkv" -f $mode, $typeInstant, ((& $ss $t) -replace '\.', '_'))
            $codec = if ($mode -eq 'copie') { @('-c', 'copy') } else { @('-c:v', 'ffv1') }
            try {
                Invoke-Outil ffmpeg (@('-hide_banner', '-loglevel', 'error', '-y', '-ss', (& $ss $debut), '-i', $chemin,
                        '-t', (& $ss $dur), '-map', '0:v:0') + $codec + @($fichier)) | Out-Null
                $nb = Invoke-Outil ffprobe @('-v', 'error', '-count_frames', '-select_streams', 'v:0',
                    '-show_entries', 'stream=nb_read_frames', '-of', 'default=nw=1:nk=1', $fichier) | Select-Object -First 1
                $h = Get-PremiereEmpreinte @('-i', $fichier)
            } catch {
                $nb = 'echec_extraction'; $h = $null
            }
            & $ajouter "extrait_$mode" $t $debutAbs $h $nb $attendues
        }
    }

    $mesures | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $dossier 'mesures.csv')
    $resume += ''
    $resume += 'methode, type d''instant | n | ok | ambigu | introuvable | ecart images min..max | ecart ms min..max'
    foreach ($g in ($mesures | Group-Object methode, type_instant)) {
        $vals = @($g.Group | Where-Object { $null -ne $_.ecart_images })
        $plage = { param($p) if ($vals.Count) { $m = $vals | Measure-Object -Property $p -Minimum -Maximum; "$($m.Minimum)..$($m.Maximum)" } else { 'n/a' } }
        $resume += '{0} | {1} | {2} | {3} | {4} | {5} | {6}' -f $g.Name, $g.Count,
        @($g.Group | Where-Object statut -eq 'ok').Count, @($g.Group | Where-Object statut -eq 'ambigu').Count,
        @($g.Group | Where-Object statut -eq 'introuvable').Count, (& $plage 'ecart_images'), (& $plage 'ecart_ms')
    }
    $resume | Set-Content -Encoding UTF8 (Join-Path $dossier 'resume.txt')
    $resume | Write-Host
}

$cibles = @($Video)
if ($GenererMires) { $cibles = (New-Mires) + $cibles }
if ($cibles.Count -eq 0) { throw 'Rien a controler : utiliser -GenererMires et/ou -Video <chemin>.' }
foreach ($v in $cibles) { Test-Video (Resolve-Path $v).Path }
