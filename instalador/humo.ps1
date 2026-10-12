<#
.SYNOPSIS
  Prueba de humo del instalador de Sílice (spec S5 §11.2; RF-97, RF-98, RNF-19).
.DESCRIPTION
  Corre en el runner de Windows (administrador) con el asistente de IA apagado. Bloquea la
  salida del python.exe de {app}, instala en una ruta con espacios y acentos, arranca, mide,
  actualiza con una base de la 0.5.0 sin migrar, prueba la red local y desinstala.
  Sale con 1 si algo falla.
.PARAMETER Instalador     Silice-<versión>[-completo].exe
.PARAMETER Actualizacion  El mismo build con la versión de parche +1 (construir.py --solo-iss)
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Instalador,
    [Parameter(Mandatory)][string]$Actualizacion,
    [Parameter(Mandatory)][string]$Version,
    [ValidateSet('basico', 'completo')][string]$Perfil = 'basico',
    [string]$Salida = 'humo-salida',
    [string]$Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Base = 'C:\Prueba Sílice'
$Programa = Join-Path $Base 'Programa ñ'
$Usuario = Join-Path $Base 'Usuario ñ'
$Datos = Join-Path $Usuario 'datos'
$Respaldos = Join-Path $Usuario 'respaldos'
$Codigo = Join-Path $Programa 'codigo'
$Python = Join-Path $Programa 'python\python.exe'
$Banderas = @('-E', '-s', '-B', '-X', 'utf8', '-m', 'operacion')
$PuertoProxy = 8899
$Url = 'http://127.0.0.1:8501'
$ReglaSalida = 'Silice humo: bloquear salida'
$Fallos = [System.Collections.Generic.List[string]]::new()
New-Item -ItemType Directory -Force -Path $Salida | Out-Null
$Salida = (Resolve-Path $Salida).Path
$env:SILICE_USUARIO = $Usuario
$env:SILICE_DATOS = $Datos
$env:SILICE_RESPALDOS = $Respaldos

function Afirmar([bool]$Condicion, [string]$Mensaje) {
    if ($Condicion) { Write-Host "ok: $Mensaje"; return }
    $Fallos.Add($Mensaje)
    Write-Host "FALLA: $Mensaje" -ForegroundColor Red
}
function Paso([string]$Texto) { Write-Host "`n== $Texto" -ForegroundColor Cyan }
function Contar($Objetos) { return @($Objetos | Where-Object { $null -ne $_ }).Count }
function Nombre([string]$Prefijo) {
    return Join-Path $Salida ($Prefijo + '-' + [guid]::NewGuid().ToString('N').Substring(0, 6))
}

function Operacion([string[]]$Argumentos) {
    $registro = Nombre 'op'
    $proceso = Start-Process -FilePath $Python -ArgumentList ($Banderas + $Argumentos) `
        -WorkingDirectory $Codigo -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput "$registro.out" -RedirectStandardError "$registro.err"
    return $proceso.ExitCode
}

function EsperarSalud([string]$Direccion, [int]$Limite = 60) {
    $reloj = [Diagnostics.Stopwatch]::StartNew()
    while ($reloj.Elapsed.TotalSeconds -lt $Limite) {
        try {
            $r = Invoke-WebRequest -Uri "$Direccion/_stcore/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { return [math]::Round($reloj.Elapsed.TotalSeconds, 2) }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

function Hijos([int]$Raiz) {
    $todos = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId
    $cola = [System.Collections.Generic.Queue[int]]::new()
    $vistos = [System.Collections.Generic.List[int]]::new()
    $cola.Enqueue($Raiz)
    while ($cola.Count -gt 0) {
        $actual = $cola.Dequeue()
        $vistos.Add($actual)
        $todos | Where-Object { $_.ParentProcessId -eq $actual } |
            ForEach-Object { $cola.Enqueue([int]$_.ProcessId) }
    }
    return $vistos.ToArray()
}
function Escuchas([int]$Raiz) {
    $pids = Hijos $Raiz
    return @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $pids -contains $_.OwningProcess })
}
function Escucha($Lista, [string]$Direccion, [int]$Puerto) {
    return Contar ($Lista | Where-Object {
        $_.LocalAddress -eq $Direccion -and $_.LocalPort -eq $Puerto })
}
function EnTodas($Lista) {
    return Contar ($Lista | Where-Object { $_.LocalAddress -in @('0.0.0.0', '::') })
}

function ArbolDe([string]$Carpeta) {
    Get-ChildItem -LiteralPath $Carpeta -Recurse -File -Force | Sort-Object FullName |
        ForEach-Object { '{0}|{1}' -f $_.FullName.Substring($Carpeta.Length), $_.Length }
}

function AEntero([string]$Ip) {
    $b = [System.Net.IPAddress]::Parse($Ip).GetAddressBytes()
    return ([uint32]$b[0] -shl 24) + ([uint32]$b[1] -shl 16) +
        ([uint32]$b[2] -shl 8) + [uint32]$b[3]
}
function ADecimal([uint32]$N) {
    $p = (($N -shr 24) -band 255), (($N -shr 16) -band 255), (($N -shr 8) -band 255), ($N -band 255)
    return $p -join '.'
}
function RangosSin([string]$Ip) {
    # Todo IPv4 salvo 127.0.0.0/8 y la IP propia: conectarse a la propia IP no es salir del equipo.
    $n = AEntero $Ip
    return @('0.0.0.0-126.255.255.255', ('128.0.0.0-' + (ADecimal ($n - 1))),
        ((ADecimal ($n + 1)) + '-255.255.255.255'))
}

function IniciarSilice {
    $env:HTTP_PROXY = "http://127.0.0.1:$PuertoProxy"
    $env:HTTPS_PROXY = $env:HTTP_PROXY
    $env:NO_PROXY = '127.0.0.1,localhost'
    try {
        $registro = Nombre 'arrancar'
        return Start-Process -FilePath $Python -PassThru -WindowStyle Hidden `
            -ArgumentList ($Banderas + @('arrancar', '--sin-navegador')) `
            -WorkingDirectory $Codigo `
            -RedirectStandardOutput "$registro.out" -RedirectStandardError "$registro.err"
    } finally {
        Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:NO_PROXY -ErrorAction SilentlyContinue
    }
}

