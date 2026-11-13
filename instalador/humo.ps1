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
$UrlApp = "$Url/app"
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
            $r = Invoke-WebRequest -Uri "$Direccion/salud" -UseBasicParsing -TimeoutSec 2
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

function JuegosDe([string]$Carpeta) {
    # Los juegos de respaldo con su ficha.json (operacion.respaldo): carpeta, motivo y bases
    Get-ChildItem -LiteralPath $Carpeta -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $ficha = Join-Path $_.FullName 'ficha.json'
        if (-not (Test-Path -LiteralPath $ficha)) { return }
        $contenido = Get-Content -LiteralPath $ficha -Raw -Encoding utf8 | ConvertFrom-Json
        [pscustomobject]@{
            nombre = $_.Name
            motivo = $contenido.motivo
            archivos = @($contenido.bases | ForEach-Object { $_.archivo })
        }
    }
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
    # Dos tramos (0.0.0.0-126.255.255.255 y 128.0.0.0-255.255.255.255) menos la IP, estén donde
    # estén: Set-NetFirewallRule rechaza un rango con el final menor que el inicio.
    $n = AEntero $Ip
    $salida = @()
    foreach ($tramo in @(@([uint32]0, [uint32]2130706431), @([uint32]2147483648, [uint32]4294967295))) {
        $desde = [uint32]$tramo[0]
        $hasta = [uint32]$tramo[1]
        if ($n -lt $desde -or $n -gt $hasta) {
            $salida += ((ADecimal $desde) + '-' + (ADecimal $hasta))
            continue
        }
        if ($n -gt $desde) { $salida += ((ADecimal $desde) + '-' + (ADecimal ($n - 1))) }
        if ($n -lt $hasta) { $salida += ((ADecimal ($n + 1)) + '-' + (ADecimal $hasta)) }
    }
    return $salida
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

