# Antivirus Project

Aplicacao desktop de seguranca desenvolvida em Python com PyQt5. O projeto organiza recursos de verificacao de arquivos, integracao com ClamAV, analise heuristica, quarentena, historico de escaneamentos, firewall, monitoramento de ransomware e ferramentas de otimizacao do sistema em uma interface unica.

## Proposito

O Antivirus Project nasceu como uma base de estudo e evolucao para um antivírus desktop modular. A proposta e reunir, em camadas bem separadas, interface grafica, controladores, servicos de seguranca, modelos de dados e persistencia local, criando um projeto facil de entender, manter e expandir.

Este projeto deve ser tratado como uma solucao educacional, experimental e de laboratorio. Ele nao substitui uma suite de seguranca corporativa ou uma ferramenta homologada para ambientes criticos.

## Objetivo

- Fornecer uma interface simples para executar verificacoes de arquivos e pastas.
- Integrar deteccao por assinatura via ClamAV com avaliacao heuristica.
- Registrar historico de escaneamentos e eventos relevantes.
- Isolar arquivos suspeitos em quarentena.
- Reunir ferramentas auxiliares como firewall, limpeza, analise de disco, Wi-Fi e desinstalacao de aplicativos.
- Manter uma arquitetura organizada para evolucao academica, tecnica ou profissional.

## Publico-alvo

- Estudantes de Python, seguranca da informacao e desenvolvimento desktop.
- Desenvolvedores que desejam estudar arquitetura MVC/MVVM com PyQt5.
- Profissionais em laboratorio que precisam de uma base extensivel para prototipos de seguranca.
- Pessoas interessadas em entender como componentes de um antivírus podem ser separados em interface, servicos, modelos, banco local e workers.

## Principais recursos

- Interface grafica com PyQt5.
- Escaneamento inteligente e personalizado.
- Pipeline de deteccao com ClamAV, identificacao de arquivo e pontuacao heuristica.
- Historico de escaneamentos em banco local.
- Quarentena e acoes sobre ameacas detectadas.
- Modulos de firewall, status do sistema, monitoramento de processos e inventario de software.
- Ferramentas de otimizacao: limpeza de temporarios, analise de disco e desinstalador.
- Servico de monitoramento contra comportamento associado a ransomware.
- Adaptadores de plataforma para Linux, Windows e macOS.

## Estrutura do projeto

```text
.
|-- main.py                  # Ponto de entrada da aplicacao
|-- clamav/                  # Cliente e integracao com ClamAV
|-- controllers/             # Coordenacao entre interface e servicos
|-- core/platform/           # Adaptadores por sistema operacional
|-- database/                # Banco local, entidades e repositorios
|-- models/                  # Modelos de dominio
|-- resources/icons/         # Icones usados pela interface
|-- services/                # Regras de negocio e servicos de seguranca
|-- system/                  # Inspecao do sistema, processos e inventario
|-- utils/                   # Utilitarios compartilhados
|-- views/                   # Telas e componentes PyQt5
|-- workers/                 # Tarefas em background
|-- locales/                 # Estrutura para traducoes
|-- testes/                  # Area reservada para testes
|-- requirements.txt         # Dependencias Python
`-- README.md
```

## Requisitos

- Python 3.12 ou superior.
- Ambiente Linux/Ubuntu recomendado para os recursos que dependem de pacotes do sistema.
- ClamAV instalado e configurado para verificacao por assinatura.
- Permissoes administrativas podem ser necessarias para firewall, processos, pacotes e recursos do sistema.

## Instalacao

Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Algumas dependencias listadas podem exigir bibliotecas do sistema operacional. Em ambientes Linux, instale os pacotes nativos correspondentes quando o `pip` indicar falta de headers, bibliotecas ou ferramentas de compilacao.

## Como executar

Com o ambiente virtual ativo, inicie a aplicacao:

```bash
python main.py
```

A janela principal abre com as areas de Status, Protecao, Otimizacao e Configuracoes.

## Guia de usuario

1. Abra a aplicacao com `python main.py`.
2. Acesse `Status` para visualizar o estado geral e iniciar verificacoes rapidas quando disponivel.
3. Em `Protecao`, use a verificacao personalizada para escolher arquivos ou pastas.
4. Consulte o `Historico de Escaneamento` para revisar verificacoes anteriores.
5. Use `Quarentena` para acompanhar arquivos isolados e decidir a acao adequada.
6. Em `Firewall`, gerencie recursos de rede quando o sistema permitir.
7. Em `Otimizacao`, use limpeza de temporarios, analise de disco e desinstalacao de aplicativos com cuidado.
8. Em `Configuracoes`, ajuste preferencias de seguranca conforme a evolucao do projeto.

## Git e autoria

Este repositorio esta configurado para usar a autoria:

```bash
git config user.name "Leonardo Boente"
git config user.email "boente66@gmail.com"
```

Quando esse e-mail estiver vinculado a uma conta do GitHub, os commits publicados serao associados ao perfil correspondente.

## Boas praticas do repositorio

Arquivos gerados localmente ficam fora do Git: ambiente virtual, caches Python, banco local, logs, builds e quarentena. O versionamento deve priorizar codigo-fonte, recursos, documentacao e estrutura essencial do projeto.

## Roadmap sugerido

- Adicionar testes automatizados para servicos criticos.
- Revisar `requirements.txt` separando dependencias Python puras de pacotes especificos do sistema.
- Criar empacotamento multiplataforma.
- Documentar fluxos internos de deteccao, quarentena e restauracao.
- Adicionar licenca antes da publicacao oficial no GitHub.
