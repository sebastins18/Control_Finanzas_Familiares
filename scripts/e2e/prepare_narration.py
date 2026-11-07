"""Extrae la voz aceptada sin recodificarla e identifica sus tiempos mediante ASR local."""
import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import unicodedata
import wave
import numpy as np
from media_common import ROOT,ffmpeg,probe,run,save,sha


def normalized(text):
    return re.sub(r'[^a-z0-9 ]','',unicodedata.normalize('NFD',text.lower())).split()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4_final')
    args=parser.parse_args()
    out=Path(args.output).resolve()
    work=ROOT/'.venv-e2e/presentacion'
    work.mkdir(parents=True,exist_ok=True)
    source=ROOT/'evidencias/MisFinanzas_S4_Voz_Natural.mp4'
    original_scenes=json.loads((ROOT/'evidencias/MisFinanzas_S4_Informe_Narracion_Natural.json').read_text(encoding='utf-8-sig'))
    assert len(original_scenes)==19
    audio=work/'voz_original.m4a'
    if not audio.exists():
        run([ffmpeg(),'-v','error','-n','-i',source,'-map','0:a:0','-c:a','copy',audio])
    audio_probe=probe(audio)
    audio_probe['format']['filename']='voz_original.m4a (extracción local)'
    inventory=[]
    for i,scene in enumerate(original_scenes,1):
        mp3=ROOT/'evidencias/audio_generado'/f'escena_{i:02}.mp3'
        wav=mp3.with_name(f'escena_{i:02}_ajustada.wav')
        inventory.append(dict(escena=i,mp3=mp3.relative_to(ROOT).as_posix(),bytes=mp3.stat().st_size,
                              sha256=sha(mp3),duracion=float(probe(mp3)['format']['duration']),wav_ajustado_presente=wav.exists()))
    save(out/'reportes/inventario_audio.json',dict(fuente=source.relative_to(ROOT).as_posix(),sha256=sha(source),
         pista_extraida_sha256=sha(audio),metodo='copia de AAC, sin filtros ni cambio de velocidad',
         inventario=inventory,escena_15='MP3 y WAV presentes. El generador omite síntesis si existe MP3 >1000 bytes; sin log histórico no se atribuye con certeza la omisión del mensaje a caché.',
         origen_velocidad='El master aceptado ya contiene ajustes históricos del generador. Se conserva exactamente su AAC; no se añaden atempo ni otros ajustes.',probe=audio_probe))
    from faster_whisper import WhisperModel
    model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=4,
                       download_root=str(ROOT/'.venv-e2e/modelos'),local_files_only=True)
    aligned=[]
    for i,scene in enumerate(original_scenes,1):
        path=work/f'voz_{i:02}.wav'
        start=scene['voice_start']
        duration=scene['adjusted_duration']
        if not path.exists():
            run([ffmpeg(),'-v','error','-n','-ss',str(start),'-i',audio,'-t',str(duration),'-ar','16000','-ac','1',path])
        with wave.open(str(path),'rb') as wav:
            pcm=np.frombuffer(wav.readframes(wav.getnframes()),dtype=np.int16).astype(np.float32)/32768
        segments,_=model.transcribe(pcm,language='es',beam_size=5,word_timestamps=True,
                                    initial_prompt=scene['text'],condition_on_previous_text=False,vad_filter=False)
        words=[]
        for seg in segments:
            for word in seg.words or []:
                words.append(dict(text=word.word.strip(),start=round(start+word.start,3),
                                  end=round(start+word.end,3),probability=round(word.probability,3)))
        text=' '.join(w['text'] for w in words)
        ratio=SequenceMatcher(None,normalized(scene['text']),normalized(text)).ratio()
        entry=dict(escena=i,**scene,recognized=text,similarity=round(ratio,3),words=words)
        aligned.append(entry)
        save(out/'reportes/alineacion_voz.json',dict(modelo='faster-whisper base CPU int8',listening_review='not_performed',
                                                   origen='Audio del MP4 aceptado; transcripción y tiempos calculados localmente',escenas=aligned))
        print(f'{i:02}/19 {ratio:.2f} {text}',flush=True)
    assert len(aligned)==19 and all(s['words'] for s in aligned)


if __name__=='__main__':
    main()
