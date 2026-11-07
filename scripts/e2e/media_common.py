"""Herramientas multimedia locales; nunca envía archivos a servicios externos."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def ffmpeg():
    candidates = list((ROOT/'.venv-e2e/tools/ffmpeg').rglob('ffmpeg.exe'))
    if candidates:
        return str(candidates[0])
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ffprobe():
    installed = shutil.which('ffprobe')
    if installed:
        return installed
    candidates = list((ROOT/'.venv-e2e/tools').rglob('ffprobe.exe'))
    if not candidates:
        raise RuntimeError('Falta FFprobe local. Ver README de presentación.')
    return str(candidates[0])


def run(args, timeout=300):
    return subprocess.run(list(map(str,args)),check=True,capture_output=True,timeout=timeout)


def probe(path):
    return json.loads(run([ffprobe(),'-v','error','-show_streams','-show_format','-of','json',path]).stdout)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def timestamp(seconds, srt=False):
    ms = round(seconds*1000)
    h,ms = divmod(ms,3600000)
    m,ms = divmod(ms,60000)
    s,ms = divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d}{"," if srt else "."}{ms:03d}'
