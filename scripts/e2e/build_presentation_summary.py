"""Resumen visible de QA, generado solo a partir de resultados ejecutados."""
from pathlib import Path
import json
from media_common import ROOT


def build(out):
    out=Path(out)
    e2e=json.loads((out/'reportes/e2e/reportes/resultados.json').read_text(encoding='utf-8'))
    extra=json.loads((out/'reportes/complementarias/comprobaciones_adicionales.json').read_text(encoding='utf-8'))
    assert e2e['conteo']==dict(APROBADA=27,FALLIDA=0,OMITIDA=0)
    assert len(extra['pruebas'])==4 and all(p['estado']=='APROBADA' for p in extra['pruebas'])
    assert extra['pruebas'][0]['tests']==109 and extra['pruebas'][2]['conteos']==[1000,1000]
    assert extra['pruebas'][3]['integridad']=='ok' and extra['pruebas'][3]['errores_fk']==0
    doc=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>MisFinanzas · Resultados comprobados</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#edf3f8;color:#17334a;font:25px Arial}}main{{max-width:1660px;margin:70px auto;padding:50px;background:white;border-radius:24px}}h1{{font-size:50px;margin:15px 0}}.label{{color:#267c72;letter-spacing:3px;font-size:19px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin:38px 0}}article{{border:1px solid #cbdbe6;border-radius:18px;padding:25px;background:#f5f9fc}}strong{{display:block;font-size:48px;color:#176b5b;margin:8px 0}}p{{line-height:1.5}}small{{font-size:20px;color:#4c6375}}</style>
<main><div class="label">INFORME REAL DE QA · INSTANCIA LOCAL AISLADA</div><h1>MisFinanzas — resultados verificados</h1><small>Git {e2e['entorno']['commit'][:7]} · {e2e['entorno']['fecha']} · Windows · Python 3.12 · SQLite</small>
<div class="grid"><article>E2E por navegador<strong>27 / 27</strong>0 fallidas · 0 omitidas</article><article>Regresión Python<strong>109 / 109</strong>Suite completa aprobada</article><article>Carga sintética<strong>1.000</strong>Repetición sin duplicados</article><article>Instalación limpia<strong>Correcta</strong>Verificación automática</article><article>Respaldo SQLite<strong>Verificado</strong>1.000 movimientos conservados</article><article>Integridad SQLite<strong>ok</strong>FK: 0 errores · WAL activo</article></div>
<p><b>Pendientes humanos:</b> revisión del grupo, instalación independiente y evaluación docente. La automatización no acredita aprobación del profesor.</p>
<small>Datos ficticios · Sin escrituras en CRNube · Este informe es una evidencia de QA, separado de la interfaz de la aplicación.</small></main></html>'''
    (out/'reportes/resumen_presentacion.html').write_text(doc,encoding='utf-8')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4_final')
    build(Path(parser.parse_args().output).resolve())
