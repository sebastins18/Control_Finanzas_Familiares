"""Verifica y empaqueta evidencias ya ejecutadas; no ejecuta operaciones financieras."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def stamp(seconds):
    seconds = max(0,int(seconds))
    return f'{seconds//60:02d}:{seconds%60:02d}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',default='evidencias/s4')
    parser.add_argument('--support',required=True)
    parser.add_argument('--public',required=True)
    parser.add_argument('--zip',default='evidencias/MisFinanzas_S4_Evidencias.zip')
    args = parser.parse_args()
    out = Path(args.evidence).resolve()
    report = out/'reportes'
    result = json.loads((report/'resultados.json').read_text(encoding='utf-8'))
    assert len(result['pruebas'])==27 and result['conteo']==dict(APROBADA=27,FALLIDA=0,OMITIDA=0), 'No se empaqueta como entrega final una ejecución E2E incompleta.'
    for name in ('regresion.txt','instalacion.txt','instalacion_limpia.md','comprobaciones_adicionales.json'):
        shutil.copyfile(Path(args.support)/name,report/name)
    shutil.copyfile(args.public,report/'login_publico.json')
    additional = json.loads((report/'comprobaciones_adicionales.json').read_text(encoding='utf-8'))
    public = json.loads((report/'login_publico.json').read_text(encoding='utf-8'))
    assert all(r['estado']=='APROBADA' for r in additional['pruebas'])
    assert additional['pruebas'][0]['tests']==109

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = out/'video'/'MisFinanzas_S4.mp4'
    frames = imageio_ffmpeg.read_frames(str(mp4))
    info = next(frames)
    frames.close()
    assert tuple(info['size'])==(1280,720) and 180<=info['duration']<=300, info
    subprocess.run([ffmpeg,'-v','error','-i',str(mp4),'-f','null','-'],check=True,capture_output=True,timeout=180)
    scenes = json.loads((report/'escenas.json').read_text(encoding='utf-8'))
    shots = [f'{i:02d}_{name}.png' for i,name in enumerate([
        'login','dashboard','crear_ingreso','crear_gasto','editar_movimiento','eliminar_movimiento',
        'presupuestos','alerta_80','alerta_100','historial','reporte_anual','validacion_error'],1)]
    assert all((out/'capturas'/s).is_file() for s in shots)
    frame_dir = report/'verificacion_video'
    frame_dir.mkdir(exist_ok=True)
    for index in (0,2,4,8,9,10,11,14,len(scenes)-1):
        at = min(scenes[index]['inicio']+3,info['duration']-1)
        dest = frame_dir/f"frame_{stamp(at).replace(':','-')}.png"
        subprocess.run([ffmpeg,'-v','error','-ss',str(at),'-i',str(mp4),'-frames:v','1','-update','1','-y',str(dest)],check=True,capture_output=True,timeout=30)
    verification = dict(fecha=datetime.now(timezone(timedelta(hours=-6))).isoformat(timespec='seconds'),
                        mp4_decodificado_completo=True,duracion_segundos=info['duration'],
                        resolucion=info['size'],codec=info['codec'],fps=info['fps'],
                        capturas_requeridas=len(shots),capturas_presentes=len(shots),
                        escenas=len(scenes),fotogramas_extraidos=9,db_en_entregables=False)
    (report/'VERIFICACION_ARCHIVOS.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')

    lines = ['# Correspondencia académica S1–S4', '',
        'Fecha de evidencia: '+result['entorno']['fecha']+'; commit '+result['entorno']['commit']+'.', '',
        '| Seguimiento | Evidencia nueva verificable | Pruebas / archivos | Alcance y pendientes |',
        '|---|---|---|---|',
        '| S1 | Estructura y arquitectura vigente; Python HTTP, SQLite y 17 tablas de aplicación | Revisión de src/, scripts/, tests/, docs/ y archivos solicitados; E03, E27; RESUMEN.md | Corrobora el estado actual. No acredita retrospectivamente la entrega histórica, propuesta aprobada, autoría ni participación individual. |',
        '| S2 | CRUD por formularios; importes en centavos; presupuesto y alertas; carga sintética local | E04–E18; capturas 03–10; comprobaciones_adicionales.json | La carga de 1.000 es una comprobación auxiliar fuera del navegador y sobre otra DB temporal. |',
        '| S3 | Valores inválidos, filtros, controles de acceso y contraste SQLite de escrituras y CSV | E06–E07, E09–E15, E17–E27; CSV; regresion.txt | No se repitió el benchmark de 100k ni se midió WAL frente a DELETE. Los errores de conexión y rollback se ejercitan en la suite existente, no mediante fallos forzados en este video. |',
        '| S4 | 27 comprobaciones E2E reales; 109 pruebas de regresión; instalación automática; video y capturas auténticas | playwright.html; instalacion_limpia.md; video/; capturas/; GUION_PRESENTACION.md | Instalación por otro integrante, acta, revisión del grupo, tags, publicación del video y evaluación docente siguen pendientes. |',
        '', 'La tabla de cada caso y su correspondencia S1–S4 está en RESUMEN.md y playwright.html. Las bitácoras históricas conservan sus resultados anteriores.']
    (report/'MATRIZ_S1_S4.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    narration = [
        'MisFinanzas organiza ingresos y gastos familiares con Python, HTML, CSS y SQLite. Esta demostración usa una instancia local, datos ficticios y un navegador real controlado por Playwright.',
        'Iniciamos sesión con la cuenta ficticia y elegimos su perfil financiero. La contraseña permanece enmascarada. Los permisos del perfil se gestionan separadamente del acceso de la cuenta.',
        'El panel muestra saldos, movimientos y planificación. Partimos sin movimientos para poder atribuir cada cambio a las operaciones de esta demostración.',
        'Consultamos las cuentas desde el menú. Trabajamos en colones. Después creamos, editamos y eliminamos una categoría temporal, y preparamos otra para el presupuesto.',
        'Registramos un ingreso ficticio de mil colones. La suite comprueba el movimiento en pantalla y verifica que SQLite guarda cien mil centavos.',
        'Agregamos un gasto de veinticinco colones en alimentación. La aplicación guarda los importes en centavos enteros y permite consultar inmediatamente el resultado.',
        'Editamos el gasto a treinta y cinco colones y cambiamos su descripción. La suite contrasta ambos campos de la interfaz con SQLite.',
        'Eliminamos el gasto y comprobamos que desaparece de la pantalla y de la base. El ingreso permanece registrado.',
        'Creamos un presupuesto de cien colones para una categoría sin gastos anteriores. Esto permite comprobar los umbrales con importes exactos.',
        'Con ochenta colones aparece Cerca del límite: es exactamente el ochenta por ciento. SQLite conserva la alerta correspondiente.',
        'Agregamos veinte colones. El total llega a cien y cambia a Excedido. Se comprueban las alertas del ochenta y cien por ciento.',
        'El historial muestra tres movimientos: un ingreso de mil y dos gastos que suman cien. Los totales están separados por moneda.',
        'Combinamos búsqueda, tipo, categoría, cuenta y fechas. Queda el gasto de ochenta colones. El CSV descargado respeta el filtro y coincide con SQLite.',
        'El reporte anual permite cambiar de año y exportar los resultados.',
        'La tabla anual muestra mil colones de ingreso y cien de gasto. El CSV descargado coincide en categoría, mes, año e importes con SQLite.',
        'Introducimos un monto negativo. El navegador bloquea el formulario y muestra su validación nativa. La suite comprueba que no se guardó el movimiento.',
        'Omitimos deliberadamente la validación del navegador para probar el servidor. Responde HTTP cuatrocientos: el monto debe ser mayor que cero. La base no cambia.',
        'La cuenta estándar recibe HTTP cuatrocientos tres en administración y calidad. Cerramos sesión y comprobamos que las rutas protegidas vuelven a pedir autenticación.',
        'Pasaron veintisiete pruebas E2E y, por separado, ciento nueve de regresión. También pasaron instalación automática y carga local. Siguen pendientes la revisión del grupo, la instalación independiente y la evaluación docente.'
    ]
    assert len(narration)==len(scenes), (len(narration),len(scenes))
    script = ['# Guion sincronizado con la grabación real', '',
              f"Video: video/MisFinanzas_S4.mp4 · duración {info['duration']:.2f} s (aprox. {stamp(round(info['duration']))}) · 1280 × 720 · sin audio.",
              'Voz sugerida para una presentación de 3–5 minutos. Las marcas provienen de la ejecución, con una tolerancia aproximada de 3 segundos respecto al primer fotograma. No hay narración generada ni servicios externos.', '']
    for i,(scene,text) in enumerate(zip(scenes,narration)):
        end = scenes[i+1]['inicio'] if i+1<len(scenes) else info['duration']
        script += [f"## {stamp(scene['inicio'])}–{stamp(end)} · {scene['escena']}", '', text, '']
    script += ['La página final es el informe auténtico del runner de QA. Las pantallas de la aplicación se grabaron sin reemplazos ni montaje de resultados. Los casos adicionales se documentan en sus archivos; no todos aparecen en el video.']
    (out/'GUION_PRESENTACION.md').write_text('\n'.join(script)+'\n',encoding='utf-8')

    diagnostics = '''# Incidencias de la automatización y límites observados

Durante la preparación se ejecutaron diagnósticos separados; no se suman al conteo final ni se presentan como ejecuciones totalmente aprobadas.

| Incidencia | Observación real | Corrección del runner |
|---|---|---|
| Selección de perfil | El botón de ingreso permanece deshabilitado hasta elegir el radio del perfil. | Elegir explícitamente el perfil antes de pulsar Ingresar. |
| Categoría del presupuesto | El formulario usa ingreso como tipo inicial; el ensayo esperaba gasto. | Seleccionar Gasto explícitamente. |
| Mensajes de validación | El error de monto y el de filtros son párrafos visibles sin role=alert. | Verificar el texto y el código 400 realmente implementados. |
| Acceso restringido | El encabezado real es “No tiene permiso para ver esta página”. | Selector exacto del encabezado observado y comprobación HTTP 403. |
| Primera grabación incompleta y otro diagnóstico | Timeout de navegación tras enviar un movimiento; tampoco respondió la captura de fallo. No se determinó una causa única. | Conservar como intentos incompletos; usar Chromium completo, margen de espera de 30 s, guardar resultados por paso y cerrar recursos incluso tras errores. Sin reintentar escrituras. |
| Encuadre | Las capturas iniciales de historial y reporte mostraban el encabezado sin todos los resultados. | Capturas de página completa y desplazamiento real a las tablas y totales durante la toma final. |

Los intentos de diagnóstico se conservaron localmente fuera del ZIP final; los fallos se describen aquí para mantener trazabilidad. No se cambió src/ ni la lógica funcional del sistema. Los timeouts no se atribuyen a un defecto confirmado de la aplicación: la ejecución final y la suite de regresión constan por separado.

Limitaciones: recorrido secuencial, un usuario estándar propietario, Chromium/Windows, una moneda y un período. No demuestra cobertura exhaustiva, concurrencia, accesibilidad completa ni seguridad de producción. La prueba pública comprueba solamente GET del login. No hay acceso SSH, WebAdmin ni navegación autenticada pública.
'''
    (report/'DIAGNOSTICO_AUTOMATIZACION.md').write_text(diagnostics,encoding='utf-8')
    shutil.copyfile(ROOT/'scripts'/'e2e'/'README.md',out/'REPETIR_PRUEBAS.md')
    (out/'LEEME.md').write_text(f'''# Entrega real E2E — MisFinanzas

Fecha: {result['entorno']['fecha']}. Código evaluado: `{result['entorno']['commit']}` en `{result['entorno']['rama']}`. Windows, Python {result['entorno']['python']}, SQLite {result['entorno']['sqlite']}, Playwright {result['entorno']['playwright']}, Chromium {result['entorno']['chromium']}.

- E2E: **27 aprobadas, 0 fallidas, 0 omitidas**.
- Regresión existente: **109 aprobadas, 0 fallidas**; ejecución independiente.
- Instalación limpia automática y carga local idempotente de 1.000 registros: aprobadas.
- Login público: **{public['estado']}**, HTTP {public.get('http','no disponible')}; solo GET sin sesión.
- Video real: [MP4](video/MisFinanzas_S4.mp4), **{info['duration']:.2f} s (aprox. {stamp(round(info['duration']))})**, 1280 × 720, H.264, sin audio. [WebM original](video/MisFinanzas_S4.webm).
- Capturas: las **12 requeridas** y capturas complementarias en [capturas/](capturas/).
- [Informe HTML de Playwright Python](reportes/playwright.html), [resumen y casos](reportes/RESUMEN.md), [matriz S1–S4](reportes/MATRIZ_S1_S4.md).
- [Errores y pendientes](reportes/ERRORES.md), [diagnósticos del runner](reportes/DIAGNOSTICO_AUTOMATIZACION.md), [validación de archivos](reportes/VERIFICACION_ARCHIVOS.json).
- [Guion sincronizado](GUION_PRESENTACION.md), [instrucciones de repetición](REPETIR_PRUEBAS.md).
- Suite reutilizable: `scripts/e2e/`, incluida en el ZIP con esa misma estructura. Requiere el checkout del repositorio; el ZIP no contiene la aplicación completa.
- CSV descargados auténticos en [exportaciones/](exportaciones/); solo datos ficticios.

Las bases temporales se eliminaron y no se incluyen secretos, cookies ni bases en el paquete. El código funcional permanece sin cambios. No se realizó push, merge, publicación de tags, despliegue ni publicación del video.

No se detectaron defectos funcionales en los 27 casos de la ejecución final. La primera toma y diagnósticos tuvieron incidencias del runner, documentadas y excluidas del conteo final. Siguen pendientes instalación por otro integrante, acta, revisión del grupo, tags, enlace público y evaluación docente.
''',encoding='utf-8')

    # El manifiesto incluye tanto las evidencias como el código exacto de la suite entregada.
    files = [(p,Path('evidencias/s4')/p.relative_to(out)) for p in out.rglob('*') if p.is_file() and p.name!='MANIFIESTO_SHA256.csv']
    files += [(p,p.relative_to(ROOT)) for p in (ROOT/'scripts'/'e2e').glob('*') if p.is_file() and p.suffix in ('.py','.ps1','.md','.txt')]
    files += [(ROOT/'docs'/'seguimientos'/name,Path('docs/seguimientos')/name)
              for name in ('S1.md','S2.md','S3.md','S4.md','ENTREGA_S4.md','GUIA_DEMO_FINAL.md','VIDEO_S4.md')]
    for source,_ in files:
        assert source.suffix.lower() not in ('.db','.sqlite','.sqlite3','.env','.har'), source
        assert 'login_credentials' not in source.name and 'storage_state' not in source.name, source
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(['archivo','bytes','sha256'])
    for source,relative in sorted(files,key=lambda pair:pair[1].as_posix()):
        writer.writerow([relative.as_posix(),source.stat().st_size,hashlib.sha256(source.read_bytes()).hexdigest()])
    manifest = report/'MANIFIESTO_SHA256.csv'
    manifest.write_text(buffer.getvalue(),encoding='utf-8')
    files.append((manifest,Path('evidencias/s4/reportes/MANIFIESTO_SHA256.csv')))
    target = Path(args.zip).resolve()
    target.parent.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for source,relative in files:
            archive.write(source,relative.as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist())==len(files)
    print(json.dumps(dict(zip=str(target),archivos=len(files),bytes=target.stat().st_size,
                          sha256=hashlib.sha256(target.read_bytes()).hexdigest(),video=verification),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
