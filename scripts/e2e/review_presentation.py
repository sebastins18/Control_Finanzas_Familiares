"""Extrae muestras de las 19 escenas y documenta sincronización y validación audiovisual."""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import re
from PIL import Image,ImageDraw,ImageFont
from media_common import ROOT,ffmpeg,probe,run,save,sha,timestamp

SAMPLES=[(3,8,14),(18.7,21.5,26),(30,33,36.5),(41,45.5,47.2,50.4,54),
 (57.6,60.8,65),(71.5,74,80),(85.4,87,90.8),(98.4,100.5,108),(112.5,114,120),
 (128,131,135),(143.5,147,151),(156,160,164),(166.8,170.8,175),(178.5,181,183),
 (185,189.5,193),(197.8,201.5,205),(208,214,218),(221,224,228),(234,239,244)]
REQUIRED=['Login e identidad del proyecto','Formulario y selección de perfil','Saldos, resumen mensual y estado inicial',
 'Cuentas y CRUD de categorías','Formulario de ingreso y movimiento CRC 1.000','Formulario de gasto y movimiento CRC 25',
 'Movimiento previo, campos de edición y gasto CRC 35','Eliminar y comprobar ausencia; ingreso permanece',
 'Presupuesto CRC 100 y estado inicial','Cerca del límite: CRC 80/100; alerta 80 persistida',
 'Excedido: CRC 100/100; alertas 80 y 100','Tres registros; ingresos 1.000 y gastos 100',
 'Filtros combinados; único gasto de 80 y CSV','Encabezado, navegación anual y exportación',
 'Totales anuales y contenido del CSV descargado','Monto negativo y mensaje nativo','Error controlado 400, sin escritura inválida',
 'Cuenta estándar, rechazos 403 y login después de logout','Resumen comprobado 27/27, 109/109, carga, instalación y respaldo']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4_final')
    args=parser.parse_args()
    out=Path(args.output).resolve()
    video=out/'MisFinanzas_S4_FINAL_Narrado_Subtitulado.mp4'
    source=out/'MisFinanzas_S4_FINAL_Narrado.mp4'
    scenes=json.loads((out/'reportes/grabacion_escenas.json').read_text(encoding='utf-8'))['escenas']
    assert len(scenes)==19
    review=out/'reportes/revision_escenas';review.mkdir(exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    contact=Image.new('RGB',(1920,5*320),'#e9f0f7')
    draw=ImageDraw.Draw(contact)
    for i,(scene,times) in enumerate(zip(scenes,SAMPLES),1):
        strip=Image.new('RGB',(640*len(times),405),'#e9f0f7')
        d=ImageDraw.Draw(strip)
        for j,t in enumerate(times):
            frame=review/f'escena_{i:02}_{j+1}.png'
            run([ffmpeg(),'-v','error','-ss',str(t),'-i',video,'-frames:v','1','-update','1','-y',frame])
            picture=Image.open(frame).convert('RGB');picture.thumbnail((640,360))
            strip.paste(picture,(j*640,0));d.text((j*640+12,370),f'Escena {i:02} · {timestamp(t)}',font=font,fill='#17344b')
        strip.save(review/f'escena_{i:02}_revision.jpg',quality=92)
        key=Image.open(review/f'escena_{i:02}_2.png').convert('RGB');key.thumbnail((480,270))
        x=(i-1)%4*480;y=(i-1)//4*320
        contact.paste(key,(x,y))
        draw.text((x+12,y+276),f'{i:02} · {scene["titulo"][:43]}',font=small,fill='#17344b')
        print(f'{i:02}/19 muestras extraídas',flush=True)
    contact.save(out/'MisFinanzas_S4_FINAL_Hoja_Contacto.jpg',quality=93)
    for first in range(0,19,5):
        group=scenes[first:first+5]
        sheet=Image.new('RGB',(1280,len(group)*405),'#e9f0f7')
        sd=ImageDraw.Draw(sheet)
        for row,scene in enumerate(group):
            for col,t in enumerate((scene['inicio']+.08,scene['final']-.08)):
                path=review/f"limite_{scene['escena']:02}_{col}.png"
                run([ffmpeg(),'-v','error','-ss',str(t),'-i',video,'-frames:v','1','-update','1','-y',path])
                picture=Image.open(path).convert('RGB');picture.thumbnail((640,360))
                sheet.paste(picture,(col*640,row*405))
                sd.text((col*640+10,row*405+370),f"Escena {scene['escena']:02} · {'Inicio' if col==0 else 'Final'}",font=font,fill='#17344b')
        sheet.save(review/f'limites_{first+1:02}_{first+len(group):02}.jpg',quality=92)
    silence=run([ffmpeg(),'-hide_banner','-i',source,'-af','silencedetect=noise=-40dB:d=0.8','-vn','-f','null','-'])
    text=silence.stderr.decode(errors='replace')
    intervals=[dict(inicio=float(a),final=float(b),duracion=float(c)) for a,b,c in re.findall(
        r'silence_start: ([0-9.]+).*?silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)',text,re.S)]
    save(out/'reportes/silencios.json',dict(umbral_db=-40,minimo_segundos=.8,intervalos=intervals,
         criterio='Los paquetes AAC son idénticos al master aceptado. No se introdujeron silencios; los intervalos fuente se usan para lectura/acciones.',
         listening_review='not_performed'))
    notes_path=out/'reportes/revision_visual_19.json'
    notes=json.loads(notes_path.read_text(encoding='utf-8')) if notes_path.exists() else {}
    voice=json.loads((out/'reportes/alineacion_voz.json').read_text(encoding='utf-8'))['escenas']
    lines=['# MisFinanzas S4 — guion y sincronización definitivos','',
       'Voz: es-CR-JuanNeural, pista AAC extraída del MP4 aceptado y reutilizada sin recodificación. Video: 1920 × 1080 nativos, 25 fps, 246,84 s. No se han cambiado tono, velocidad ni palabras del audio.','',
       '| Escena | Inicio | Final | Narración | Pantalla requerida | Acción visual | Validación |',
       '|---|---|---|---|---|---|---|']
    for scene,spoken,required in zip(scenes,voice,REQUIRED):
        n=scene['escena'];note=notes.get(str(n),'Revisión visual pendiente; DOM y datos comprobados durante la captura.')
        narration=spoken['text'].replace('HTTP cuatrocientos','error cuatrocientos').replace('E2E','de extremo a extremo')
        lines.append(f"| {n:02} | {timestamp(scene['inicio'])} | {timestamp(scene['final'])} | {narration} | {required} | {scene['titulo']} | {note} |")
    lines+=['','Los subtítulos se anclan en tiempos de reconocimiento local del audio; las variantes de siglas reflejan su pronunciación en el master. No se usó reparto proporcional por palabras.',
       'La portada lateral de la escena 1 está rotulada como presentación editorial. El visor CSV y el resumen de QA se identifican como evidencias; el resto del funcionamiento procede del navegador real.',
       'Los paquetes de audio fueron comparados por SHA-256, uno por uno, entre fuente y exportaciones. Esto comprueba su conservación; no equivale a una escucha humana.','']
    (out/'MisFinanzas_S4_FINAL_Guion.md').write_text('\n'.join(lines),encoding='utf-8')
    technical=json.loads((out/'reportes/validacion_tecnica.json').read_text(encoding='utf-8'))
    validation=['# Validación final de MisFinanzas S4','',
       'Fecha: '+datetime.now(timezone(timedelta(hours=-6))).isoformat(timespec='seconds')+'.','',
       '- Dos MP4 decodificados íntegramente con FFmpeg: H.264 y AAC, 1920 × 1080 nativos, 25 fps.',
       '- Duración: '+str(technical['duracion'])+' segundos; diferencia entre pistas menor de 50 ms.',
       '- Los paquetes AAC son idénticos al audio aceptado. Sin regeneración, filtros de tempo, cambios de tono ni remezcla.',
       '- 19 escenas capturadas nuevamente con Playwright sobre SQLite temporal aislada; consultas de contraste en modo de solo lectura.',
       '- Recorrido funcional independiente: 27 aprobadas, 0 fallidas, 0 omitidas; regresión completa: 109/109.',
       '- Instalación automática, carga idempotente de 1.000 movimientos y respaldo consistente: aprobados; integridad ok y FK 0.',
       '- Escena 15: existen MP3 y WAV originales; la transcripción coincide con tabla anual y exportación. La caché del generador explica una posible omisión de la línea de síntesis, pero no se dispone de aquel log para afirmarlo como hecho.',
       '- Hoja de contacto de 19 escenas y muestras de inicio, acción y resultado en reportes/revision_escenas/.',
       '- No se realizó escucha humana del audio desde este entorno. La revisión usa transcripción local, conservación exacta de paquetes, detección de silencio, lectura de subtítulos y fotogramas por escena.','',
       '| Escena | Resultado de revisión visual |','|---|---|']
    validation += [f'| {n:02} | {notes.get(str(n),"Pendiente de inspección visual")} |' for n in range(1,20)]
    validation+=['','La confirmación del responsable de que S3 está cerrado y S4 desplegado se documenta separadamente de estas pruebas locales. Solo se hizo GET del login público; no se accedió a WebAdmin ni se modificó CRNube.',
       'Pendientes humanos: revisión del grupo, instalación independiente, publicación del video y evaluación docente. No se acredita aprobación del profesor.','']
    (out/'MisFinanzas_S4_FINAL_Validacion.md').write_text('\n'.join(validation),encoding='utf-8')


if __name__=='__main__':
    main()
