#!/usr/bin/env python3
"""Coloca você (gravado em casa) na frente da foto do prédio do cliente.

Exemplo:
    python compor.py --video eu.mp4 --fundo predio.jpg --legenda --titulo "Condomínio Solar"
"""
import argparse
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

FORMATOS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
FPS = 30


def run(cmd):
    print("+", " ".join(str(c) for c in cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)


def duracao(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video],
        check=True, capture_output=True, text=True).stdout
    return float(json.loads(out)["format"]["duration"])


def recortar_com_ia(video, destino):
    """Sem fundo verde: remove o fundo quadro a quadro com rembg (lento em CPU)."""
    from rembg import new_session, remove
    from PIL import Image

    w, h = map(int, subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", video], check=True, capture_output=True, text=True).stdout.strip().split(","))
    sessao = new_session("u2net_human_seg")
    leitor = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-r", str(FPS), "-f", "rawvideo",
                               "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    escritor = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                                 "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-", "-c:v", "png", destino],
                                stdin=subprocess.PIPE)
    n = 0
    while quadro := leitor.stdout.read(w * h * 3):
        img = Image.frombytes("RGB", (w, h), quadro)
        escritor.stdin.write(remove(img, session=sessao, post_process_mask=True).tobytes())
        n += 1
        if n % FPS == 0:
            print(f"  recorte IA: {n // FPS}s processados", file=sys.stderr)
    escritor.stdin.close()
    escritor.wait()
    leitor.wait()


def gerar_legenda(video, srt):
    from faster_whisper import WhisperModel

    def ts(t):
        return f"{int(t // 3600):02}:{int(t % 3600 // 60):02}:{int(t % 60):02},{int(t % 1 * 1000):03}"

    segmentos, _ = WhisperModel("small", compute_type="int8").transcribe(
        video, language="pt", word_timestamps=True)
    palavras = [w for s in segmentos for w in s.words]
    blocos = [palavras[i:i + 5] for i in range(0, len(palavras), 5)]  # legenda curta, estilo Reels
    with open(srt, "w", encoding="utf-8") as f:
        for i, b in enumerate(blocos, 1):
            texto = "".join(w.word for w in b).strip()
            f.write(f"{i}\n{ts(b[0].start)} --> {ts(b[-1].end)}\n{texto}\n\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", required=True, help="sua gravação")
    p.add_argument("--fundo", required=True, help="foto do prédio/cliente")
    p.add_argument("--saida", help="arquivo final (padrão: saida/<video>_<formato>.mp4)")
    p.add_argument("--formato", choices=FORMATOS, default="9:16")
    p.add_argument("--recorte", choices=["verde", "ia"], default="verde",
                   help="verde = gravou com pano verde (rápido e melhor); ia = sem pano (lento)")
    p.add_argument("--cor-chave", default="0x00FF00", help="cor do pano (padrão verde puro)")
    p.add_argument("--tolerancia", type=float, default=0.15, help="chromakey: suba se sobrar verde")
    p.add_argument("--posicao", choices=["centro", "esquerda", "direita"], default="centro")
    p.add_argument("--altura", type=float, default=0.85, help="altura da pessoa em fração da tela")
    p.add_argument("--desfoque", type=float, default=6, help="desfoque do fundo (0 = nítido)")
    p.add_argument("--legenda", action="store_true", help="gera legenda automática (faster-whisper)")
    p.add_argument("--logo", help="PNG da sua marca (canto superior direito)")
    p.add_argument("--titulo", help="texto nos primeiros 4s, ex: nome do condomínio")
    a = p.parse_args()

    W, H = FORMATOS[a.formato]
    dur = duracao(a.video)
    frames = int(dur * FPS) + FPS
    saida = Path(a.saida or f"saida/{Path(a.video).stem}_{a.formato.replace(':', 'x')}.mp4")
    saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())

    pessoa = a.video
    if a.recorte == "ia":
        pessoa = str(tmp / "pessoa.mov")
        recortar_com_ia(a.video, pessoa)

    entradas = ["-i", pessoa, "-i", a.fundo]
    if a.recorte == "ia":
        entradas += ["-i", a.video]  # áudio original
    audio = "2:a?" if a.recorte == "ia" else "0:a?"

    # Fundo: foto preenchendo a tela, zoom lento (não parece congelada) e leve desfoque.
    filtros = [
        f"[1:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
        f"zoompan=z='1+0.12*on/{frames}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s={W}x{H}:fps={FPS}"
        + (f",gblur=sigma={a.desfoque}" if a.desfoque else "") + "[bg]",
    ]
    chave = (f"chromakey={a.cor_chave}:{a.tolerancia}:0.08,despill=type=green,"
             if a.recorte == "verde" else "")
    filtros.append(f"[0:v]fps={FPS},{chave}scale=-2:{int(H * a.altura)},format=rgba[eu]")
    x = {"centro": "(W-w)/2", "esquerda": "W*0.04", "direita": "W-w-W*0.04"}[a.posicao]
    filtros.append(f"[bg][eu]overlay=x={x}:y=H-h:shortest=1[v]")
    ultimo = "v"
    if a.logo:
        entradas += ["-i", a.logo]
        idx = len(entradas) // 2 - 1
        filtros.append(f"[{idx}:v]scale={int(W * 0.18)}:-1[logo];"
                       f"[{ultimo}][logo]overlay=W-w-W*0.04:H*0.03[vl]")
        ultimo = "vl"
    if a.titulo:
        fonte = int(min(W, H) * 0.055)
        (tmp / "titulo.txt").write_text(textwrap.fill(a.titulo, int(W * 0.85 / (fonte * 0.55))), encoding="utf-8")
        filtros.append(
            f"[{ultimo}]drawtext=textfile={tmp / 'titulo.txt'}:font=Sans:fontsize={fonte}:line_spacing={int(fonte * 0.3)}:"
            f"fontcolor=white:box=1:boxcolor=black@0.55:boxborderw={int(W * 0.02)}:"
            f"x=(w-text_w)/2:y=h*0.12:enable='lt(t,4)'[vt]")
        ultimo = "vt"
    if a.legenda:
        srt = tmp / "legenda.srt"
        gerar_legenda(a.video, srt)
        tamanho = 13 if a.formato == "9:16" else 22
        filtros.append(
            f"[{ultimo}]subtitles={srt}:force_style='FontName=Sans,Bold=1,FontSize={tamanho},"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
            f"Alignment=2,MarginV={60 if a.formato == '9:16' else 30}'[vs]")
        ultimo = "vs"

    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-stats", *entradas,
         "-filter_complex", ";".join(filtros), "-map", f"[{ultimo}]", "-map", audio,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-t", f"{dur:.3f}", "-movflags", "+faststart", str(saida)])
    print(f"\nPronto: {saida}")


if __name__ == "__main__":
    main()
