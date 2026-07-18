# Relatório Técnico de Correção do Fluxo de Detecção de Ameaças

**Projeto:** Antivirus Project

**Data do relatório:** 17 de julho de 2026

**Tipo de intervenção:** Correção focada de contratos e compatibilidade

**Situação:** Implementação e validações concluídas, sem commit

## 1. Objetivo

Este relatório documenta a correção realizada no fluxo de detecção de ameaças, com foco nos contratos entre `DetectedFile`, `Virus`, `ScanResult` e `DetectionPipeline`, bem como na integração desse fluxo com `ScanWorker`, `ScanController` e as views relacionadas ao escaneamento.

A intervenção preservou a arquitetura existente, não alterou o banco de dados e não modificou os módulos de firewall, ransomware ou outras áreas fora das incompatibilidades estritamente necessárias para o funcionamento das views.

## 2. Escopo analisado

Foram analisados diretamente os seguintes arquivos:

- `models/detected_file.py`;
- `models/virus_model.py`;
- `models/scan_result.py`;
- `services/detection_pipeline.py`;
- `services/scan_service.py`;
- `services/clamav_service.py`;
- `services/threat_score_service.py`;
- `services/threat_action_service.py`;
- `workers/scan_worker.py`;
- `controllers/scan_controller.py`;
- todas as views, com atenção especial às telas relacionadas ao scan.

Também foram pesquisadas globalmente todas as instanciações de `Virus(...)`, `ScanResult(...)` e `DetectedFile(...)`.

## 3. Diagnóstico inicial

Antes da correção, foram identificados os seguintes problemas:

1. O `DetectionPipeline` retornava `None` quando o arquivo não era considerado infectado, quebrando o contrato de retorno uniforme do pipeline.
2. Qualquer resposta verdadeira do ClamAV era tratada automaticamente como infecção, sem validação explícita do estado `FOUND`.
3. Respostas inválidas do ClamAV eram mascaradas por uma assinatura genérica `unknown`.
4. O pipeline chamava `ThreatScoreService.calculate()` com o argumento inexistente `file_info`, provocando erro durante a análise.
5. O `ScanWorker` ignorava silenciosamente exceções inesperadas ocorridas na análise de arquivos.
6. O controller poderia finalizar como concluído um scan que anteriormente havia sido marcado como falho ou cancelado.
7. A navegação para a tela de scan poderia adicionar novamente um widget já registrado no `QStackedWidget`.
8. A view de scan personalizado destruía a própria página após iniciar uma verificação, impedindo sua reutilização.
9. A tabela de ameaças não normalizava uma ação `None` antes de criar o item visual.
10. A inicialização do conjunto de views era interrompida pela construção incompatível do `CleanerService`.
11. A view de uso de disco encaminhava um valor decimal para `QProgressBar.setValue()`, que exige um inteiro.

## 4. Correções implementadas

### 4.1. Modelo `DetectedFile`

O arquivo `models/detected_file.py` foi analisado e não precisou ser alterado.

O modelo já atendia aos requisitos definidos:

- recebe `path` no construtor;
- mantém o atributo obrigatório `path`;
- deriva o atributo obrigatório `filename` com `os.path.basename()`;
- disponibiliza `get_path()` e `get_filename()`;
- não realiza cálculo de hash ou processamento pesado no construtor.

### 4.2. Modelo `Virus`

O arquivo `models/virus_model.py` foi analisado e não precisou ser alterado.

O construtor já aceita:

- `name`, obrigatório;
- `path`, opcional;
- `detection_date`, opcional;
- `virus_type`, opcional;
- `recommended_action`, opcional.

Os métodos de leitura e atualização existentes foram preservados.

### 4.3. Modelo `ScanResult`

O modelo foi ajustado para explicitar os tipos do contrato atual e normalizar `infected` como booleano.

O contrato principal passa a expor:

- `detected_file: DetectedFile`;
- `virus: Virus`;
- `infected: bool`;
- `action: str | None`.

A criação com argumentos nomeados permanece suportada:

```python
ScanResult(
    detected_file=detected_file,
    virus=virus,
    infected=True,
    action=None,
)
```

Por compatibilidade com o código legado, também foram preservados:

- `file_path`;
- `status`;
- `signature`;
- `datetime_scanned`;
- criação a partir de um caminho de arquivo.

### 4.4. `DetectionPipeline`

O pipeline foi corrigido para:

- interpretar explicitamente respostas `FOUND` e `OK` do ClamAV;
- considerar resposta vazia como arquivo não infectado;
- rejeitar respostas malformadas com exceções descritivas;
- propagar estados de erro do ClamAV sem mascará-los;
- chamar o serviço de score com a assinatura efetivamente suportada;
- manter identificação e pontuação centralizadas no pipeline;
- preservar a detecção heurística para score igual ou superior a 70;
- construir `DetectedFile`, `Virus` e `ScanResult` de acordo com seus contratos;
- retornar um `ScanResult` infectado quando houver assinatura ou detecção heurística;
- retornar um `ScanResult` não infectado quando não houver ameaça;
- manter `action=None` no resultado inicial;
- não executar quarentena nem exclusão.

Para arquivos limpos, o pipeline retorna um objeto `Virus` com nome vazio, preservando a estabilidade estrutural de `result.virus.name` sem representar uma ameaça inexistente.

### 4.5. `ScanWorker`

O worker já verificava `result.infected` antes de emitir `threat_found`. Essa regra foi preservada e validada.

