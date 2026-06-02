"""
Módulo: exceptions.py
Descrição: Centraliza todos os erros personalizados do domínio de Cotas e Adesões.
Em vez de lançar erros genéricos de HTTP (como 400 ou 404) dentro das regras de 
negócio, o serviço lança estas exceções puras. A camada de API (routers) ficará 
responsável por capturar (catch) esses erros de domínio e traduzi-los para os 
códigos HTTP corretos do contrato OpenAPI.
"""