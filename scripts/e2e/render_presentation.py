"""Conforma escenas a 1× y reutiliza el AAC original; subtítulos con alineación local."""
from __future__ import annotations
import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import shutil
import unicodedata
from media_common import ROOT,ffmpeg,ffprobe,probe,run,save,sha,timestamp


def norm(word):
    return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFD',word.lower()))


def captions(out,work):
    aligned=json.loads((out/'reportes/alineacion_voz.json').read_text(encoding='utf-8'))['escenas']
    cues=[]
    findings=[]
    from PIL import ImageFont
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',38)
    for scene in aligned:
        # La voz fuente pronuncia estas siglas según el generador original.
        canonical=scene['text'].replace('HTTP cuatrocientos','error cuatrocientos').replace('E2E','de extremo a extremo').split()
        words=[dict(w) for w in scene['words']]
        if scene['escena']==1 and norm(words[0]['text'])=='mis' and norm(words[1]['text'])=='finanzas':
            words=[dict(words[0],text='MisFinanzas',end=words[1]['end'])]+words[2:]
        for word in words:
            if norm(word['text'])=='eniciamos': word['text']='Iniciamos'
            if norm(word['text'])=='trinta': word['text']='treinta'
            if scene['escena']==19 and word['text']=='V,': word['text']='y,'
        matcher=SequenceMatcher(None,list(map(norm,canonical)),[norm(w['text']) for w in words],autojunk=False)
        mapping={}
        for operation,a,b,c,d in matcher.get_opcodes():
            if operation=='equal' or operation=='replace' and b-a==d-c:
                mapping.update({a+i:c+i for i in range(b-a)})
        # Intervalos de frase anclados en palabras reconocidas; nunca reparto proporcional de tiempos.
        groups=[]
        first=0
        for i,word in enumerate(canonical):
            size=len(' '.join(canonical[first:i+1]))
            if i==len(canonical)-1 or size>=60 or (word.endswith(('.',':',';')) and size>=25):
                groups.append((first,i+1));first=i+1
        if len(groups)>1 and len(' '.join(canonical[groups[-1][0]:groups[-1][1]]))<20:
            groups[-2]=(groups[-2][0],groups[-1][1]);groups.pop()
        if scene['escena']==19 and len(groups)>1:
            groups[-2]=(groups[-2][0],groups[-1][1]);groups.pop()
        for first,last in groups:
            anchors=[mapping[i] for i in range(first,last) if i in mapping]
            assert anchors and len(anchors)/(last-first)>=.6,(scene['escena'],canonical[first:last])
            begin=words[min(anchors)]['start']
            end=words[max(anchors)]['end']
            text=' '.join(canonical[first:last])
            lines=[];line=''
            for word in text.split():
                candidate=(line+' '+word).strip()
                if font.getlength(candidate)>1640 and line:
                    lines.append(line);line=word
                else:
                    line=candidate
            if line: lines.append(line)
            assert len(lines)<=2
            assert end>begin and end<=246.84
            if cues and begin<cues[-1]['end']:
                begin=cues[-1]['end']
            cue=dict(escena=scene['escena'],start=begin,end=end,text='\n'.join(lines),
                     cps=round(len(text)/(end-begin),2),metodo='límites de palabras de ASR; frase canónica contrastada')
            cues.append(cue)
    for i,cue in enumerate(cues):
        limit=cues[i+1]['start']-.025 if i+1<len(cues) else 246.84
        cue['end']=round(min(cue['end']+.3,limit),3)
        cue['cps']=round(len(cue['text'].replace('\n',' '))/(cue['end']-cue['start']),2)
        if cue['cps']>22 or cue['end']-cue['start']<.8:
            findings.append(cue)
    save(out/'reportes/subtitulos_alineados.json',dict(cues=cues,advertencias_lectura=findings,
         correcciones='Se eliminaron alucinaciones finales de ASR no presentes en el guion fuente. Se normalizaron MisFinanzas, Iniciamos, treinta e y. La pista de audio no se modificó.',listening_review='not_performed'))
    srt=out/'MisFinanzas_S4_FINAL_Subtitulos.srt'
    srt.write_text('\n\n'.join(f"{i}\n{timestamp(c['start'],True)} --> {timestamp(c['end'],True)}\n{c['text']}" for i,c in enumerate(cues,1))+'\n',encoding='utf-8')
    def ass_time(t):
        return timestamp(t)[1:-1]
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,38,&H00FFFFFF,&H00FFFFFF,&H60000000,&H60000000,0,0,0,0,100,100,0,0,3,3,0,2,120,120,32,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    ass=work/'subtitulos.ass'
    ass.write_text(header+'\n'.join(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Default,,0,0,0,,{c['text'].replace(chr(10),chr(92)+'N')}" for c in cues)+'\n',encoding='utf-8')
    return cues


def marker_end(source,scene=None):
    # Solo el preroll lleva marca técnica. El primer fotograma sin ella fija el inicio real.
    p=probe(source)
    video=next(s for s in p['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'])==(1920,1080)
    assert video['r_frame_rate']=='25/1'
    data=run([ffmpeg(),'-v','error','-i',source,'-vf','crop=80:24:1840:0,format=rgb24','-an','-f','rawvideo','-']).stdout
    import numpy as np
    pixels=np.frombuffer(data,dtype=np.uint8).reshape((-1,24,80,3))
    pink=(pixels[:,:,:,0]>200)&(pixels[:,:,:,1]<80)&(pixels[:,:,:,2]>200)
    marked=np.flatnonzero(pink.any(axis=(1,2))).tolist()
    if not marked:
        assert scene is not None, f'No se encontró marca técnica: {source}'
        scene['metodo_inicio']='Anclaje al final del clip y duración medida; comprobación visual de la escena requerida'
        return round((float(p['format']['duration'])-scene['duracion_grabada'])*25)/25
    if scene is not None:
        scene['metodo_inicio']='Primer fotograma después de la marca técnica visible'
    return (max(marked)+1)/25


def audio_packets(path):
    data=run([ffprobe(),'-v','error','-select_streams','a:0','-show_packets','-show_data_hash','sha256',
              '-show_entries','packet=data_hash','-of','json',path]).stdout
    return [p['data_hash'] for p in json.loads(data)['packets']]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4_final')
    parser.add_argument('--work',default='.venv-e2e/presentacion/toma-final')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--csv-coverage',default='.venv-e2e/presentacion/cobertura-csv/cobertura.json')
    args=parser.parse_args()
    out=Path(args.output).resolve();work=Path(args.work).resolve()
    work.mkdir(parents=True,exist_ok=True)
    cues=captions(out,work)
    if args.prepare_only:
        return
    selection=work/'seleccion_final.json'
    entries=json.loads((selection if selection.exists() else work/'escenas_grabadas.json').read_text(encoding='utf-8'))
    assert [s['escena'] for s in entries]==list(range(1,20))
    conformed=work/'conformados';conformed.mkdir(exist_ok=True)
    edl=[]
    shutil.copyfile('C:/Windows/Fonts/arial.ttf',work/'arial.ttf')
    for scene in entries:
        number=scene['escena'];source=ROOT/scene['fuente']
        begin=marker_end(source,scene)
        duration=scene['final']-scene['inicio']
        assert float(probe(source)['format']['duration'])>=begin+duration-.04
        target=conformed/f'escena_{number:02}.mp4'
        extra_source=None
        filtergraph='setpts=PTS-STARTPTS'
        if number==1:
            filtergraph+=",drawbox=x=70:y=295:w=580:h=430:color=0x173d59@0.96:t=fill"
            for text,y,size,color in [('PRESENTACION EDITORIAL',335,23,'0x7fe1ce'),('MisFinanzas',395,54,'white'),
                 ('Python 3.12 + SQLite',485,33,'white'),('HTML / CSS',540,33,'white'),('E2E local con Playwright',605,31,'white')]:
                filtergraph+=f",drawtext=fontfile=arial.ttf:text='{text}':x=110:y={y}:fontsize={size}:fontcolor={color}"
        if not target.exists():
            coverage=Path(args.csv_coverage).resolve()
            if number==15 and coverage.exists():
                extra=json.loads(coverage.read_text(encoding='utf-8'))
                extra_path=ROOT/extra['fuente']
                extra_begin=marker_end(extra_path,extra)
                first_frame=round(begin*25)
                extra_frame=round(extra_begin*25)
                graph=(f'[0:v]trim=start_frame={first_frame}:end_frame={first_frame+112},setpts=PTS-STARTPTS[a];'
                       f'[1:v]trim=start_frame={extra_frame}:end_frame={extra_frame+213},setpts=PTS-STARTPTS[b];'
                       '[a][b]concat=n=2:v=1:a=0[v]')
                command=[ffmpeg(),'-v','error','-n','-i',source,'-i',extra_path,'-filter_complex',graph,'-map','[v]']
                extra_source=dict(fuente=extra['fuente'],source_in=extra_begin,source_out=extra_begin+8.52,
                                  sequence_start=188.48,sequence_end=197.0,sha256=sha(extra_path),csv_sha256=extra['csv_sha256'])
            elif scene.get('cortes'):
                graph=[]
                for j,cut in enumerate(scene['cortes']):
                    length=cut['dest_out']-cut['dest_in']
                    start=begin+cut['source_in']
                    assert start+length<=float(probe(source)['format']['duration'])+.041
                    first_frame=round(start*25)
                    last_frame=first_frame+round(length*25)
                    graph.append(f'[0:v]trim=start_frame={first_frame}:end_frame={last_frame},setpts=PTS-STARTPTS[c{j}]')
                graph.append(''.join(f'[c{j}]' for j in range(len(scene['cortes'])))+f'concat=n={len(scene["cortes"])}:v=1:a=0[v]')
                command=[ffmpeg(),'-v','error','-n','-i',source,'-filter_complex',';'.join(graph),'-map','[v]']
            else:
                command=[ffmpeg(),'-v','error','-n','-ss',str(begin),'-i',source,'-t',str(duration),'-vf',filtergraph]
            run([*command,'-an','-c:v','libx264','-threads','4','-preset','fast','-crf','18','-pix_fmt','yuv420p',
                 '-video_track_timescale','12800',target],timeout=240)
        actual=float(probe(target)['format']['duration'])
        assert abs(actual-duration)<.045,(number,actual,duration)
        source_span=(4.48 if extra_source else max((c['source_in']+c['dest_out']-c['dest_in'] for c in scene.get('cortes',[])),default=duration))
        edl.append(dict(escena=number,source_in=begin,source_out=begin+source_span,sequence_start=scene['inicio'],
                        sequence_end=scene['final'],velocidad=1.0,fuente=scene['fuente'],sha256_fuente=sha(source),
                        conformado=target.relative_to(ROOT).as_posix(),cortes=scene.get('cortes',[]),
                        metodo_inicio=scene['metodo_inicio'],fuente_adicional=extra_source))
        print(f'{number:02}/19 conformada a 1x; {duration:.2f}s',flush=True)
    save(out/'reportes/montaje_edl.json',edl)
    concat=work/'concat.txt'
    concat.write_text('\n'.join("file '"+str((ROOT/e['conformado']).resolve()).replace('\\','/')+"'" for e in edl),encoding='utf-8')
    picture=work/'imagen_final.mp4'
    if not picture.exists():
        run([ffmpeg(),'-v','error','-n','-f','concat','-safe','0','-i',concat,'-c:v','copy',picture])
    voice=ROOT/'.venv-e2e/presentacion/voz_original.m4a'
    clean=out/'MisFinanzas_S4_FINAL_Narrado.mp4'
    if not clean.exists():
        run([ffmpeg(),'-v','error','-n','-i',picture,'-i',voice,'-map','0:v:0','-map','1:a:0',
             '-c:v','copy','-c:a','copy','-movflags','+faststart',clean])
    burned=out/'MisFinanzas_S4_FINAL_Narrado_Subtitulado.mp4'
    if not burned.exists():
        result=__import__('subprocess').run([ffmpeg(),'-v','error','-n','-i',str(clean),'-vf','ass=subtitulos.ass',
               '-map','0:v:0','-map','0:a:0','-c:v','libx264','-threads','4','-preset','fast','-crf','18',
               '-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(burned)],cwd=work,capture_output=True,timeout=600)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace'))
    probes={}
    for path in (clean,burned):
        p=probe(path);probes[path.name]=p
        p['format']['filename']=path.name
        video=next(s for s in p['streams'] if s['codec_type']=='video')
        audio=next(s for s in p['streams'] if s['codec_type']=='audio')
        assert (video['width'],video['height'])==(1920,1080)
        assert abs(float(video['duration'])-float(audio['duration']))<.05
        assert video['codec_name']=='h264' and audio['codec_name']=='aac'
        assert audio_packets(voice)==audio_packets(path),'La secuencia de paquetes AAC cambió'
        run([ffmpeg(),'-v','error','-i',path,'-f','null','-'],timeout=240)
    save(out/'reportes/ffprobe_final.json',probes)
    save(out/'reportes/validacion_tecnica.json',dict(escenas=19,resolucion_nativa=[1920,1080],velocidad_video=1,
         voz_reutilizada_sin_regenerar=True,paquetes_aac_identicos=True,decodificacion_completa=True,
         duracion=float(probes[clean.name]['format']['duration']),subtitulos=len(cues),
         listening_review='not_performed',revision='Tiempos de ASR, assertions DOM/SQLite y revisión visual por escena; no se realizó escucha humana.'))


if __name__=='__main__':
    main()