Também foi removido o descarte silencioso de exceções inesperadas. Falhas de análise agora são contextualizadas com o caminho do arquivo e propagadas ao tratamento geral do worker.

Erros esperados de permissão ou desaparecimento do arquivo durante a varredura continuam sendo ignorados de forma controlada, permitindo que o scan prossiga.

### 4.6. `ScanController`

O controller foi ajustado para:

- rejeitar resultados nulos ou não infectados em `_on_threat()`;
- definir `result.action` após a decisão da camada de ação;
- manter quarentena sob responsabilidade de `QuarantineService`;
- manter exclusão sob responsabilidade de `safe_remove()`;
- impedir que um scan falho ou cancelado seja posteriormente sobrescrito como concluído;
- continuar registrando ameaças usando `DetectedFile` e `Virus` recebidos do pipeline.

Não foi adicionado cálculo de score nem identificação de arquivo no worker ou no controller.

### 4.7. Views

Foram aplicadas correções mínimas de compatibilidade:

- `ScanView` ignora resultados não infectados e converte `action=None` para `-` antes da exibição;
- `MainView` passa automaticamente para a tela de scan quando o sinal `scan_started` é emitido;
- `show_scan_view()` apenas seleciona a tela já registrada, sem duplicar widgets;
- `CustomScanView` deixa de destruir a própria página e passa a navegar para a tela de progresso;
- `CleanerView` obtém o serviço corretamente por meio de `CleanerController`, evitando erro de construtor;
- `DiskUsageView` converte o percentual para inteiro antes de enviá-lo ao `QProgressBar`.

## 5. Contratos finais

### `DetectedFile`

```text
Entrada obrigatória: path
Atributos: path, filename
Métodos preservados: get_path(), get_filename()
Processamento pesado no construtor: não
```

### `Virus`

```text
Entrada obrigatória: name
Entradas opcionais: path, detection_date, virus_type, recommended_action
Acesso direto preservado: virus.name, virus.path
```

### `ScanResult`

```text
Contrato principal:
  detected_file: DetectedFile
  virus: Virus
  infected: bool
  action: str | None

Compatibilidade preservada:
  result.detected_file.path
  result.virus.name
  result.infected
  result.action
  result.file_path
  result.status
  result.signature
  result.datetime_scanned
```

## 6. Arquivos alterados nesta correção

- `controllers/scan_controller.py`;
- `models/scan_result.py`;
- `services/detection_pipeline.py`;
- `views/cleaner_view.py`;
- `views/disk_usage_view.py`;
- `views/main_view.py`;
- `views/scan_options_view.py`;
- `views/scan_view.py`;
- `workers/scan_worker.py`.

Os arquivos `models/detected_file.py` e `models/virus_model.py` foram analisados, mas permaneceram inalterados por já atenderem aos contratos solicitados.

Foi identificada uma alteração local preexistente em `services/ransomware/engine.py`. Essa alteração não faz parte desta correção e foi preservada sem intervenção.

## 7. Validações executadas

Foram realizadas as seguintes verificações:

1. Compilação de sintaxe de models, services, workers, controllers e todas as views.
2. Verificação de formatação do diff com `git diff --check`.
3. Teste de pipeline com resposta infectada do ClamAV.
4. Teste de pipeline com arquivo limpo.
5. Teste de detecção heurística.
6. Teste de propagação de resposta inválida ou estado de erro do ClamAV.
7. Teste de compatibilidade da construção legada de `ScanResult`.
8. Teste de construção de `ScanResult` com argumentos nomeados.
9. Teste de emissão de `threat_found` somente para resultados infectados.
10. Teste da definição de `result.action` pelo controller.
11. Teste offscreen da composição e navegação entre as 12 páginas principais.
12. Busca global de todas as instanciações de `Virus(...)` e `ScanResult(...)`.

Resultado das buscas finais:

- `Virus(...)`: uma instanciação, localizada em `services/detection_pipeline.py`;
- `ScanResult(...)`: uma instanciação, localizada em `services/detection_pipeline.py`.

Todas as validações funcionais relacionadas aos contratos e ao fluxo corrigido foram concluídas com sucesso.

## 8. Restrições respeitadas

- nenhuma alteração de arquitetura de diretórios;
- nenhuma classe renomeada;
- nenhuma alteração no banco de dados;
- nenhuma alteração funcional em firewall ou ransomware;
- nenhuma execução de quarentena ou exclusão pelo pipeline;
- nenhuma duplicação de score ou identificação no worker/controller;
- nenhum cálculo pesado adicionado aos modelos;
- nenhum commit criado.

## 9. Observações finais

Durante o teste offscreen foram exibidos avisos referentes a ícones não encontrados (`loading.svg`, `restore.svg` e `delete.svg`) e uma advertência do ambiente relacionada a limite de monitoramento `inotify`. Esses avisos não impediram a composição e a navegação das páginas e não foram tratados nesta correção para evitar ampliação indevida do escopo.

## 10. Conclusão

O fluxo de detecção passou a possuir retorno uniforme, contratos compatíveis e tratamento explícito de falhas. A responsabilidade do pipeline ficou limitada à identificação e representação do resultado, enquanto decisões e ações permanecem nas camadas apropriadas. O worker e o controller agora respeitam de forma consistente o campo `infected`, e as views relacionadas conseguem consumir o resultado sem duplicação de widgets ou destruição indevida das páginas.

As alterações encontram-se disponíveis apenas no diretório de trabalho e aguardam revisão e aprovação antes de qualquer commit.
