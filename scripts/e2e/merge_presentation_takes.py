"""Selecciona tomas reales y cortes a 1x; elimina esperas de navegación sin tocar la voz."""
import argparse
import json
from pathlib import Path
from media_common import ROOT,save


def frame(t):
    return round(t*25)/25


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',default='.venv-e2e/presentacion/toma-final')
    parser.add_argument('--corrections',default='.venv-e2e/presentacion/correcciones-01')
    parser.add_argument('--output',default='evidencias/s4_final')
    args=parser.parse_args()
    base=Path(args.base).resolve()
    original=json.loads((base/'escenas_grabadas.json').read_text(encoding='utf-8'))
    corrections=json.loads((Path(args.corrections)/'escenas_grabadas.json').read_text(encoding='utf-8'))
    takes={s['escena']:s for s in original}
    takes.update({s['escena']:s for s in corrections})
    def edit(scene,parts):
        scene['cortes']=[dict(dest_in=frame(a),dest_out=frame(b),source_in=frame(c)) for a,b,c in parts]
        previous_end=0
        for part in scene['cortes']:
            assert part['source_in']>=previous_end-.041,scene
            previous_end=part['source_in']+part['dest_out']-part['dest_in']
        assert abs(scene['cortes'][-1]['dest_out']-(scene['final']-scene['inicio']))<.041
    for number in (4,5,9,13,15):
        scene=takes[number]
        times=[v['t'] for v in scene['validaciones'] if v['tipo']=='encuadre']
        duration=scene['final']-scene['inicio']
        if number==4:
            assert len(times)==6,times
            edit(scene,[(0,4.6,0),(4.6,5.96,times[0]+2.2),(5.96,6.88,times[1]+1),
                        (6.88,7.88,times[2]+1.5),(7.88,9.88,times[3]+2.1),
                        (9.88,11.52,times[4]+1),(11.52,18,times[5]+.04)])
        else:
            cut={5:3.6,9:2.52,13:4.12,15:4.48}[number]
            if times[-1]+.04<=cut:
                scene['cortes']=[]
            else:
                edit(scene,[(0,cut,0),(cut,duration,times[-1]+.04)])
    entries=[takes[n] for n in range(1,20)]
    save(base/'seleccion_final.json',entries)
    save(Path(args.output)/'reportes/grabacion_escenas.json',dict(resolucion=[1920,1080],
         fuente='Playwright Chromium nativo; montaje de tomas comprobadas',datos='Ficticios, base temporal eliminada',
         codigo_funcional_modificado=False,escenas=entries))


if __name__=='__main__':
    main()
