# Gerenciador de receitas

Caderno de receitas no terminal, escrito em Python com armazenamento SQLite local.
Permite cadastrar, listar, consultar, editar e excluir receitas com ingredientes,
quantidades, unidades, porções e etapas de preparo.

## Requisitos

Python 3.10 ou superior. Apenas biblioteca padrão: não precisa instalar pacotes,
criar conta nem configurar serviços externos. Execute os comandos na raiz do projeto.

## Uso rápido no Windows

```powershell
py -3.13 -m recipes --help
py -3.13 -m recipes add examples/panquecas.json
py -3.13 -m recipes list
py -3.13 -m recipes show 1
```

Use o ID retornado pelo cadastro no lugar de `1`. No Linux/macOS, substitua
`py -3.13` por `python3`. No Windows com outra versão, ajuste o seletor do launcher.

Para editar, copie o JSON de exemplo, altere os campos desejados e execute:

```powershell
py -3.13 -m recipes edit 1 examples/panquecas.json
```

`edit` substitui **todos** os campos da receita e mantém seu ID. A validação ocorre
antes da gravação; um arquivo inválido não substitui a receita existente.

Para excluir definitivamente:

```powershell
py -3.13 -m recipes delete 1 --yes
```

Sem `--yes`, a operação é recusada e a receita permanece intacta.

## Formato das receitas

Veja [examples/panquecas.json](examples/panquecas.json). O arquivo deve ser JSON UTF-8
com exatamente os campos `title`, `servings`, `ingredients` e `steps`.

- `title`: texto não vazio.
- `servings`: número inteiro entre 1 e 10000.
- `ingredients`: lista não vazia de objetos com `name`, `quantity` e `unit`.
- `name` e `unit`: textos não vazios; unidades são livres e não são convertidas.
- `quantity`: número positivo e finito, de até 1000000000; use ponto decimal no JSON.
- `steps`: lista não vazia de textos não vazios.

Títulos repetidos são permitidos; cada receita tem seu próprio ID. `show` retorna
somente os dados da receita em JSON, que pode ser reutilizado como entrada.

## Dados locais

Por padrão, o banco fica em `~/.gerenciador-receitas/recipes.db`, na pasta pessoal
do usuário. Para usar outro banco, informe `--db` **antes** do comando:

```powershell
py -3.13 -m recipes --db dados/teste.db add examples/panquecas.json
py -3.13 -m recipes --db dados/teste.db list
```

Use o mesmo caminho nos comandos seguintes. Faça backup do arquivo SQLite com o
programa fechado. O banco não é criptografado; não armazene informações sensíveis.
Arquivos de banco local são ignorados pelo Git.

## Testes

```powershell
py -3.13 -m unittest discover -s tests -v
```

Os testes executam a interface real em subprocessos com bancos temporários.
Cobrem persistência entre execuções, cadastro, edição, consulta, exclusão,
confirmação de exclusão, dados inválidos, arquivos ausentes e IDs inexistentes.
Não acessam nem alteram o banco pessoal.

Códigos de saída: `0` para sucesso, `1` para erro de dados/armazenamento,
`2` para erro de sintaxe dos argumentos.

## Estrutura

```text
recipes/
  __main__.py     Entrada do programa
  cli.py          Comandos e mensagens
  model.py        Validação de receitas
  storage.py      Transações e armazenamento SQLite
examples/        Receita de exemplo
tests/           Testes de integração da CLI
```

Esta versão é local e usa arquivos JSON para entrada. Não contém interface gráfica,
sincronização, conversão de unidades ou ajuste automático de porções.

## Licença

Distribuído sob a [licença MIT](LICENSE).