function IniciarVentana([string]$Registro) {
    # El puerto de depuración lo abre la política de HKLM (PonerPoliticaCdp), no una variable: el
    # proceso es elevado y WebView2 ignora ahí sus variables de entorno.
    $env:HTTP_PROXY = "http://127.0.0.1:$PuertoProxy"
    $env:HTTPS_PROXY = $env:HTTP_PROXY
    $env:NO_PROXY = '127.0.0.1,localhost'
    try {
        # -NoNewWindow: sin consola propia, la ventana principal del proceso es la de Sílice
        return Start-Process -FilePath $Python -PassThru -NoNewWindow `
            -ArgumentList ($Banderas + @('arrancar')) `
            -WorkingDirectory $Codigo `
            -RedirectStandardOutput "$Registro.out" -RedirectStandardError "$Registro.err"
    } finally {
        Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:NO_PROXY -ErrorAction SilentlyContinue
    }
}

# La humo corre elevada y, desde el runtime 150, WebView2 ignora en un proceso elevado la variable
# WEBVIEW2_* y la política de HKCU («Develop secure WebView2 apps», Microsoft): solo la de HKLM.
$PoliticaCdp = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments'
$script:PoliticaPrevia = $null
$script:TipoPrevio = 'String'
$script:ClaveCreada = $false
function ValorPoliticaCdp {
    if (-not (Test-Path -Path $PoliticaCdp)) { return $null }
    return (Get-Item -Path $PoliticaCdp).GetValue('python.exe', $null, 'DoNotExpandEnvironmentNames')
}
function PonerPoliticaCdp([int]$PuertoCdp) {
    # La política de máquina que documenta Microsoft para lo mismo que la variable: un valor con el
    # nombre del ejecutable. Solo durante el paso 6b; QuitarPoliticaCdp deja la clave como estaba.
    # New-Item -Force sobre una clave que ya existe la recrea vacía (borra sus otros valores y
    # subclaves): solo se crea si falta.
    if (-not (Test-Path -Path $PoliticaCdp)) {
        New-Item -Path $PoliticaCdp -Force | Out-Null
        $script:ClaveCreada = $true
    }
    $clave = Get-Item -Path $PoliticaCdp
    $script:PoliticaPrevia = $clave.GetValue('python.exe', $null, 'DoNotExpandEnvironmentNames')
    if ($null -ne $script:PoliticaPrevia) {
        $script:TipoPrevio = [string]$clave.GetValueKind('python.exe')
        Write-Host "  la política ya tenía un valor python.exe: se devuelve al terminar"
    }
    New-ItemProperty -Path $PoliticaCdp -Name 'python.exe' -PropertyType String -Force `
        -Value "--remote-debugging-port=$PuertoCdp" | Out-Null
}
function QuitarPoliticaCdp {
    # Idempotente: el paso 6b y el finally la llaman
    if (-not (Test-Path -Path $PoliticaCdp)) { return }
    if ($null -ne $script:PoliticaPrevia) {
        New-ItemProperty -Path $PoliticaCdp -Name 'python.exe' -PropertyType $script:TipoPrevio `
            -Force -Value $script:PoliticaPrevia | Out-Null
        return
    }
    Remove-ItemProperty -Path $PoliticaCdp -Name 'python.exe' -ErrorAction SilentlyContinue
    if ($script:ClaveCreada) {
        # La creó la humo: se va si quedó vacía (las claves padre vacías no estorban)
        $clave = Get-Item -Path $PoliticaCdp
        if ($clave.ValueCount -eq 0 -and $clave.SubKeyCount -eq 0) { Remove-Item -Path $PoliticaCdp }
        $script:ClaveCreada = $false
    }
}

function PuertoLibre {
    # Windows da un puerto libre fuera de los rangos reservados (Hyper-V en windows-2025): con uno
    # fijo, Chromium no abre el de depuración y no avisa.
    $escucha = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $escucha.Start()
    try { return $escucha.LocalEndpoint.Port } finally { $escucha.Stop() }
}

function EsperarCdp([int]$Puerto, [int]$Limite = 60) {
    $reloj = [Diagnostics.Stopwatch]::StartNew()
    while ($reloj.Elapsed.TotalSeconds -lt $Limite) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Puerto/json/version" `
                -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { return [math]::Round($reloj.Elapsed.TotalSeconds, 2) }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    return $null
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

$servidor = $null; $ventana = $null; $proxy = $null; $trabajo = $null; $ip = $null
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
    $salidaInstalador = InstalarSilencioso $Instalador (Join-Path $Salida 'instalacion.log')
    Afirmar ($salidaInstalador -eq 0) "el instalador terminó con 0 (fue $salidaInstalador)"
    Afirmar (Test-Path $Python) 'python.exe quedó en la ruta con espacios y ñ'
    # La instalación crea instalacion.db (orden migrar) y el caso de demostración (orden
    # demostracion); el caso por defecto lo crea el lanzador al primer arranque (spec S5 §5.4, paso 4).
    $bases = (Test-Path (Join-Path $Datos 'instalacion.db')) -and
        (Test-Path (Join-Path $Datos 'casos\demostracion.db'))
    if (-not $bases) {
        Get-ChildItem -LiteralPath $Usuario -Recurse -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty FullName | Set-Content (Join-Path $Salida 'datos.txt')
    }
    Afirmar $bases 'la base de la instalación y el caso de demostración nacieron en la carpeta de datos'

    Paso '3. Inventario y manifiesto'
    Afirmar ((Operacion @('verificar-programa')) -eq 0) '{app}\codigo coincide con manifiesto.json'
    $residuos = @((Join-Path $Codigo 'ui'), (Join-Path $Codigo '.streamlit')) |
        Where-Object { Test-Path $_ }
    Afirmar (@($residuos).Count -eq 0) 'no viaja ninguna carpeta ui ni .streamlit'
    Afirmar (Test-Path (Join-Path $Codigo 'frontend-desktop\dist\index.html')) 'la interfaz compilada viaja con el programa'
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
    Afirmar (Test-Path (Join-Path $Datos 'casos\silice.db')) 'el arranque creó el caso por defecto'
    @{ salud_s = $segundos; perfil = $Perfil; version = $Version } | ConvertTo-Json |
        Set-Content (Join-Path $Salida 'tiempos.json')
    $escuchas = Escuchas $servidor.Id
    Afirmar ((Escucha $escuchas '127.0.0.1' 8501) -ge 1) 'el 8501 escucha en 127.0.0.1'
    Afirmar ((EnTodas $escuchas) -eq 0) 'nada de Sílice escucha en 0.0.0.0 ni en ::'
    $otros = Contar ($escuchas | Where-Object { $_.LocalPort -ne 8501 })
    Afirmar ($otros -eq 0) 'un solo puerto: el 8501 sirve la API y la interfaz, y no escucha ningún otro'
    $app = Invoke-WebRequest -Uri "$UrlApp/" -UseBasicParsing -TimeoutSec 5
    Afirmar ($app.StatusCode -eq 200 -and $app.Content -match '/app/assets/') '/app/ entrega la interfaz de React (index.html con sus recursos)'

    Paso '5. Navegador sin interfaz'
    $navegador = Join-Path $Raiz 'instalador\navegador.py'
    & uv run --no-project --with playwright python $navegador --url $UrlApp `
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

    Paso '6b. Ventana de Sílice: WebView2 por CDP, sin red, primer administrador, descarga y cierre'
    $puertoCdp = PuertoLibre
    $regVentana = Nombre 'ventana'
    PonerPoliticaCdp $puertoCdp
    $ventana = IniciarVentana $regVentana
    $segVentana = EsperarSalud $Url 60
    Afirmar ($null -ne $segVentana) "la salud con ventana respondió 200 en <= 60 s (fueron $segVentana s)"
    $segCdp = EsperarCdp $puertoCdp 60
    Afirmar ($null -ne $segCdp) "CDP respondió en el $puertoCdp en <= 60 s (fueron $segCdp s)"
    if ($null -eq $segCdp) {
        # Diagnóstico: con qué orden arrancó WebView2 y qué puertos tiene reservados Windows
        Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" |
            Where-Object { $_.CommandLine -match 'remote-debugging|perfil_ventana' } |
            Select-Object -First 3 | ForEach-Object { Write-Host "  webview2: $($_.CommandLine)" }
        netsh int ipv4 show excludedportrange protocol=tcp | ForEach-Object { Write-Host "  $_" }
        foreach ($raiz in @('HKLM:\SOFTWARE\Policies\Microsoft\Edge', 'HKCU:\Software\Policies\Microsoft\Edge')) {
            Get-ChildItem -Path $raiz -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
                Write-Host "  politica: $($_.Name) $(($_.Property | ForEach-Object { $_ }) -join ', ')"
            }
        }
    }
    & uv run --no-project --with playwright python $navegador --url $UrlApp `
        --cdp "http://127.0.0.1:$puertoCdp" `
        --codigo (Join-Path $Datos 'codigo_instalacion.txt') `
        --salida (Join-Path $Salida 'ventana-peticiones.json')
    Afirmar ($LASTEXITCODE -eq 0) 'la ventana no pidió nada fuera de 127.0.0.1 y bajó el respaldo'
    $ventana.Refresh()
    Afirmar ($ventana.MainWindowTitle -eq 'Sílice') "título de la ventana = 'Sílice' (fue '$($ventana.MainWindowTitle)')"
    Afirmar ($ventana.CloseMainWindow()) 'CloseMainWindow() aceptó el cierre de la ventana'
    Afirmar ($ventana.WaitForExit(30000)) 'el lanzador terminó en <= 30 s al cerrar la ventana'
    QuitarPoliticaCdp
    $valorRestante = ValorPoliticaCdp
    Afirmar ($script:PoliticaPrevia -eq $valorRestante) "la política de HKLM volvió a como estaba (python.exe = '$valorRestante')"
    Afirmar ($null -eq (EsperarSalud $Url 3)) 'el puerto quedó libre tras cerrar la ventana'
    Afirmar (-not (Test-Path (Join-Path $Usuario 'estado\servidor.json'))) 'estado\servidor.json se borró'
    # Python guarda en búfer la salida a un archivo: se lee cuando el lanzador ya terminó
    $textoVentana = [string](Get-Content "$regVentana.out" -Raw -Encoding utf8 -ErrorAction SilentlyContinue)
    # El aviso tiene que nombrar la política que abrió el puerto (operacion.ventana y el lanzador)
    $avisoPolitica = 'AVISO: La política HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments (valor «python.exe») pide un puerto de depuración'
    Afirmar ($textoVentana -match 'puerto de depuración') 'el lanzador avisó que algo pide un puerto de depuración'
    Afirmar ($textoVentana.Contains($avisoPolitica)) 'el aviso del lanzador nombra la política de HKLM con el valor «python.exe»'
    Afirmar ($textoVentana -match 'Se cerró la ventana de Sílice') 'el lanzador registró «Se cerró la ventana de Sílice»'
    $vivosVentana = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Programa) })
    Afirmar ($vivosVentana.Count -eq 0) 'ningún python.exe de {app} sigue vivo tras cerrar la ventana'
    Afirmar (-not (Compare-Object $antes (ArbolDe $Programa))) 'la ventana no escribió en {app}'

    Paso '7. Actualización con Sílice en marcha y bases viejas sin migrar'
    $casos = Join-Path $Datos 'casos'
    New-Item -ItemType Directory -Force -Path $casos | Out-Null
    $bases = Join-Path $Raiz 'tests\fixtures\bases'
    Copy-Item (Join-Path $bases 'v0_5_0\demo.db') (Join-Path $casos 'v050_demo.db')
    Copy-Item (Join-Path $bases 'v1_0_0\demo.db') (Join-Path $casos 'v100_demo.db')
    $servidor = IniciarSilice
    Afirmar ($null -ne (EsperarSalud $Url 60)) 'Sílice arrancó antes de actualizar'
    # El 6b dejó un juego manual en la misma carpeta (la descarga del respaldo): cuentan solo los
    # juegos que nacen con la actualización, y entre ellos tiene que estar el de la orden migrar.
    $juegosAntes = JuegosDe $Respaldos | ForEach-Object { $_.nombre }
    $salidaActualizacion = InstalarSilencioso $Actualizacion (Join-Path $Salida 'actualizacion.log')
    Afirmar ($salidaActualizacion -eq 0) "la actualización terminó con 0 (fue $salidaActualizacion)"
    Afirmar ($null -eq (EsperarSalud $Url 3)) 'el instalador detuvo Sílice antes de copiar'
    $nuevos = @(JuegosDe $Respaldos | Where-Object { $juegosAntes -notcontains $_.nombre })
    $migracion = @($nuevos | Where-Object {
        $_.motivo -eq 'migracion' -and (@($_.archivos) -like '*v050_demo.db').Count -ge 1 })
    Afirmar ($migracion.Count -eq 1) "la actualización dejó un juego nuevo de migración con la base de la 0.5.0 en su ficha ($($nuevos.Count) juegos nuevos: $(($nuevos | ForEach-Object { $_.nombre }) -join ', '))"
    & uv run python (Join-Path $Raiz 'instalador\verificar_bases.py') --casos $casos `
        --par '0.5.0:demo.db=v050_demo.db' --par '1.0.0:demo.db=v100_demo.db'
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
        -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
        "/LOG=`"$(Join-Path $Salida 'desinstalar.log')`""
    $limite = (Get-Date).AddSeconds(60)
    $inicioBaja = Get-Date
    while ((Test-Path $Programa) -and (Get-Date) -lt $limite) { Start-Sleep -Seconds 2 }
    if (Test-Path $Programa) {
        # Diagnóstico: qué quedó, quién lo sostiene y si el desinstalador sigue en marcha.
        $resto = @(Get-ChildItem $Programa -Recurse -Force -ErrorAction SilentlyContinue)
        Write-Host "  quedan $($resto.Count) entradas en {app} tras $([int]((Get-Date) - $inicioBaja).TotalSeconds) s"
        $resto | Select-Object -First 40 | ForEach-Object {
            Write-Host "    $($_.FullName.Substring($Programa.Length))"
        }
        Get-CimInstance Win32_Process | Where-Object {
            ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($Programa)) -or
            ($_.Name -like '_iu*') -or ($_.Name -like 'unins*')
        } | ForEach-Object { Write-Host "    proceso vivo: $($_.ProcessId) $($_.Name) $($_.ExecutablePath)" }
        Get-Content (Join-Path $Salida 'desinstalar.log') -ErrorAction SilentlyContinue |
            Where-Object { $_ -match 'codigo\\?\s*$|codigo"|Failed|failed|error|Error|Deleting directory' } |
            Select-Object -Last 40 | ForEach-Object { Write-Host "    registro: $_" }
    }
    Afirmar (-not (Test-Path $Programa)) '{app} ya no existe'
    $quedan = (Test-Path (Join-Path $Datos 'instalacion.db')) -and (Test-Path $casos) -and
        (Test-Path $Respaldos)
    Afirmar $quedan 'la carpeta de datos y sus respaldos siguen ahí'
}
finally {
    if ($trabajo) { Stop-Job $trabajo -ErrorAction SilentlyContinue }
    if ($trabajo) { Remove-Job $trabajo -Force -ErrorAction SilentlyContinue }
    QuitarPoliticaCdp
    if ($ventana -and -not $ventana.HasExited) {
        Stop-Process -Id $ventana.Id -Force -ErrorAction SilentlyContinue
    }
    if ($proxy) { Stop-Process -Id $proxy.Id -Force -ErrorAction SilentlyContinue }
    Remove-NetFirewallRule -DisplayName $ReglaSalida -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName 'Silice red local*' -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
}
Write-Host "`nFallos: $($Fallos.Count)"
$Fallos | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
exit ([int]($Fallos.Count -gt 0))
