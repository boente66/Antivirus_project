
# ANTVIRUS PROJECT 

1. Introdução
O software antivírus multiplataforma foi projetado com o objetivo de fornecer proteção contra ameaças digitais, aliado a ferramentas de otimização de sistema. O sistema é voltado para usuários domésticos e técnicos que necessitam de controle detalhado sobre segurança, desempenho e análise do ambiente computacional.
O principal diferencial do software está na sua capacidade de adaptação entre sistemas operacionais distintos, utilizando uma arquitetura modular baseada em adaptação de plataforma. O sistema foi desenvolvido para operar em Linux, Windows e macOS, respeitando as particularidades de cada ambiente.
O software atende a usuários que desejam: proteção contra malware, análise de arquivos, gerenciamento de firewall, monitoramento de atividades suspeitas e otimização de recursos do sistema.
2. Arquitetura do Sistema
O sistema foi desenvolvido utilizando a arquitetura MVC (Model-View-Controller), complementada com camadas de Services e Workers para garantir organização, escalabilidade e desempenho.
A separação em camadas permite que cada componente tenha uma responsabilidade bem definida. As Views são responsáveis pela interface gráfica, os Controllers coordenam a lógica de interação, os Services implementam as regras de negócio e os Workers executam tarefas pesadas em segundo plano.
A estratégia de desenvolvimento adotada foi baseada em desacoplamento e reutilização de código. Para garantir compatibilidade entre sistemas operacionais, foi implementado o padrão Adapter, com uma fábrica (PlatformFactory) responsável por instanciar o comportamento correto conforme o sistema detectado.
As estruturas de dados utilizadas incluem listas para armazenamento de processos e arquivos, dicionários para representação de estados e configurações, e objetos para modelagem de entidades como ameaças, permissões e registros.
O sistema utiliza processamento assíncrono com QThread para evitar bloqueios na interface gráfica, garantindo uma experiência fluida ao usuário.
3. Guia do Usuário
3.1 Instalação do ClamAV:
Linux: sudo apt install clamav clamav-daemon
Windows: instalar via pacote oficial ou WSL
macOS: brew install clamav
Após a instalação, é necessário iniciar o serviço e atualizar a base de dados de vírus utilizando o comando freshclam.
3.2 Verificação de arquivos:
O usuário pode executar uma verificação inteligente ou personalizada. A verificação inteligente analisa diretórios comuns como Downloads e Desktop, enquanto a personalizada permite selecionar qualquer diretório.
3.3 Firewall:
O módulo de firewall permite bloquear ou liberar portas. No Linux, utiliza-se o UFW; no Windows, o netsh; e no macOS, o sistema interno de firewall. O usuário pode criar regras personalizadas para controle de tráfego.
3.4 Limpeza do sistema:
A limpeza remove arquivos temporários, caches e logs desnecessários. Essa funcionalidade foi inspirada em ferramentas como CCleaner e BleachBit, adaptadas para um contexto multiplataforma.
3.5 Desinstalação de aplicativos:
No Linux, utiliza apt ou rpm; no Windows, utiliza o registro do sistema; no macOS, remove aplicativos da pasta Applications. O sistema detecta automaticamente o método adequado.
4. Segurança
O sistema implementa múltiplas camadas de segurança. Arquivos suspeitos são isolados em quarentena, impedindo sua execução. Operações críticas exigem permissões elevadas, garantindo proteção contra ações indevidas.
A execução de comandos do sistema é controlada e validada, evitando riscos de execução maliciosa. Além disso, o sistema monitora alterações suspeitas em arquivos, contribuindo para a prevenção de ransomware.
5. Compatibilidade
O sistema é compatível com Linux, Windows e macOS. Cada sistema possui características específicas, como gerenciamento de processos, permissões e ferramentas nativas.
Através do uso do PlatformAdapter, o sistema adapta seu comportamento automaticamente. No Linux, utiliza comandos como ps e ufw; no Windows, utiliza tasklist e netsh; no macOS, utiliza ferramentas nativas do sistema.
Essa abordagem garante que o software funcione de forma consistente, independentemente do sistema operacional, mantendo uma experiência uniforme ao usuário.

## Licença

Este projeto é distribuído sob a [Licença de Uso Não Comercial e Uso Comercial
sob Autorização Prévia](LICENSE). O uso pessoal, acadêmico, educacional, de
avaliação e de pesquisa sem finalidade comercial é permitido nas condições da
licença. **Qualquer uso comercial exige autorização prévia, expressa e escrita
de Leonardo Boente.**

Esta é uma licença de código-fonte disponível com restrição comercial; não é a
Licença MIT nem uma licença open source aprovada pela Open Source Initiative.
Consulte também o [aviso jurídico para utilização no Brasil](NOTICE-BR.md).
