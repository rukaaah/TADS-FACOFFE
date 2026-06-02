"""
Módulo: repositories.py
Descrição: Implementa o padrão Repository. Isola todas as queries e operações 
de I/O (CRUD) do banco de dados. A camada de serviços (`services.py`) não deve 
escrever SQL ou saber como os dados são salvos; ela apenas chama os métodos 
deste arquivo (ex: `salvar_cota`, `buscar_participacoes_ativas`).
"""