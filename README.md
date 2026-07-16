# RITMO — RISC-V Interactive Tilemap and Map Output

O RITMO é um editor de mapas e animações feito para projetos de jogos em Assembly RISC-V. Ele permite montar cenários a partir de um *tileset*, marcar áreas de colisão, posicionar entidades e exportar os dados em arquivos `.s` prontos para serem incluídos no código do jogo.

O projeto surgiu durante o desenvolvimento de um clone de **Mega Man 2** para a disciplina de Organização e Arquitetura de Computadores (2026.1), executado em um processador RISC-V implementado na FPGA DE1-SoC.

Em vez de armazenar cada cenário como uma imagem completa na seção de dados, o jogo guarda uma matriz de IDs. Cada ID aponta para um bloco reutilizável do tileset. Essa abordagem reduz o consumo de memória e ainda permite que renderização, colisão e posicionamento de entidades compartilhem a mesma grade do mapa.

> Repositório de exemplo: [felipe-costa-ft/MegaManRISCV](https://github.com/felipe-costa-ft/MegaManRISCV)

## Tutorial em vídeo

Um tutorial de utilização do RITMO está disponível no YouTube:

[Como usar o RITMO](https://www.youtube.com/watch?v=krWMkNkizWI)

## Funcionalidades

- edição da camada visual com um ou vários tiles por pincel;
- camada independente para tipos de colisão;
- cadastro e posicionamento de entidades por tipo;
- conjuntos, clipes, frames, duração e repetição de animações;
- zoom, navegação pelo mapa, preenchimento de áreas e seleção retangular;
- histórico de desfazer/refazer com até 30 estados;
- salvamento do projeto em JSON, com caminho relativo para o tileset;
- exportação de constantes, mapas, colisões, entidades, offsets do tileset e animações em Assembly RISC-V.

## Requisitos

- [Python](https://www.python.org/downloads/) 3.10 ou mais recente;
- `pip`;
- Pygame 2.5 ou mais recente;
- Pillow 10 ou mais recente.

O Python 3.10+ é necessário porque o código utiliza recursos de sintaxe introduzidos nessa versão.

## Instalação e execução

Use um ambiente virtual para manter as dependências do RITMO isoladas das demais instalações do Python.

### macOS

No Terminal, entre na pasta do projeto e execute:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Se o comando `python3` não existir, instale uma versão recente pelo site do Python ou pelo Homebrew. Para encerrar o ambiente virtual depois de usar o editor:

```bash
deactivate
```

### Linux

No terminal, entre na pasta do projeto e execute:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Em distribuições Debian/Ubuntu, caso a criação do ambiente virtual não esteja disponível, instale antes o pacote correspondente:

```bash
sudo apt install python3-venv python3-pip
```

Para sair do ambiente virtual:

```bash
deactivate
```

### Windows

No PowerShell, entre na pasta do projeto e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Se o PowerShell bloquear a ativação do ambiente, autorize scripts apenas para a sessão atual e tente novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

No Prompt de Comando (`cmd`), a ativação equivalente é:

```bat
.venv\Scripts\activate.bat
```

Para sair do ambiente virtual:

```powershell
deactivate
```

Nas execuções seguintes, basta ativar novamente o ambiente virtual e rodar `python main.py`; não é necessário reinstalar as dependências.

## Como utilizar

### 1. Prepare o tileset

O tileset deve ser uma imagem formada por blocos de tamanho uniforme. A largura e a altura da imagem devem ser múltiplas das dimensões escolhidas para o tile. Por exemplo, uma imagem de `192 × 160` pixels comporta uma grade de `12 × 10` tiles de `16 × 16` pixels.

O ID de cada tile corresponde à sua posição na imagem, em ordem da esquerda para a direita e de cima para baixo, começando em `0`. Como o editor usa o ID `0` ao apagar e ao criar áreas vazias, é recomendável reservar o primeiro tile do tileset como vazio ou transparente.

### 2. Crie um novo mapa

Clique em **Novo** e informe:

- quantidade de colunas e linhas do mapa;
- largura e altura de cada tile, em pixels;
- arquivo de imagem do tileset.

Essas dimensões definem a grade lógica exportada. O tamanho visual do cenário será `colunas × largura do tile` por `linhas × altura do tile`.

O botão **Redimensionar** altera um mapa existente mantendo o conteúdo ancorado no canto superior esquerdo. Áreas acrescentadas recebem o valor `0`; tiles e entidades que ficarem fora dos novos limites são descartados. Essa operação também limpa o histórico de desfazer/refazer.

### 3. Edite as camadas

Use os botões da barra superior ou pressione `Tab` para alternar entre os quatro modos:

#### Visual

Escolha um tile no painel lateral e pinte o cenário com o botão esquerdo. Arraste sobre vários tiles do painel para criar um pincel retangular; cada clique no mapa aplica o bloco completo.

#### Colisão

Crie tipos de colisão com IDs, nomes e cores diferentes — por exemplo, `sólido`, `espinho`, `escada` ou `porta`. Selecione um tipo e pinte as células às quais ele se aplica. O tipo `0: vazio` já existe por padrão.

#### Entidades

Crie tipos como `player`, `inimigo`, `item` ou `chefe`, opcionalmente escolhendo uma imagem para a pré-visualização. Um clique esquerdo posiciona a entidade selecionada e um clique direito remove a entidade daquela célula.

As imagens escolhidas para pré-visualizar entidades não são incorporadas ao JSON nem exportadas para Assembly; elas servem somente como auxílio visual durante a sessão atual.

#### Animações

Crie primeiro um **Set** (por exemplo, `PLAYER`) e depois um ou mais **Clips** (por exemplo, `IDLE`, `RUN` e `SHOOT`). Ao clicar nos tiles exibidos no canvas, seus IDs são adicionados como frames ao clipe ativo.

O painel permite:

- reordenar ou remover frames;
- ajustar o atraso padrão do clipe em passos de 10 ms;
- sobrescrever o atraso de um frame específico;
- ativar ou desativar a repetição (*loop*);
- reproduzir ou pausar a pré-visualização.

### 4. Salve o projeto

Clique em **Salvar** e escolha um arquivo `.json`. O arquivo mantém dimensões, camadas, tipos, entidades e animações. O caminho do tileset é salvo de forma relativa ao JSON; por isso, ao mover o projeto, preserve a relação entre os dois arquivos.

Use **Abrir** para continuar editando um projeto salvo.

> Os atalhos `Ctrl+S` e `Ctrl+E` estão reservados no código, mas ainda não executam as ações de salvar e exportar. Use os botões da barra superior.

### 5. Exporte para Assembly RISC-V

Clique em **Exportar**, escolha o diretório de destino e informe um prefixo para os labels, como `MAPA1`. O prefixo é convertido para letras maiúsculas.

Para o prefixo `MAPA1`, são gerados:

| Arquivo | Conteúdo |
| --- | --- |
| `MAPA1_defs.s` | dimensões, tamanho dos tiles e constantes dos tipos de entidade |
| `MAPA1_visual.s` | matriz de IDs da camada visual, linha a linha |
| `MAPA1_colisao.s` | matriz de IDs da camada de colisão |
| `MAPA1_entidades.s` | posições `coluna, linha`, agrupadas por tipo de entidade |
| `MAPA1_entidades_flat.s` | lista única no formato `tipo, coluna, linha` |
| `MAPA1_tileset_offsets.s` | offsets, em bytes, de cada tile dentro do tileset |
| `MAPA1_anim.s` | descritores dos clipes; gerado somente se houver conjuntos de animação |

Por padrão, as camadas são exportadas de cima para baixo, com um byte por tile. A camada visual passa a usar `.half` automaticamente quando o tileset possui mais de 255 tiles. Os arquivos incluem comentários, constantes e exemplos de leitura para facilitar a integração com a engine do jogo.

O arquivo de animações exporta a sequência de IDs dos tiles e o atraso padrão de cada clipe. Atrasos específicos de frames e a opção de *loop* permanecem salvos no projeto JSON, mas a rotina de exportação atual não os codifica no descritor Assembly; se o jogo precisar dessas informações, sua engine deve tratá-las separadamente ou o formato de exportação deve ser estendido.

No projeto MegaManRISCV usado como referência, os resultados ficam em `assets/maps/`, são incluídos pelo programa principal e consumidos assim:

- `*_visual.s` informa qual tile desenhar em cada posição;
- `*_colisao.s` alimenta as consultas da física;
- `*_entidades.s` fornece as posições iniciais dos inimigos e outros objetos;
- `*_tileset_offsets.s` permite localizar rapidamente cada tile nos dados gráficos do tileset.

O RITMO exporta as tabelas e constantes, mas não converte a imagem do tileset para o formato gráfico da plataforma. Essa conversão e as rotinas que interpretam os arquivos `.s` pertencem ao projeto do jogo.

## Atalhos e controles

No macOS, os atalhos de teclado abaixo também usam a tecla **Control (`Ctrl`)**, e não `Command (⌘)`, conforme a implementação atual.

### Teclado

| Atalho | Ação |
| --- | --- |
| `Tab` | alterna entre Visual, Colisão, Entidades e Animações |
| `Ctrl+Z` | desfaz a última edição |
| `Ctrl+Shift+Z` | refaz a edição desfeita |
| `Ctrl+Y` | refaz a edição desfeita |
| `Alt` + arrastar com botão esquerdo | seleciona uma região retangular do mapa |
| `Ctrl+C` | copia as camadas visual e de colisão da região selecionada |
| `Ctrl+V` | ativa a pré-visualização da cópia; clique no mapa para colar |
| `Esc` | cancela a colagem e limpa a seleção atual |
| `Ctrl` + clique esquerdo | preenche toda a área contígua do mesmo valor (*flood fill*) nos modos Visual e Colisão |
| `Shift` + arrastar com botão esquerdo | preenche um retângulo nos modos Visual e Colisão |
| `Shift` + arrastar com botão direito | apaga um retângulo nos modos Visual e Colisão |

### Mouse e trackpad

| Controle | Ação |
| --- | --- |
| clique/arraste com botão esquerdo | pinta tiles ou colisões; em Entidades, posiciona uma entidade |
| clique/arraste com botão direito | apaga tiles ou colisões; em Entidades, remove uma entidade |
| arrastar com botão do meio | move a câmera pelo mapa |
| roda sobre o mapa | aumenta ou reduz o zoom mantendo o ponto sob o cursor |
| roda sobre o painel do tileset | desloca verticalmente a lista de tiles |
| `Shift` + roda sobre o painel do tileset | desloca horizontalmente a lista de tiles |
| gesto horizontal do trackpad sobre o tileset | desloca horizontalmente a lista de tiles |
| arrastar no painel do tileset | seleciona vários tiles e monta um pincel retangular |

Também é possível mudar o zoom pelos botões `−` e `+` da barra superior. O intervalo disponível é de `0,25×` a `8×`.

## Estrutura do projeto

```text
ritmo/
├── main.py            # janela, eventos e fluxo principal
├── editor.py          # estado e operações de edição
├── canvas.py          # desenho do mapa e das animações
├── panels.py          # barra de ferramentas e painéis laterais
├── dialogs.py         # diálogos de criação, abertura e salvamento
├── importer.py        # persistência dos projetos JSON
├── exporter.py        # exportação das camadas para Assembly
├── anim_panel.py      # controles de conjuntos, clipes e frames
├── anim_exporter.py   # exportação das animações
└── requirements.txt   # dependências Python
```

## Exemplo

O principal exemplo de integração é o clone de Mega Man 2 em Assembly RISC-V que motivou a criação do editor:

[felipe-costa-ft/MegaManRISCV](https://github.com/felipe-costa-ft/MegaManRISCV)

## Licença

O código-fonte do RITMO é distribuído sob a [licença MIT](LICENSE).

A licença não se aplica a marcas, personagens, imagens, músicas ou outros recursos de terceiros. Esses materiais permanecem propriedade de seus respectivos titulares.
