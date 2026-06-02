"""
Módulo: retry.py
Descrição: Centraliza a lógica do Padrão de Retentativa (Retry Pattern).
Contém decoradores de resiliência que protegem operações críticas de rede 
(como salvar no banco de dados ou ler do RabbitMQ) contra falhas temporárias 
(ex: picos de I/O, perda momentânea de conexão), usando backoff exponencial.
"""