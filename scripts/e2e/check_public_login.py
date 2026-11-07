"""Única comprobación pública autorizada: GET del login; nunca autentica ni escribe."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

URL = 'https://diego01.grupo5.crnube.org/finanzas/login'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='evidencias/s4/reportes/login_publico.json')
    args = parser.parse_args()
    record = dict(fecha=datetime.now(timezone(timedelta(hours=-6))).isoformat(timespec='seconds'),
                  url=URL,metodo='GET',autenticacion=False,redirecciones_seguidas=False)
    try:
        with build_opener(NoRedirect()).open(Request(URL,method='GET'),timeout=20) as response:
            content = response.read(256000).decode('utf-8',errors='replace')
            record.update(http=response.status,formulario_login='name="contrasena"' in content,
                          estado='APROBADA' if response.status==200 and 'name="contrasena"' in content else 'FALLIDA')
    except HTTPError as exc:
        record.update(estado='FALLIDA',http=exc.code)
    except (URLError,OSError):
        record.update(estado='OMITIDA',motivo='No se pudo completar GET por restricción de red, TLS o disponibilidad. No demuestra caída del servidor.')
    output = Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':
    main()
