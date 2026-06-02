"""
Módulo: session.py
Descrição: Gerencia a conexão com o banco de dados exclusivo do serviço de 
Cotas e Adesões (Database per Service). Define a 'Engine' de conexão e 
disponibiliza sessões (transações) seguras para a camada de repositório.
Nenhum outro serviço tem acesso a essa string de conexão.
"""