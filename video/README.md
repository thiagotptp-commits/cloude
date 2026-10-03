# Vídeos de serviço: você + fundo do cliente

Você se grava em casa, e o `compor.py` coloca você na frente da foto do prédio do cliente.
O script também põe zoom lento e desfoque no fundo, título, logo e legenda automática, e
exporta em 9:16 (Reels/TikTok/Shorts) ou 16:9 (YouTube/site).

Tudo roda local com ffmpeg. Não usa plataforma paga.

## Instalar (uma vez)

1. **ffmpeg**:
   - Windows: `winget install ffmpeg`
   - Mac: `brew install ffmpeg`
   - Linux: `apt install ffmpeg`
2. **Python 3.10+**, e depois:
   ```
   pip install -r requirements.txt
   ```
   Só é necessário para `--legenda` e `--recorte ia`. O modo pano verde funciona sem isso.

## Como gravar (é isso que define a qualidade)

- **Pano verde** atrás de você (R$100–200), esticado, sem dobra, a ~1 m das suas costas.
- **Luz uniforme no pano** (sem sombra) e uma luz na sua frente. Use a luz da janela ou um ring light.
- **Não use verde na roupa**: some junto com o fundo.
- Celular **em pé** para 9:16 e **deitado** para 16:9, 1080p e 30 fps. Use microfone de lapela: o áudio importa mais que a imagem.
- **Olhe a foto do prédio antes de gravar.** Se o sol vem da esquerda na foto, a luz principal deve vir da esquerda em você também. Luz que não bate com a foto é o que mais denuncia a montagem.
- Enquadramento: da cintura para cima, com espaço acima da cabeça.

## Como usar

```bash
# Básico: 9:16 com pano verde
python compor.py --video eu.mp4 --fundo predio.jpg

# Completo
python compor.py --video eu.mp4 --fundo predio.jpg --legenda \
  --titulo "Condomínio Solar — impermeabilização da laje" --logo logo.png

# Versão YouTube, você à esquerda e o prédio aparecendo à direita
python compor.py --video eu.mp4 --fundo predio.jpg --formato 16:9 --posicao esquerda

# Sem pano verde (recorte por IA: bem mais lento, e as bordas ficam piores)
python compor.py --video eu.mp4 --fundo predio.jpg --recorte ia
```

O resultado sai em `saida/`. Para ver todas as opções: `python compor.py -h`.

| Problema | Ajuste |
|---|---|
| Sobra borda verde em você | `--tolerancia 0.2` (suba aos poucos) |
| Partes de você ficam transparentes | `--tolerancia 0.1` e mais luz no pano |
| Você grande ou pequeno demais | `--altura 0.7` (fração da altura da tela) |
| Fundo muito borrado ou nítido | `--desfoque 3` (0 = nítido) |

## Limites (leia antes de prometer algo a cliente)

- **Recorte por IA** (`--recorte ia`) processa quadro a quadro na CPU. Um vídeo de 3 minutos pode levar **mais de 1 hora**, e cabelo e mãos rápidos ficam serrilhados. Pano verde é muito melhor.
- **Legenda**: o modelo do Whisper (~500 MB) é baixado na primeira vez. Revise erros em nomes próprios.
- **Foto parada atrás de você continua parecendo montagem**, mesmo com zoom e desfoque. Fica melhor intercalando com imagens **reais** do serviço (antes/depois).
- **Peça autorização ao cliente** para mostrar o prédio e o nome dele.
