"""Prepara entrega y propuesta Git selectiva; no hace add, commit, push ni publicaciones."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timedelta,timezone
import io
import json
from pathlib import Path
import subprocess
import zipfile
from media_common import ROOT,save,sha


def git(*args):
    return subprocess.run(['git','-c',f'safe.directory={ROOT.as_posix()}',*args],cwd=ROOT,capture_output=True,text=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4_final')
    args=parser.parse_args()
    out=Path(args.output).resolve()
    technical=json.loads((out/'reportes/validacion_tecnica.json').read_text(encoding='utf-8'))
    review=json.loads((out/'reportes/revision_visual_19.json').read_text(encoding='utf-8'))
    assert set(review)=={str(i) for i in range(1,20)} and all(review.values())
    assert technical['paquetes_aac_identicos'] and technical['decodificacion_completa']
    e2e=json.loads((out/'reportes/e2e/reportes/resultados.json').read_text(encoding='utf-8'))
    assert e2e['conteo']==dict(APROBADA=27,FALLIDA=0,OMITIDA=0)
    extra=json.loads((out/'reportes/complementarias/comprobaciones_adicionales.json').read_text(encoding='utf-8'))
    assert len(extra['pruebas'])==4 and all(p['estado']=='APROBADA' for p in extra['pruebas'])
    branch=git('branch','--show-current').stdout.strip()
    save(out/'reportes/contexto_confirmado.json',dict(fecha=datetime.now(timezone(timedelta(hours=-6))).isoformat(timespec='seconds'),
         origen='Datos confirmados expresamente por el responsable en su solicitud',
         s3='Cerrado técnicamente en Issue #3',s4='Desplegado en CRNube, commit 8a88aeb',
         sqlite_servidor=dict(tablas=17,integrity_check='ok',errores_fk=0,wal=True,respaldo_previo_consistente=True),
         comprobacion_propia='Solo GET al login público; ninguna sesión, WebAdmin, SSH o escritura remota',
         aprobacion_docente='No acreditada',instalacion_independiente='Pendiente'))
    (out/'LEEME.md').write_text(f'''# MisFinanzas S4 — entrega audiovisual corregida

Código evaluado: `8a88aeb`. Rama local de trabajo: `{branch}`. Windows, Python 3.12, SQLite, Playwright y FFmpeg/FFprobe.

- **27/27 E2E aprobadas; 0 fallidas y 0 omitidas.** [HTML](reportes/e2e/reportes/playwright.html) · [Markdown](reportes/e2e/reportes/RESUMEN.md).
- **109/109 de regresión**; instalación limpia, carga idempotente de **1.000** y respaldo íntegro correctos. [Resultados](reportes/complementarias/comprobaciones_adicionales.json).
- Video nativo **1920 × 1080, 25 fps, {technical['duracion']:.2f} s**; sin escalado desde 720p.
- Voz Juan Neural reutilizada: mismos paquetes AAC, sin síntesis, cambios de tempo o tono.
- 19 escenas revisadas mediante fotogramas de acción, resultados y subtítulos. No se realizó escucha humana desde este entorno; la conservación de audio y sus tiempos se comprobaron técnicamente y con ASR local.

## Archivos finales

- [MP4 narrado](MisFinanzas_S4_FINAL_Narrado.mp4).
- [MP4 narrado y subtitulado](MisFinanzas_S4_FINAL_Narrado_Subtitulado.mp4). Los subtítulos están incrustados: no activar además el SRT.
- [SRT](MisFinanzas_S4_FINAL_Subtitulos.srt), [guion y tabla de sincronización](MisFinanzas_S4_FINAL_Guion.md), [validación](MisFinanzas_S4_FINAL_Validacion.md).
- [Hoja de contacto de 19 escenas](MisFinanzas_S4_FINAL_Hoja_Contacto.jpg), [muestras por escena](reportes/revision_escenas/), [12 capturas principales](capturas/).
- [Montaje y fuente de cada corte](reportes/montaje_edl.json), [inventario de 19 audios y escena 15](reportes/inventario_audio.json), [FFprobe](reportes/ffprobe_final.json).
- [Propuesta de archivos para Git](PROPUESTA_GIT.md) y [guía para repetir](../../scripts/e2e/PRESENTACION.md).

Los originales del usuario siguen en `evidencias/` y la primera toma en `evidencias/s4/`. Las tomas intermedias están en `.venv-e2e/presentacion/` y no se incluyen en commits. La aplicación no cambió su lógica funcional. Toda escritura de prueba se realizó en SQLite temporal local, eliminada al cerrar.

S3 cerrado técnicamente y S4 desplegado en CRNube en `8a88aeb`, según confirmación del responsable. El GET propio al login devolvió 200. No se modificó el servidor. Quedan pendientes instalación independiente, revisión del grupo, publicación del video y evaluación docente. No se hizo push, merge ni publicación de tags.
''',encoding='utf-8')
    captures=[out/'capturas'/f'{i:02}_{name}.png' for i,name in enumerate([
        'login','dashboard','crear_ingreso','crear_gasto','editar_movimiento','eliminar_movimiento',
        'presupuestos','alerta_80','alerta_100','historial','reporte_anual','validacion_error'],1)]
    assert all(p.exists() for p in captures)
    docs=[ROOT/'docs/seguimientos'/n for n in ('S1.md','S2.md','S3.md','S4.md','ENTREGA_S4.md','GUIA_DEMO_FINAL.md','VIDEO_S4.md')]
    sources=[p for p in (ROOT/'scripts/e2e').glob('*') if p.is_file() and p.suffix in ('.py','.ps1','.md','.txt')]
    # La documentación y JSON se pueden versionar; los binarios grandes se entregan por separado.
    small=[p for p in out.rglob('*') if p.is_file() and p.suffix in ('.md','.json','.srt') and 'revision_escenas' not in p.parts and p.name!='grabacion_parcial.json']
    proposed=[ROOT/'.gitignore',*docs,*sources,*captures,*small,out/'MisFinanzas_S4_FINAL_Hoja_Contacto.jpg']
    proposed=sorted(set(proposed),key=lambda p:p.as_posix())
    included=[]
    for path in proposed:
        relative=path.relative_to(ROOT).as_posix()
        if git('check-ignore','-q','--',relative).returncode==0:
            raise AssertionError('Un archivo propuesto para Git está ignorado: '+relative)
        included.append(relative)
    excluded=[]
    for name in ('MisFinanzas_S4_FINAL_Narrado.mp4','MisFinanzas_S4_FINAL_Narrado_Subtitulado.mp4'):
        relative=(out/name).relative_to(ROOT).as_posix()
        result=git('check-ignore','-v','--',relative)
        assert result.returncode==0
        excluded.append(result.stdout.strip())
    proposal=['# Propuesta selectiva para Git','',f'Rama: `{branch}`. No se ha ejecutado git add, commit, push, merge ni tags.','',
       'Revisar y agregar únicamente estos archivos. La lista exacta también está en reportes/archivos_git.json.','',
       *[f'- `{p}`' for p in included], '',
       'Excluir de los commits normales: MP4/WebM, WAV/MP3/M4A, ZIP, entornos, modelos, cachés, SQLite, logs, HTML generado y los fotogramas masivos de revisión. Se conservan localmente.',
       'Las fuentes históricas adicionales que ya existían en evidencias/ permanecen intactas; revisar por separado su incorporación. La propuesta no las agrega automáticamente.', '',
       'Comprobación real de los MP4 ignorados:', '', '```text',*excluded,'```','',
       'Para publicar los videos y el ZIP, elegir el medio acordado por el grupo, comprobar acceso del profesor y colocar las URL finales en README/portal.yml. No se inventa una URL pública.','']
    (out/'PROPUESTA_GIT.md').write_text('\n'.join(proposal),encoding='utf-8')
    save(out/'reportes/archivos_git.json',dict(rama=branch,propuestos=included,mp4_ignorados=excluded))
    status=git('status','--short').stdout
    (out/'reportes/ESTADO_GIT.txt').write_text(status,encoding='utf-8')
    assert git('diff','--exit-code','--','src','scripts/init_db.py','scripts/seed.py').returncode==0
    assert git('diff','--check').returncode==0
    # ZIP explícito: incluye solo entrega final, fuentes reutilizables y bitácoras.
    files=[p for p in out.rglob('*') if p.is_file() and (p.suffix not in ('.png','.webm') or p in captures)]
    files=[p for p in files if p.name!='MANIFIESTO_SHA256.csv']
    files += [ROOT/'.gitignore',*docs,*sources]
    for path in files:
        assert path.suffix not in ('.db','.sqlite','.sqlite3','.har') and '.venv' not in path.parts,path
        assert 'login_credentials' not in path.name and 'storage_state' not in path.name,path
    buffer=io.StringIO(newline='');writer=csv.writer(buffer)
    writer.writerow(['archivo','bytes','sha256'])
    for path in sorted(files,key=lambda p:p.as_posix()):
        writer.writerow([path.relative_to(ROOT).as_posix(),path.stat().st_size,sha(path)])
    manifest=out/'reportes/MANIFIESTO_SHA256.csv';manifest.write_text(buffer.getvalue(),encoding='utf-8')
    files.append(manifest)
    archive=ROOT/'evidencias/MisFinanzas_S4_FINAL_Evidencias.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in files:
            z.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for row in csv.DictReader(io.StringIO(z.read(manifest.relative_to(ROOT).as_posix()).decode('utf-8'))):
            import hashlib
            assert hashlib.sha256(z.read(row['archivo'])).hexdigest()==row['sha256']
    print(json.dumps(dict(rama=branch,propuestos_git=len(included),archivos_zip=len(files),
                          zip=str(archive),bytes=archive.stat().st_size,sha256=sha(archive)),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
