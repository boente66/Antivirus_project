# Pacote Debian para testes no Linux

Este diretório produz um pacote `.deb` autocontido da interface do Antivírus
Project. O pacote é destinado a **testes funcionais**, não a implantação em
produção.

## Decisões de segurança

- A aplicação é iniciada como o usuário da sessão, nunca como `root`.
- Arquivos instalados globalmente não recebem permissão de escrita para grupo
  ou outros usuários.
- Operações UFW solicitam autorização individual por `pkexec`/Polkit.
- A instalação não ativa nem desativa o UFW.
- A instalação não altera regras do Firewall.
- Nenhum scan é iniciado automaticamente.
- Dados e logs do usuário não são incluídos no pacote.
- A remoção do pacote preserva dados do usuário deliberadamente.

## Sistemas indicados

Construa o pacote na mesma distribuição e arquitetura em que ele será
testado. O binário PyInstaller não deve ser considerado universal entre todas
as versões de Debian e Ubuntu.

O fluxo foi preparado inicialmente para Debian/Ubuntu com ambiente gráfico,
ClamAV, UFW e Polkit.

## ClamAV é obrigatório para o escaneamento

O aplicativo usa o daemon do ClamAV como mecanismo de detecção. O pacote pode
ser aberto para diagnóstico de interface, mas **nenhum teste de scan deve ser
considerado válido** sem estas três condições:

1. `clamav-daemon` instalado e em execução;
2. banco de assinaturas instalado e atualizado pelo `clamav-freshclam`;
3. conexão com o socket local do `clamd` disponível para o aplicativo.

O `.deb` declara `clamav`, `clamav-daemon` e `clamav-freshclam` como
dependências obrigatórias. Por isso, instale o arquivo com `apt`, e não apenas
com `dpkg -i`, para que as dependências sejam resolvidas.

## Dependências para construir

No ambiente de desenvolvimento:

```bash
sudo apt install dpkg-dev desktop-file-utils
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pyinstaller
```

O script não baixa dependências e não usa `sudo`.

Se `lintian` estiver instalado, o pacote também será verificado por ele ao
final. A ausência do `lintian` é informada e não impede a construção.

## Construção

Na raiz do repositório:

```bash
./packaging/debian/build_deb.sh
```

O artefato será criado em:

```text
dist/deb/antivirus-project-test_<versão>_<arquitetura>.deb
```

Para definir outra versão ou diretório de saída:

```bash
PACKAGE_VERSION=1.0.0~test2-1 OUTPUT_DIR=/tmp/deb ./packaging/debian/build_deb.sh
```

## Inspeção antes da instalação

```bash
dpkg-deb --info dist/deb/*.deb
dpkg-deb --contents dist/deb/*.deb
```

## Instalação para teste

Use `apt` para que as dependências declaradas sejam resolvidas:

```bash
sudo apt install ./dist/deb/antivirus-project-test_*.deb
```

Depois da instalação, confirme a prontidão do mecanismo antes do primeiro
scan:

```bash
sudo systemctl stop clamav-freshclam
sudo freshclam
sudo systemctl enable --now clamav-daemon clamav-freshclam
systemctl is-active clamav-daemon
systemctl is-active clamav-freshclam
clamdscan --version
```

Se o `clamav-freshclam` já estiver ativo, aguarde a atualização em andamento
em vez de iniciar simultaneamente outro processo `freshclam`.

O pacote instala:

- aplicação em `/opt/antivirus-project`;
- lançador em `/usr/bin/antivirus-project`;
- entrada de menu em `/usr/share/applications`;
- documentação em `/usr/share/doc/antivirus-project-test`.

O script executa o diagnóstico tanto no bundle intermediário quanto em uma
extração limpa do `.deb`, sem instalar o pacote no sistema de construção.

## Diagnóstico

Execute sem abrir a interface:

```bash
/opt/antivirus-project/antivirus-project --diagnose
```

O diagnóstico valida os módulos Python e recursos incorporados. ClamAV, UFW e
Polkit aparecem separadamente como integrações do sistema. A ausência de uma
integração produz aviso e não é confundida com corrupção do pacote.

Esse diagnóstico confirma a presença dos componentes, mas não substitui a
verificação de que o daemon está ativo e a base de assinaturas está atualizada.

Para verificar os serviços:

```bash
systemctl status clamav-daemon
systemctl status clamav-freshclam
clamdscan --version
ufw status
```

O comando `ufw status` pode exigir privilégios na distribuição utilizada. Não
ative o Firewall durante o teste sem revisar previamente as regras de acesso.

## Execução

Abra **Antivírus Project (Teste)** pelo menu ou execute:

```bash
antivirus-project
```

Arquivos de execução do usuário:

- banco e dados: `~/.local/share/antivirus-project/`;
- log do lançador: `~/.local/state/antivirus-project/antivirus-project.log`;
- quarentena: `~/.antivirus_quarantine/`;
- preferências Qt: diretório de configuração padrão da sessão.

## Remoção

```bash
sudo apt remove antivirus-project-test
```

A remoção não apaga banco, logs ou quarentena do usuário. Essa limpeza deve
ser uma decisão explícita depois da inspeção dos dados.

## Licença

O pacote inclui a licença do repositório. Uso comercial exige autorização
prévia, expressa e escrita, conforme `LICENSE` e `NOTICE-BR.md`.