function InstalarSilencioso([string]$Exe, [string]$Registro) {
    $argumentos = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER',
        "/DIR=`"$Programa`"", "/LOG=`"$Registro`"")
    if ($Perfil -eq 'completo') {
        $argumentos += '/COMPONENTS="programa,demostracion,similitud"'
    }
    return (Start-Process -FilePath $Exe -ArgumentList $argumentos -Wait -PassThru).ExitCode
}

function DescartesDe([string]$Registro, [string[]]$Pids) {
    if (-not (Test-Path $Registro)) { return @() }
    $lineas = Get-Content $Registro
    $cabecera = $lineas | Where-Object { $_ -like '#Fields:*' } | Select-Object -Last 1
    $campos = ($cabecera -replace '^#Fields:\s*', '') -split '\s+'
    if ($campos -notcontains 'pid') { return @() }
    $filas = foreach ($linea in ($lineas | Where-Object { $_ -and $_ -notlike '#*' })) {
        $valores = $linea -split ' '
        $fila = @{}
        for ($i = 0; $i -lt [math]::Min($campos.Count, $valores.Count); $i++) {
            $fila[$campos[$i]] = $valores[$i]
        }
        [pscustomobject]$fila
    }
    return @($filas | Where-Object {
        $_.action -eq 'DROP' -and $Pids -contains $_.pid -and $_.'dst-ip' -notmatch '^(127\.|::1)'
    })
}

$Muestreo = {
    param($programa, $archivo)
    while ($true) {
        $pids = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($programa) } |
            ForEach-Object { $_.ProcessId })
        if ($pids.Count) {
            $pids | ForEach-Object { "pid $_" } | Add-Content -Path "$archivo.pids"
            Get-NetTCPConnection -ErrorAction SilentlyContinue |
                Where-Object { $pids -contains $_.OwningProcess -and $_.State -ne 'Listen' } |
                ForEach-Object {
                    $local = "$($_.LocalAddress):$($_.LocalPort)"
                    $remoto = "$($_.RemoteAddress):$($_.RemotePort)"
                    "$($_.OwningProcess) $($_.State) $local $remoto"
                } | Add-Content -Path $archivo
        }
        Start-Sleep -Seconds 1
    }
}

