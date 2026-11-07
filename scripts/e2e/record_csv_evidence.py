"""Cobertura nativa del CSV descargado: visor QA separado de la aplicación."""
import csv
import argparse
import html
from pathlib import Path
import time
from media_common import ROOT,save,sha


def main():
    from playwright.sync_api import sync_playwright,expect
    from record_presentation import CURSOR
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4_final')
    parser.add_argument('--work',default='.venv-e2e/presentacion/cobertura-csv')
    args=parser.parse_args()
    out=Path(args.output).resolve()
    source=out/'exportaciones/reporte_anual.csv'
    with source.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.reader(f))
    assert len(rows)==3 and rows[0][-1]=='total'
    assert sorted(r[-1] for r in rows[1:])==['100.00','1000.00']
    table=''.join('<tr>'+''.join('<td>'+html.escape(cell)+'</td>' for cell in row)+'</tr>' for row in rows)
    pagefile=out/'reportes/visor_csv_anual.html'
    pagefile.write_text(f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Evidencia CSV real</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#edf3f8;color:#18374c;font:24px Arial;min-height:1080px;display:grid;place-items:center}}main{{width:1760px;background:white;border-radius:22px;padding:45px}}h1{{font-size:42px}}table{{border-collapse:collapse;width:100%;font-size:20px}}td{{padding:14px 10px;border:1px solid #bcceda}}tr:first-child{{background:#deebf4;font-weight:bold}}small{{font-size:20px}}</style><main><small>VISOR LOCAL DE EVIDENCIA QA · ARCHIVO DESCARGADO AUTÉNTICO</small><h1>Exportación anual CSV</h1><p>reporte_anual.csv · importes contrastados con SQLite · datos ficticios</p><table>{table}</table><p>Ingreso: CRC 1.000,00 · gasto: CRC 100,00 · mismo año y mes que el reporte anual.</p><small>Esta vista muestra el archivo exportado; está separada de la interfaz de MisFinanzas.</small></main></html>''',encoding='utf-8')
    work=Path(args.work).resolve()
    work.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chromium',headless=True)
        context=browser.new_context(viewport=dict(width=1920,height=1080),record_video_dir=str(work),record_video_size=dict(width=1920,height=1080))
        context.add_init_script(CURSOR)
        page=context.new_page();page.goto(pagefile.as_uri(),wait_until='load')
        expect(page.get_by_role('heading',name='Exportación anual CSV')).to_be_visible()
        page.evaluate('''()=>{let d=document.createElement('div');d.id='qa-sync';d.style.cssText='position:fixed;left:1870px;top:10px;width:20px;height:20px;background:rgb(255,0,255);z-index:2147483647';document.body.append(d)}''')
        page.wait_for_timeout(1000);page.screenshot(path=str(work/'marca.png'));page.wait_for_timeout(500)
        page.evaluate('document.getElementById("qa-sync").remove()');start=time.monotonic()
        page.mouse.move(1750,880,steps=15)
        page.wait_for_timeout(13000)
        elapsed=time.monotonic()-start
        page.screenshot(path=str(out/'capturas/15_csv_verificado.png'))
        video=page.video;page.close();video.save_as(str(work/'csv_real.webm'));context.close();browser.close()
    save(work/'cobertura.json',dict(fuente=(work/'csv_real.webm').relative_to(ROOT).as_posix(),duracion_grabada=elapsed,
         csv_sha256=sha(source),tipo='Captura nativa de visor local del CSV real descargado',escena=15))


if __name__=='__main__':
    main()