$servidor = $null; $proxy = $null; $trabajo = $null; $ip = $null
try {
    Paso '1. Cortafuegos de salida y proxy testigo'
    New-NetFirewallRule -DisplayName $ReglaSalida -Direction Outbound -Action Block `
        -Program $Python -Profile Any | Out-Null
    $registroFw = Join-Path $Salida 'pfirewall.log'
    Set-NetFirewallProfile -Profile Domain, Private, Public -LogBlocked True `
        -LogFileName $registroFw -LogMaxSizeKilobytes 16384
    $proxy = Start-Process -FilePath python -PassThru -WindowStyle Hidden -ArgumentList @(
        (Join-Path $Raiz 'instalador\proxy_testigo.py'), '--puerto', $PuertoProxy,
        '--registro', (Join-Path $Salida 'proxy.log'))

    Paso '2. Instalación silenciosa en una ruta con espacios y acentos'
    $codigo = InstalarSilencioso $Instalador (Join-Path $Salida 'instalacion.log')
    Afirmar ($codigo -eq 0) "el instalador terminó con 0 (fue $codigo)"
    Afirmar (Test-Path $Python) 'python.exe quedó en la ruta con espacios y ñ'
    $bases = (Test-Path (Join-Path $Datos 'instalacion.db')) -and
        (Test-Path (Join-Path $Datos 'casos\silice.db'))
    Afirmar $bases 'las dos bases nacieron en la carpeta de datos'

    Paso '3. Inventario y manifiesto'
    Afirmar ((Operacion @('verificar-programa')) -eq 0) '{app}\codigo coincide con manifiesto.json'
    $configs = @(Get-ChildItem -LiteralPath $Codigo -Recurse -Filter 'config.toml' -File)
    $unico = $configs.Count -eq 1 -and $configs[0].FullName.EndsWith('.streamlit\config.toml')
    Afirmar $unico 'hay un único .streamlit\config.toml'
    $ajustes = Join-Path $Usuario 'config'
    New-Item -ItemType Directory -Force -Path $ajustes | Out-Null
    Set-Content -Path (Join-Path $ajustes 'silice.toml') -Encoding utf8 `
        -Value "[servidor]`npuerto = 8501`n[interfaz]`nmostrar_investigacion = true`n"
    $antes = ArbolDe $Programa

    Paso '4. Arranque, salud y puertos'
    $trabajo = Start-Job -ScriptBlock $Muestreo `
        -ArgumentList $Programa, (Join-Path $Salida 'conexiones.log')
    $servidor = IniciarSilice
    $segundos = EsperarSalud $Url 60
    Afirmar ($null -ne $segundos) "la salud respondió 200 en <= 60 s (fueron $segundos s)"
    @{ salud_s = $segundos; perfil = $Perfil; version = $Version } | ConvertTo-Json |
        Set-Content (Join-Path $Salida 'tiempos.json')
    $escuchas = Escuchas $servidor.Id
    Afirmar ((Escucha $escuchas '127.0.0.1' 8501) -ge 1) 'el 8501 escucha en 127.0.0.1'
    Afirmar ((EnTodas $escuchas) -eq 0) 'nada de Sílice escucha en 0.0.0.0 ni en ::'
    $api = Contar ($escuchas | Where-Object { $_.LocalPort -eq 8000 })
    Afirmar ($api -eq 0) 'el 8000 (API) no escucha'

    Paso '5. Navegador sin interfaz'
    $navegador = Join-Path $Raiz 'instalador\navegador.py'
    & uv run --no-project --with playwright python $navegador --url $Url `
        --salida (Join-Path $Salida 'peticiones.json')
    Afirmar ($LASTEXITCODE -eq 0) 'el navegador no pidió nada fuera de 127.0.0.1 (ni telemetría)'
    if ($Perfil -eq 'completo') {
        $modelo = Operacion @('diagnostico-similitud')
        Afirmar ($modelo -eq 0) 'el modelo de similitud carga sin red'
    }

    Paso '6. Parada, puerto libre e inventario sin cambios'
    Afirmar ((Operacion @('parar')) -eq 0) 'operacion parar terminó con 0'
    Start-Sleep -Seconds 2
    Afirmar ($null -eq (EsperarSalud $Url 3)) 'el puerto quedó libre'
    $despues = ArbolDe $Programa
    Afirmar (-not (Compare-Object $antes $despues)) 'nada se escribió en la carpeta del programa'
    $peticiones = Get-Content (Join-Path $Salida 'proxy.log') -ErrorAction SilentlyContinue
    Afirmar ((Contar $peticiones) -eq 0) 'el proxy testigo anotó 0 peticiones'

    Paso '7. Actualización con Sílice en marcha y bases viejas sin migrar'
    $casos = Join-Path $Datos 'casos'
    New-Item -ItemType Directory -Force -Path $casos | Out-Null
    $bases = Join-Path $Raiz 'tests\fixtures\bases'
    Copy-Item (Join-Path $bases 'v0_5_0\demo.db') (Join-Path $casos 'v050_demo.db')
    Copy-Item (Join-Path $bases 'v0_9_0\demo.db') (Join-Path $casos 'v090_demo.db')
    $servidor = IniciarSilice
    Afirmar ($null -ne (EsperarSalud $Url 60)) 'Sílice arrancó antes de actualizar'
    $codigo = InstalarSilencioso $Actualizacion (Join-Path $Salida 'actualizacion.log')
    Afirmar ($codigo -eq 0) "la actualización terminó con 0 (fue $codigo)"
    Afirmar ($null -eq (EsperarSalud $Url 3)) 'el instalador detuvo Sílice antes de copiar'
    $juegos = @(Get-ChildItem -LiteralPath $Respaldos -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName 'ficha.json') })
    Afirmar ($juegos.Count -ge 1) 'existe un juego de respaldo con su ficha'
    & uv run python (Join-Path $Raiz 'instalador\verificar_bases.py') --casos $casos `
        --par '0.5.0:demo.db=v050_demo.db' --par '0.9.0:demo.db=v090_demo.db'
    Afirmar ($LASTEXITCODE -eq 0) 'las dos bases están en head y cuadran con su ficha'

    Paso '8. Red local en la IP de la interfaz'
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)' } |
        Select-Object -First 1).IPAddress
    Afirmar ($null -ne $ip) 'el runner tiene una interfaz con dirección privada'
    if ($ip) {
        Set-NetFirewallRule -DisplayName $ReglaSalida -RemoteAddress (RangosSin $ip)
        Afirmar ((Operacion @('red-local', 'activar', '--ip', $ip, '--si')) -eq 0) "activar en $ip"
        $filtros = Get-NetFirewallRule -DisplayName 'Silice red local*' |
            Get-NetFirewallApplicationFilter
        $conPrograma = Contar ($filtros | Where-Object { $_.Program -eq $Python })
        Afirmar ($conPrograma -ge 1) 'la regla apunta al python.exe de la ruta con espacios y ñ'
        $servidor = IniciarSilice
        Afirmar ($null -ne (EsperarSalud "http://${ip}:8501" 60)) 'la salud responde por esa IP'
        $escuchas = Escuchas $servidor.Id
        Afirmar ((Escucha $escuchas $ip 8501) -ge 1) 'escucha solo en esa IP'
        Afirmar ((EnTodas $escuchas) -eq 0) 'nunca en 0.0.0.0'
        Afirmar ($null -eq (EsperarSalud $Url 3)) 'ya no responde en 127.0.0.1'
        Operacion @('parar') | Out-Null
        Afirmar ((Operacion @('red-local', 'desactivar')) -eq 0) 'red-local desactivar'
        $quedan = Get-NetFirewallRule -DisplayName 'Silice red local*' -ErrorAction SilentlyContinue
        Afirmar ((Contar $quedan) -eq 0) 'las reglas del cortafuegos se borraron'
    }

    Paso '9. Ninguna conexión saliente en toda la corrida'
    Stop-Job $trabajo -ErrorAction SilentlyContinue
    $conexiones = Get-Content (Join-Path $Salida 'conexiones.log') -ErrorAction SilentlyContinue
    $propias = if ($ip) { '|' + [regex]::Escape($ip) } else { '' }
    $locales = '^(127\.0\.0\.1|::1|0\.0\.0\.0|::|\[::\]' + $propias + '):'
    $ajenas = @($conexiones | Where-Object { $_ -and ($_ -split ' ')[3] -notmatch $locales })
    Afirmar ($ajenas.Count -eq 0) "el muestreo no vio conexiones ajenas ($($ajenas.Count))"
    $vistos = Get-Content (Join-Path $Salida 'conexiones.log.pids') -ErrorAction SilentlyContinue |
        ForEach-Object { ($_ -split ' ')[1] } | Sort-Object -Unique
    $descartes = DescartesDe $registroFw $vistos
    Afirmar ((Contar $descartes) -eq 0) 'el cortafuegos no descartó nada de Sílice hacia fuera'

    Paso '10. Desinstalación: el programa se va y los datos quedan'
    $desinstalador = Join-Path $Programa 'unins000.exe'
    Start-Process -FilePath $desinstalador -Wait `
        -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'
    $limite = (Get-Date).AddSeconds(60)
    while ((Test-Path $Programa) -and (Get-Date) -lt $limite) { Start-Sleep -Seconds 2 }
    Afirmar (-not (Test-Path $Programa)) '{app} ya no existe'
    $quedan = (Test-Path (Join-Path $Datos 'instalacion.db')) -and (Test-Path $casos) -and
        (Test-Path $Respaldos)
    Afirmar $quedan 'la carpeta de datos y sus respaldos siguen ahí'
}
finally {
    if ($trabajo) { Stop-Job $trabajo -ErrorAction SilentlyContinue }
    if ($trabajo) { Remove-Job $trabajo -Force -ErrorAction SilentlyContinue }
    if ($proxy) { Stop-Process -Id $proxy.Id -Force -ErrorAction SilentlyContinue }
    Remove-NetFirewallRule -DisplayName $ReglaSalida -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName 'Silice red local*' -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
}
Write-Host "`nFallos: $($Fallos.Count)"
$Fallos | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
exit ([int]($Fallos.Count -gt 0))
